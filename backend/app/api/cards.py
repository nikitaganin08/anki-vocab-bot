from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_audio_dir,
    get_openrouter_client,
    get_pronunciation_generator,
    require_telegram_webapp_user,
)
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
from app.models.card import AnkiSyncStatus, Card, EntryType, SourceLanguage
from app.services.card_service import apply_source_text
from app.services.pronunciation import EdgeTtsPronunciationGenerator, PronunciationAudioError

router = APIRouter(
    prefix="/api/cards",
    tags=["cards"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]
OpenRouterClientDep = Annotated[OpenRouterClient, Depends(get_openrouter_client)]
PronunciationGeneratorDep = Annotated[
    EdgeTtsPronunciationGenerator, Depends(get_pronunciation_generator)
]
AudioDirDep = Annotated[Path, Depends(get_audio_dir)]


@router.get("", response_model=CardListResponse)
def list_cards(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    search: Annotated[str | None, Query()] = None,
    source_language: Annotated[SourceLanguage | None, Query()] = None,
    entry_type: Annotated[EntryType | None, Query()] = None,
    anki_sync_status: Annotated[AnkiSyncStatus | None, Query()] = None,
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
    if anki_sync_status is not None:
        base = base.where(Card.anki_sync_status == anki_sync_status)
    if is_learning is not None:
        base = base.where(Card.is_learning == is_learning)

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
        validation = validate_source_input(source_text)
        if validation.normalized_text is None:
            summary_counts["invalid_input"] += 1
            items.append(
                CardBatchImportItemResponse(
                    source_text=source_text,
                    status="invalid_input",
                    message=validation.error_message,
                )
            )
            continue

        try:
            result = apply_source_text(session, openrouter_client, validation.normalized_text)
        except OpenRouterError as exc:
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
                    message=result.rejection.message_for_user,
                )
            )
            continue

        summary_counts[result.status] += 1
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
        summary=CardBatchImportSummaryResponse(total=len(payload.source_texts), **summary_counts),
    )


@router.patch("/{card_id}", response_model=CardResponse)
def patch_card(card_id: int, body: CardPatchRequest, session: SessionDep) -> CardResponse:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card.is_learning = body.is_learning
    session.commit()
    return CardResponse.from_card(card)


# Sync route: edge-tts runs its own event loop (asyncio.run) in the threadpool worker.
@router.get("/{card_id}/audio")
def get_card_audio(
    card_id: int,
    session: SessionDep,
    generator: PronunciationGeneratorDep,
    audio_dir: AudioDirDep,
) -> FileResponse:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    path = audio_dir / f"{card_id}.mp3"
    if not path.is_file():
        try:
            audio = generator.generate_audio(card.canonical_text)
        except PronunciationAudioError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.user_message
            ) from exc
        audio_dir.mkdir(parents=True, exist_ok=True)
        # Atomic: a concurrent request never serves a half-written file.
        with tempfile.NamedTemporaryFile(dir=audio_dir, suffix=".tmp", delete=False) as tmp:
            tmp.write(audio)
        Path(tmp.name).replace(path)

    return FileResponse(path, media_type="audio/mpeg")


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, session: SessionDep, audio_dir: AudioDirDep) -> None:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    session.delete(card)
    session.commit()
    # SQLite may reuse the id: never serve the old word's audio for a new card.
    (audio_dir / f"{card_id}.mp3").unlink(missing_ok=True)
