"""Read-only views of stored speaking practice for the Mini App's Speaking tab."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.speaking import SpeakingIssue, SpeakingSession
from app.services.speaking import CATEGORY_LABELS
from app.services.srs import as_utc

WINDOW_DAYS = 30
RECENT_SESSIONS = 50


@dataclass(slots=True)
class CategoryCount:
    category: str
    label: str
    count: int


@dataclass(slots=True)
class SessionRow:
    id: int
    recorded_at: datetime
    kind: str
    duration_seconds: int
    topic: str | None
    filler_count: int
    fix_count: int


@dataclass(slots=True)
class SpeakingStats:
    recordings: int
    minutes: int
    filler_rate: float | None
    filler_rate_prev: float | None
    words_used: int
    words_total: int
    categories: list[CategoryCount] = field(default_factory=list)
    sessions: list[SessionRow] = field(default_factory=list)


def topic_of(prompt_text: str | None) -> str | None:
    for line in (prompt_text or "").splitlines():
        if line.startswith("Topic: "):
            return line.removeprefix("Topic: ")
    return None


def _rate(rows: list[SpeakingSession]) -> float | None:
    seconds = sum(row.duration_seconds for row in rows)
    return round(sum(row.filler_count for row in rows) * 60 / seconds, 1) if seconds else None


def _between(session: Session, start: datetime, end: datetime) -> list[SpeakingSession]:
    return list(
        session.scalars(
            select(SpeakingSession).where(
                SpeakingSession.recorded_at >= start, SpeakingSession.recorded_at < end
            )
        )
    )


def build_stats(session: Session, now: datetime) -> SpeakingStats:
    now = as_utc(now)
    start = now - timedelta(days=WINDOW_DAYS)
    rows = _between(session, start, now + timedelta(seconds=1))
    previous = _between(session, start - timedelta(days=WINDOW_DAYS), start)
    words = [word for row in rows for word in json.loads(row.words_json)]
    counts = Counter(
        session.scalars(
            select(SpeakingIssue.category).where(
                SpeakingIssue.session_id.in_([row.id for row in rows])
            )
        )
    )
    fix_counts = dict(
        session.execute(
            select(SpeakingIssue.session_id, func.count()).group_by(SpeakingIssue.session_id)
        ).all()
    )
    recent = session.scalars(
        select(SpeakingSession).order_by(SpeakingSession.recorded_at.desc()).limit(RECENT_SESSIONS)
    )
    return SpeakingStats(
        recordings=len(rows),
        minutes=round(sum(row.duration_seconds for row in rows) / 60),
        filler_rate=_rate(rows),
        filler_rate_prev=_rate(previous),
        words_used=sum(bool(word["used"]) for word in words),
        words_total=len(words),
        categories=[
            CategoryCount(category, CATEGORY_LABELS[category], count)
            for category, count in counts.most_common()
        ],
        sessions=[
            SessionRow(
                id=row.id,
                recorded_at=as_utc(row.recorded_at),
                kind=row.kind,
                duration_seconds=row.duration_seconds,
                topic=topic_of(row.prompt_text),
                filler_count=row.filler_count,
                fix_count=fix_counts.get(row.id, 0),
            )
            for row in recent
        ],
    )


def issues_of(session: Session, category: str) -> list[tuple[SpeakingIssue, datetime]]:
    query = (
        select(SpeakingIssue, SpeakingSession.recorded_at)
        .join(SpeakingSession, SpeakingSession.id == SpeakingIssue.session_id)
        .where(SpeakingIssue.category == category)
        .order_by(SpeakingSession.recorded_at.desc(), SpeakingIssue.id)
    )
    return [(issue, as_utc(recorded_at)) for issue, recorded_at in session.execute(query).all()]
