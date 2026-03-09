from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_anki_token
from app.api.schemas import AnkiAckRequest, AnkiFailRequest, AnkiPendingCardResponse
from app.db.session import get_session
from app.models.anki_sync_attempt import AnkiSyncAttempt
from app.models.card import AnkiSyncStatus, Card

router = APIRouter(
    prefix="/api/anki",
    tags=["anki"],
    dependencies=[Depends(require_anki_token)],
)

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/pending", response_model=list[AnkiPendingCardResponse])
def get_pending(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AnkiPendingCardResponse]:
    retryable_statuses = (AnkiSyncStatus.PENDING, AnkiSyncStatus.FAILED)
    cards = (
        session.execute(
            select(Card)
            .where(Card.eligible_for_anki == True)  # noqa: E712
            .where(Card.anki_sync_status.in_(retryable_statuses))
            .order_by(Card.created_at.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [AnkiPendingCardResponse.from_card(c) for c in cards]


@router.post("/ack", status_code=status.HTTP_204_NO_CONTENT)
def ack_card(body: AnkiAckRequest, session: SessionDep) -> None:
    card = session.get(Card, body.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card.anki_sync_status = AnkiSyncStatus.SYNCED
    card.anki_note_id = body.anki_note_id
    attempt = AnkiSyncAttempt(card_id=card.id, status="synced")
    session.add(attempt)
    session.commit()


@router.post("/fail", status_code=status.HTTP_204_NO_CONTENT)
def fail_card(body: AnkiFailRequest, session: SessionDep) -> None:
    card = session.get(Card, body.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card.anki_sync_status = AnkiSyncStatus.FAILED
    attempt = AnkiSyncAttempt(card_id=card.id, status="failed", error_message=body.error_message)
    session.add(attempt)
    session.commit()
