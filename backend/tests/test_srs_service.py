from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from fsrs import Card as FsrsCard
from fsrs import State
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings
from app.services.srs import (
    GradeInput,
    StaleReviewError,
    as_utc,
    build_scheduler,
    build_session,
    day_window,
    grade_card,
    preview_intervals,
    undo_last,
)

from .conftest import make_card

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


def _add(session: Session, name: str, **overrides: object) -> Card:
    card = make_card(canonical_text=name, canonical_text_normalized=name, **overrides)
    session.add(card)
    session.commit()
    return card


def _schedule(
    session: Session,
    card: Card,
    state: State,
    due: datetime,
    *,
    stability: float = 10.0,
    last_review: datetime | None = None,
) -> Card:
    fsrs_card = FsrsCard(
        card_id=card.id,
        state=state,
        step=None if state == State.Review else 0,
        stability=stability,
        difficulty=5.0,
        due=due,
        last_review=last_review or due - timedelta(days=stability),
    )
    card.srs_card_json = fsrs_card.to_json()
    card.srs_due_at = due
    card.srs_state = state.name.lower()
    session.commit()
    return card


def _log(session: Session, card: Card, state_before: str | None) -> None:
    session.add(
        ReviewLogEntry(
            card_id=card.id,
            reviewed_at=NOW - timedelta(hours=1),
            rating=3,
            auto_rating=3,
            overridden=False,
            prompt_kind="chunk",
            prompt_index=0,
            typed_answer="x",
            verdict="correct",
            hint_used=False,
            response_ms=1000,
            state_before=state_before,
        )
    )


def _grade(card: Card, rating: int = 3) -> GradeInput:
    return GradeInput(
        rating=rating,
        auto_rating=rating,
        overridden=False,
        typed_answer=card.canonical_text,
        prompt_kind="translation",
        prompt_index=0,
        verdict="correct",
        hint_used=False,
        response_ms=2000,
        expected_due_at=card.srs_due_at,
    )


def _log_count(session: Session) -> int:
    return session.scalar(sa.select(sa.func.count()).select_from(ReviewLogEntry)) or 0


def test_day_window_before_4am_belongs_to_previous_day() -> None:
    # 01:00 in Moscow on the 21st is still the 20th's study day (starts 04:00 MSK = 01:00 UTC).
    start, end = day_window(datetime(2026, 10, 20, 22, 0, tzinfo=UTC), "Europe/Moscow")

    assert start == datetime(2026, 10, 20, 1, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 21, 1, 0, tzinfo=UTC)


def test_new_card_good_goes_to_learning(session: Session) -> None:
    card = _add(session, "give up")

    grade_card(session, get_app_settings(session), card, _grade(card), NOW)

    assert card.srs_state == "learning"
    assert as_utc(card.srs_due_at) == NOW + timedelta(minutes=10)
    assert card.srs_reps == 1


def test_grade_after_reload_from_db(session: Session) -> None:
    settings = get_app_settings(session)
    card = _add(session, "give up")
    grade_card(session, settings, card, _grade(card), NOW)

    session.expire_all()
    card = session.get(Card, card.id)
    assert card is not None
    assert card.srs_due_at is not None and card.srs_due_at.tzinfo is None  # SQLite drops tz
    grade_card(session, settings, card, _grade(card), NOW + timedelta(minutes=11))

    assert _log_count(session) == 2
    assert card.srs_state == "review"


def test_session_order_learning_then_reviews_then_new(session: Session) -> None:
    _add(session, "new one")
    _schedule(session, _add(session, "review one"), State.Review, NOW - timedelta(days=1))
    _schedule(session, _add(session, "learning one"), State.Learning, NOW + timedelta(minutes=5))
    _schedule(session, _add(session, "learning later"), State.Learning, NOW + timedelta(hours=1))

    items = build_session(session, get_app_settings(session), NOW)

    assert [item.card.canonical_text for item in items] == ["learning one", "review one", "new one"]
    assert [item.intro for item in items] == [False, False, True]
    assert items[2].prompt.kind == "translation"


def test_session_respects_daily_limits(session: Session) -> None:
    for i in range(5):
        card = _schedule(
            session, _add(session, f"intro {i}"), State.Learning, NOW + timedelta(hours=2)
        )
        _log(session, card, None)
    reviewed = _schedule(session, _add(session, "reviewed"), State.Review, NOW + timedelta(days=3))
    for _ in range(50):
        _log(session, reviewed, "review")
    session.commit()
    _add(session, "new one")
    _schedule(session, _add(session, "review due"), State.Review, NOW - timedelta(days=1))
    _schedule(session, _add(session, "learning due"), State.Learning, NOW)

    items = build_session(session, get_app_settings(session), NOW)

    assert [item.card.canonical_text for item in items] == ["learning due"]


def test_session_skips_not_learning_cards(session: Session) -> None:
    _add(session, "rare new", is_learning=False)
    _schedule(
        session,
        _add(session, "rare review", is_learning=False),
        State.Review,
        NOW - timedelta(days=1),
    )

    assert build_session(session, get_app_settings(session), NOW) == []


def test_reviews_sorted_by_retrievability_desc(session: Session) -> None:
    due = NOW - timedelta(hours=1)
    _schedule(
        session,
        _add(session, "forgotten"),
        State.Review,
        due,
        last_review=NOW - timedelta(days=30),
    )
    _schedule(
        session, _add(session, "fresh"), State.Review, due, last_review=NOW - timedelta(days=5)
    )

    items = build_session(session, get_app_settings(session), NOW)

    assert [item.card.canonical_text for item in items] == ["fresh", "forgotten"]


def test_grade_rejects_stale_due(session: Session) -> None:
    settings = get_app_settings(session)
    card = _add(session, "give up")
    stale = _grade(card)
    grade_card(session, settings, card, stale, NOW)

    with pytest.raises(StaleReviewError):
        grade_card(session, settings, card, stale, NOW)

    assert _log_count(session) == 1


def test_undo_restores_previous_state(session: Session) -> None:
    assert undo_last(session) is None
    settings = get_app_settings(session)
    card = _schedule(session, _add(session, "give up"), State.Review, NOW - timedelta(days=1))
    before_json, before_due = card.srs_card_json, as_utc(card.srs_due_at)
    grade_card(session, settings, card, _grade(card, rating=1), NOW)
    assert (card.srs_state, card.srs_reps, card.srs_lapses) == ("relearning", 1, 1)

    assert undo_last(session) is card

    assert card.srs_card_json == before_json
    assert as_utc(card.srs_due_at) == before_due
    assert (card.srs_state, card.srs_reps, card.srs_lapses) == ("review", 0, 0)
    assert _log_count(session) == 0


def test_undo_first_answer_resets_to_new(session: Session) -> None:
    card = _add(session, "give up")
    grade_card(session, get_app_settings(session), card, _grade(card), NOW)

    undo_last(session)

    assert (card.srs_card_json, card.srs_due_at, card.srs_state) == (None, None, None)


def test_preview_intervals_monotonic(session: Session) -> None:
    scheduler = build_scheduler(get_app_settings(session))
    new = _add(session, "give up")
    review = _schedule(session, _add(session, "take on"), State.Review, NOW)

    for card in (new, review):
        intervals = preview_intervals(scheduler, card, NOW)
        assert list(intervals) == [1, 2, 3, 4]
        assert intervals[1] <= intervals[2] <= intervals[3] <= intervals[4]
    assert preview_intervals(scheduler, new, NOW)[3] == 600
