from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import CardListResponse, CardResponse
from app.db.session import get_session
from app.models.card import AnkiSyncStatus, Card, EntryType, SourceLanguage

router = APIRouter(prefix="/api/cards", tags=["cards"])

SessionDep = Annotated[Session, Depends(get_session)]


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


@router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: int, session: SessionDep) -> CardResponse:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return CardResponse.from_card(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, session: SessionDep) -> None:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    session.delete(card)
    session.commit()
