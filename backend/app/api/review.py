from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_telegram_webapp_user
from app.api.schemas import (
    CardResponse,
    ReviewCheckRequest,
    ReviewCheckResponse,
    ReviewGradeRequest,
    ReviewGradeResponse,
    ReviewPromptResponse,
    ReviewSessionItemResponse,
    ReviewSessionResponse,
    ReviewUndoResponse,
)
from app.db.session import get_session
from app.models.card import Card
from app.services.answer_check import auto_rating, build_prompt, check_answer
from app.services.app_settings import get_app_settings
from app.services.review_stats import ReviewSummary, build_summary
from app.services.srs import (
    GradeInput,
    StaleReviewError,
    as_utc,
    build_scheduler,
    build_session,
    grade_card,
    preview_intervals,
    undo_last,
)

router = APIRouter(
    prefix="/api/review",
    tags=["review"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]

TRANSLATION_OPTIONAL_PREFIXES = ("to ", "a ", "an ", "the ")


def _get_card(session: Session, card_id: int) -> Card:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return card


@router.get("/summary", response_model=ReviewSummary)
def get_summary(session: SessionDep) -> ReviewSummary:
    return build_summary(session, get_app_settings(session), datetime.now(UTC))


@router.get("/session", response_model=ReviewSessionResponse)
def get_review_session(
    session: SessionDep,
    size: Annotated[int, Query(ge=1, le=20)] = 10,
    include_backlog: bool = False,
) -> ReviewSessionResponse:
    items = build_session(
        session, get_app_settings(session), datetime.now(UTC), size, include_backlog
    )
    return ReviewSessionResponse(
        items=[
            ReviewSessionItemResponse(
                card=CardResponse.from_card(item.card),
                intro=item.intro,
                # The expected answer stays on the server; /check reveals it.
                prompt=ReviewPromptResponse(
                    kind=item.prompt.kind,
                    index=item.prompt.index,
                    masked=item.prompt.masked,
                    hint_translation=item.prompt.hint_translation,
                ),
                srs_due_at=as_utc(item.card.srs_due_at) if item.card.srs_due_at else None,
            )
            for item in items
        ]
    )


@router.post("/{card_id}/check", response_model=ReviewCheckResponse)
def check(card_id: int, body: ReviewCheckRequest, session: SessionDep) -> ReviewCheckResponse:
    settings = get_app_settings(session)
    card = _get_card(session, card_id)
    # Rebuild the prompt the client was shown: prompt_index picks the chunk.
    chunks = card.chunks_json if body.prompt_kind == "chunk" else []
    prompt = build_prompt(
        chunks, card.translation_variants_json, card.canonical_text, body.prompt_index
    )
    prefixes = TRANSLATION_OPTIONAL_PREFIXES if prompt.kind == "translation" else ()
    result = check_answer(
        body.typed,
        prompt.expected,
        optional_prefixes=prefixes,
        base_form=card.canonical_text if prompt.kind == "chunk" else None,
    )
    intervals = preview_intervals(build_scheduler(settings), card, datetime.now(UTC))
    return ReviewCheckResponse(
        verdict=result.verdict,
        expected=result.expected,
        auto_rating=auto_rating(result.verdict, body.hint_used),
        intervals=intervals,
    )


@router.post("/{card_id}/grade", response_model=ReviewGradeResponse)
def grade(card_id: int, body: ReviewGradeRequest, session: SessionDep) -> ReviewGradeResponse:
    settings = get_app_settings(session)
    card = _get_card(session, card_id)
    grade_input = GradeInput(
        rating=body.rating,
        auto_rating=body.auto_rating,
        overridden=body.overridden,
        typed_answer=body.typed,
        prompt_kind=body.prompt_kind,
        prompt_index=body.prompt_index,
        verdict=body.verdict,
        hint_used=body.hint_used,
        response_ms=body.response_ms,
        expected_due_at=body.expected_due_at,
    )
    try:
        card = grade_card(session, settings, card, grade_input, datetime.now(UTC))
    except StaleReviewError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewGradeResponse(srs_due_at=as_utc(card.srs_due_at), srs_state=card.srs_state)


@router.post("/undo", response_model=ReviewUndoResponse)
def undo(session: SessionDep) -> ReviewUndoResponse:
    card = undo_last(session)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nothing to undo")
    return ReviewUndoResponse(card_id=card.id)
