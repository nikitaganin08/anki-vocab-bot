from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import StatsResponse
from app.db.session import get_session
from app.models.card import AnkiSyncStatus, Card, EntryType, SourceLanguage

router = APIRouter(prefix="/api/stats", tags=["stats"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=StatsResponse)
def get_stats(session: SessionDep) -> StatsResponse:
    total_cards: int = session.execute(select(func.count(Card.id))).scalar_one()
    eligible: int = session.execute(
        select(func.count(Card.id)).where(Card.eligible_for_anki == True)  # noqa: E712
    ).scalar_one()

    def _count_anki_status(s: AnkiSyncStatus) -> int:
        return session.execute(
            select(func.count(Card.id)).where(Card.anki_sync_status == s)
        ).scalar_one()

    by_entry_type: dict[str, int] = {}
    for et in EntryType:
        count: int = session.execute(
            select(func.count(Card.id)).where(Card.entry_type == et)
        ).scalar_one()
        by_entry_type[et.value] = count

    by_source_language: dict[str, int] = {}
    for lang in SourceLanguage:
        count = session.execute(
            select(func.count(Card.id)).where(Card.source_language == lang)
        ).scalar_one()
        by_source_language[lang.value] = count

    return StatsResponse(
        total_cards=total_cards,
        eligible_for_anki=eligible,
        anki_pending=_count_anki_status(AnkiSyncStatus.PENDING),
        anki_synced=_count_anki_status(AnkiSyncStatus.SYNCED),
        anki_failed=_count_anki_status(AnkiSyncStatus.FAILED),
        by_entry_type=by_entry_type,
        by_source_language=by_source_language,
    )
