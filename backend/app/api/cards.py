from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_card_generator
from app.api.schemas import (
    CardBatchImportItemResponse,
    CardBatchImportRequest,
    CardBatchImportResponse,
    CardBatchImportSummaryResponse,
    CardListResponse,
    CardResponse,
)
from app.bot.input_validation import validate_source_input
from app.db.session import get_session
from app.models.card import AnkiSyncStatus, Card, EntryType, SourceLanguage
from app.services.card_service import CardGenerator, CardService, CardServiceUpstreamError

router = APIRouter(prefix="/api/cards", tags=["cards"])

SessionDep = Annotated[Session, Depends(get_session)]
CardGeneratorDep = Annotated[CardGenerator, Depends(get_card_generator)]


@router.get("", response_model=CardListResponse)
def list_cards(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    search: Annotated[str | None, Query()] = None,
    source_language: Annotated[SourceLanguage | None, Query()] = None,
    entry_type: Annotated[EntryType | None, Query()] = None,
    anki_sync_status: Annotated[AnkiSyncStatus | None, Query()] = None,
    eligible_for_anki: Annotated[bool | None, Query()] = None,
) -> CardListResponse:
    base = select(Card)

    if search:
        pattern = f"%{search}%"
        base = base.where(Card.canonical_text.ilike(pattern) | Card.source_text.ilike(pattern))
    if source_language is not None:
        base = base.where(Card.source_language == source_language)
    if entry_type is not None:
        base = base.where(Card.entry_type == entry_type)
    if anki_sync_status is not None:
        base = base.where(Card.anki_sync_status == anki_sync_status)
    if eligible_for_anki is not None:
        base = base.where(Card.eligible_for_anki == eligible_for_anki)

    total: int = session.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    cards = (
        session.execute(base.order_by(Card.created_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )

    return CardListResponse(
        items=[CardResponse.from_card(c) for c in cards],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/batch", response_model=CardBatchImportResponse)
def batch_import_cards(
    payload: CardBatchImportRequest,
    session: SessionDep,
    generator: CardGeneratorDep,
) -> CardBatchImportResponse:
    service = CardService(session=session, generator=generator)
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
        validation = validate_source_input(source_text)
        if not validation.ok or validation.normalized_text is None:
            summary_counts["invalid_input"] += 1
            items.append(
                CardBatchImportItemResponse(
                    source_text=source_text,
                    status="invalid_input",
                    message=validation.error_message or "Invalid input.",
                )
            )
            continue

        try:
            result = service.apply_source_text(validation.normalized_text)
        except CardServiceUpstreamError as exc:
            summary_counts["upstream_error"] += 1
            items.append(
                CardBatchImportItemResponse(
                    source_text=source_text,
                    status="upstream_error",
                    message=exc.user_message,
                )
            )
            continue

        if result.status == "rejected":
            summary_counts["rejected"] += 1
            items.append(
                CardBatchImportItemResponse(
                    source_text=source_text,
                    status="rejected",
                    message=(
                        result.rejection.message_for_user
                        if result.rejection is not None
                        else "The input was rejected by the language model."
                    ),
                )
            )
            continue

        if result.card is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected card service state",
            )

        if result.status == "created":
            summary_counts["created"] += 1
        elif result.status == "duplicate_source":
            summary_counts["duplicate_source"] += 1
        elif result.status == "duplicate_canonical":
            summary_counts["duplicate_canonical"] += 1
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected card service state",
            )

        items.append(
            CardBatchImportItemResponse(
                source_text=source_text,
                status=result.status,
                card_id=result.card.id,
                canonical_text=result.card.canonical_text,
            )
        )

    return CardBatchImportResponse(
        items=items,
        summary=CardBatchImportSummaryResponse(
            total=len(payload.source_texts),
            created=summary_counts["created"],
            duplicate_source=summary_counts["duplicate_source"],
            duplicate_canonical=summary_counts["duplicate_canonical"],
            rejected=summary_counts["rejected"],
            invalid_input=summary_counts["invalid_input"],
            upstream_error=summary_counts["upstream_error"],
        ),
    )


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, session: SessionDep) -> None:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    session.delete(card)
    session.commit()
