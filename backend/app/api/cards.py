from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_openrouter_client, get_tts_client, require_telegram_webapp_user
from app.api.schemas import (
    CardBatchImportItemResponse,
    CardBatchImportRequest,
    CardBatchImportResponse,
    CardBatchImportSummaryResponse,
    CardListResponse,
    CardPatchRequest,
    CardResponse,
)
from app.bot.input_validation import validate_source_input
from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.db.session import get_session
from app.models.card import Card, EntryType, SourceLanguage
from app.services.card_service import CardServiceResult, apply_source_text
from app.services.pronunciation import PronunciationAudioError, TtsClient

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/cards",
    tags=["cards"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]
OpenRouterClientDep = Annotated[OpenRouterClient, Depends(get_openrouter_client)]
TtsClientDep = Annotated[TtsClient, Depends(get_tts_client)]


@router.get("", response_model=CardListResponse)
def list_cards(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    search: Annotated[str | None, Query()] = None,
    source_language: Annotated[SourceLanguage | None, Query()] = None,
    entry_type: Annotated[EntryType | None, Query()] = None,
    is_learning: Annotated[bool | None, Query()] = None,
) -> CardListResponse:
    base = select(Card)

    if search:
        pattern = f"%{search}%"
        base = base.where(Card.canonical_text.ilike(pattern) | Card.source_text.ilike(pattern))
    if source_language is not None:
        base = base.where(Card.source_language == source_language)
    if entry_type is not None:
        base = base.where(Card.entry_type == entry_type)
    if is_learning is not None:
        base = base.where(Card.is_learning == is_learning)

    total: int = session.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    cards = (
        session.execute(
            # id breaks created_at ties so offset paging never repeats or skips a card.
            base.order_by(Card.created_at.desc(), Card.id.desc()).offset(offset).limit(limit)
        )
        .scalars()
        .all()
    )

    return CardListResponse(
        items=[CardResponse.from_card(c) for c in cards],
        total=total,
        offset=offset,
        limit=limit,
    )


def import_source_text(
    session: Session, openrouter_client: OpenRouterClient, source_text: str
) -> tuple[CardBatchImportItemResponse, CardServiceResult | None]:
    """The item for the API reply and, when the LLM ran, the service result (for Telegram)."""
    validation = validate_source_input(source_text)
    if validation.normalized_text is None:
        item = CardBatchImportItemResponse(
            source_text=source_text, status="invalid_input", message=validation.error_message
        )
        return item, None
    try:
        result = apply_source_text(session, openrouter_client, validation.normalized_text)
    except OpenRouterError as exc:
        item = CardBatchImportItemResponse(
            source_text=source_text, status="upstream_error", message=exc.user_message
        )
        return item, None
    if result.status == "rejected":
        item = CardBatchImportItemResponse(
            source_text=source_text,
            status="rejected",
            message=result.rejection.message_for_user,
        )
        return item, result
    item = CardBatchImportItemResponse(
        source_text=source_text,
        status=result.status,
        card_id=result.card.id,
        canonical_text=result.card.canonical_text,
    )
    return item, result


@router.post("/batch", response_model=CardBatchImportResponse)
def batch_import_cards(
    payload: CardBatchImportRequest,
    session: SessionDep,
    openrouter_client: OpenRouterClientDep,
) -> CardBatchImportResponse:
    items: list[CardBatchImportItemResponse] = []
    summary_counts: dict[str, int] = {
        "created": 0,
        "duplicate_source": 0,
        "duplicate_canonical": 0,
        "rejected": 0,
        "invalid_input": 0,
        "upstream_error": 0,
    }

    for source_text in payload.source_texts:
        item, _ = import_source_text(session, openrouter_client, source_text)
        summary_counts[item.status] += 1
        items.append(item)

    return CardBatchImportResponse(
        items=items,
        summary=CardBatchImportSummaryResponse(total=len(payload.source_texts), **summary_counts),
    )


@router.get("/{card_id}/audio", response_class=Response)
def get_card_audio(
    card_id: int,
    session: SessionDep,
    tts_client: TtsClientDep,
    text: Annotated[str | None, Query(max_length=300)] = None,
) -> Response:
    """MP3 of the card's word, or of one of its usage chunks / examples when `text` is given.

    Synthesized per request, the server keeps no copy. `text` must be part of the card, so the
    endpoint cannot be used to read arbitrary text aloud.
    """
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    spoken = card.canonical_text
    if text is not None:
        phrases = [c["text"] for c in card.chunks_json or []] + list(card.examples_json or [])
        if text not in phrases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Text is not part of the card"
            )
        spoken = text
    try:
        audio = tts_client.synthesize(spoken)
    except PronunciationAudioError as exc:
        logger.warning("Pronunciation failed for card %s: %s", card_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.user_message
        ) from exc
    # The word never changes for a card id, so the client may cache it for good.
    return Response(
        audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


@router.patch("/{card_id}", response_model=CardResponse)
def patch_card(card_id: int, body: CardPatchRequest, session: SessionDep) -> CardResponse:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card.is_learning = body.is_learning
    session.commit()
    return CardResponse.from_card(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, session: SessionDep) -> None:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    session.delete(card)
    session.commit()
