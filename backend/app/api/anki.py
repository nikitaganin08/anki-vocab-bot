from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.cards import TtsClientDep, card_audio_response
from app.api.deps import get_openrouter_client, require_anki_token
from app.api.schemas import (
    AnkiAckRequest,
    AnkiFailRequest,
    AnkiImportRequest,
    AnkiImportResponse,
    AnkiPendingCardResponse,
)
from app.clients.openrouter import OpenRouterClient
from app.db.session import get_session
from app.models.card import AnkiSyncStatus, Card
from app.services.anki_import import import_anki_note

router = APIRouter(
    prefix="/api/anki",
    tags=["anki"],
    dependencies=[Depends(require_anki_token)],
)

SessionDep = Annotated[Session, Depends(get_session)]
OpenRouterClientDep = Annotated[OpenRouterClient, Depends(get_openrouter_client)]


@router.get("/pending", response_model=list[AnkiPendingCardResponse])
def get_pending(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AnkiPendingCardResponse]:
    retryable_statuses = (AnkiSyncStatus.PENDING, AnkiSyncStatus.FAILED)
    cards = (
        session.execute(
            select(Card)
            .where(Card.is_learning == True)  # noqa: E712
            .where(Card.anki_sync_status.in_(retryable_statuses))
            # New cards first, so permanently failing ones cannot starve the queue.
            .order_by(Card.anki_sync_status == AnkiSyncStatus.FAILED, Card.created_at.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [AnkiPendingCardResponse.from_card(c) for c in cards]


@router.get("/cards/{card_id}/audio", response_class=Response)
def get_card_audio(card_id: int, session: SessionDep, tts_client: TtsClientDep) -> Response:
    return card_audio_response(session, card_id, tts_client)


@router.post("/ack", status_code=status.HTTP_204_NO_CONTENT)
def ack_card(body: AnkiAckRequest, session: SessionDep) -> None:
    card = session.get(Card, body.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card.anki_sync_status = AnkiSyncStatus.SYNCED
    card.anki_note_id = body.anki_note_id
    card.anki_sync_error = None
    session.commit()


@router.post("/fail", status_code=status.HTTP_204_NO_CONTENT)
def fail_card(body: AnkiFailRequest, session: SessionDep) -> None:
    card = session.get(Card, body.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card.anki_sync_status = AnkiSyncStatus.FAILED
    card.anki_sync_error = body.error_message
    session.commit()


@router.post("/import", response_model=AnkiImportResponse)
def import_note(
    body: AnkiImportRequest, session: SessionDep, openrouter_client: OpenRouterClientDep
) -> AnkiImportResponse:
    result, card = import_anki_note(session, openrouter_client, body, datetime.now(UTC))
    return AnkiImportResponse(status=result, card_id=card.id if card else None)
