from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_telegram_webapp_user
from app.api.schemas import (
    SpeakingIssueResponse,
    SpeakingSessionDetailResponse,
    SpeakingStatsResponse,
)
from app.db.session import get_session
from app.models.speaking import SpeakingIssue, SpeakingSession
from app.schemas.speaking import ISSUE_CATEGORIES
from app.services.speaking import CATEGORY_LABELS
from app.services.speaking_stats import build_stats, issues_of, topic_of
from app.services.srs import as_utc

router = APIRouter(
    prefix="/api/speaking",
    tags=["speaking"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


def _issue(issue: SpeakingIssue, recorded_at: datetime) -> SpeakingIssueResponse:
    return SpeakingIssueResponse(
        id=issue.id,
        session_id=issue.session_id,
        recorded_at=recorded_at,
        category=issue.category,
        label=CATEGORY_LABELS[issue.category],
        wrong=issue.wrong,
        right=issue.right,
        why=issue.why,
    )


@router.get("/stats", response_model=SpeakingStatsResponse)
def read_stats(session: SessionDep) -> SpeakingStatsResponse:
    return SpeakingStatsResponse.model_validate(build_stats(session, datetime.now(UTC)))


@router.get("/issues", response_model=list[SpeakingIssueResponse])
def read_issues(category: str, session: SessionDep) -> list[SpeakingIssueResponse]:
    if category not in ISSUE_CATEGORIES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown category")
    return [_issue(issue, recorded_at) for issue, recorded_at in issues_of(session, category)]


@router.get("/sessions/{session_id}", response_model=SpeakingSessionDetailResponse)
def read_session(session_id: int, session: SessionDep) -> SpeakingSessionDetailResponse:
    row = session.get(SpeakingSession, session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recording not found")
    recorded_at = as_utc(row.recorded_at)
    issues = session.scalars(
        select(SpeakingIssue).where(SpeakingIssue.session_id == row.id).order_by(SpeakingIssue.id)
    )
    return SpeakingSessionDetailResponse(
        id=row.id,
        recorded_at=recorded_at,
        kind=row.kind,
        duration_seconds=row.duration_seconds,
        topic=topic_of(row.prompt_text),
        words=[{"word": w["word"], "used": bool(w["used"])} for w in json.loads(row.words_json)],
        transcript=row.transcript,
        filler_count=row.filler_count,
        natural_version=row.natural_version,
        next_time=row.next_time,
        focus_check=row.focus_check,
        issues=[_issue(issue, recorded_at) for issue in issues],
    )
