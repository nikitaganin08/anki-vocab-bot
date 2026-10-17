from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from fsrs import Card as FsrsCard
from fsrs import Scheduler, State
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings
from app.services.review_stats import build_summary
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
DAY = 86400


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
    difficulty: float = 5.0,
    last_review: datetime | None = None,
) -> Card:
    fsrs_card = FsrsCard(
        card_id=card.id,
        state=state,
        step=None if state == State.Review else 0,
        stability=stability,
        difficulty=difficulty,
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


def test_day_window_starts_at_local_midnight() -> None:
    # 00:30 in Moscow on the 21st already belongs to the 21st (midnight MSK = 21:00 UTC).
    start, end = day_window(datetime(2026, 10, 20, 21, 30, tzinfo=UTC), "Europe/Moscow")

    assert start == datetime(2026, 10, 20, 21, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 21, 21, 0, tzinfo=UTC)

    # 23:30 in Moscow on the 20th is still the 20th's study day.
    start, _ = day_window(datetime(2026, 10, 20, 20, 30, tzinfo=UTC), "Europe/Moscow")
    assert start == datetime(2026, 10, 19, 21, 0, tzinfo=UTC)


def test_new_card_good_goes_to_learning(session: Session) -> None:
    card = _add(session, "give up")

    grade_card(session, get_app_settings(session), card, _grade(card), NOW)

    assert card.srs_state == "learning"
    assert as_utc(card.srs_due_at) == NOW + timedelta(days=1)
    assert card.srs_reps == 1


def test_grade_after_reload_from_db(session: Session) -> None:
    settings = get_app_settings(session)
    card = _add(session, "give up")
    grade_card(session, settings, card, _grade(card), NOW)

    session.expire_all()
    card = session.get(Card, card.id)
    assert card is not None
    assert card.srs_due_at is not None and card.srs_due_at.tzinfo is None  # SQLite drops tz
    grade_card(session, settings, card, _grade(card), NOW + timedelta(days=1))

    assert _log_count(session) == 2
    assert card.srs_state == "review"


def test_session_order_learning_then_reviews_then_new(session: Session) -> None:
    _add(session, "new one")
    _schedule(session, _add(session, "review one"), State.Review, NOW - timedelta(days=1))
    just_now = NOW - timedelta(minutes=5)
    _schedule(
        session,
        _add(session, "learning one"),
        State.Learning,
        NOW + timedelta(minutes=5),
        last_review=just_now,
    )
    _schedule(
        session,
        _add(session, "learning later"),
        State.Learning,
        NOW + timedelta(hours=1),
        last_review=just_now,
    )

    items = build_session(session, get_app_settings(session), NOW)

    assert [item.card.canonical_text for item in items] == ["learning one", "review one", "new one"]
    assert [item.intro for item in items] == [False, False, True]
    assert items[2].prompt.kind == "translation"


def test_session_respects_daily_limits(session: Session) -> None:
    for i in range(5):
        card = _schedule(
            session,
            _add(session, f"intro {i}"),
            State.Learning,
            NOW + timedelta(hours=2),
            last_review=NOW - timedelta(minutes=10),
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


def test_session_include_backlog_ignores_cap(session: Session) -> None:
    settings = get_app_settings(session)
    settings.reviews_per_day = 1
    for i in range(3):
        _schedule(session, _add(session, f"review {i}"), State.Review, NOW - timedelta(days=1))
    _add(session, "new one")

    capped = build_session(session, settings, NOW)
    backlog = build_session(session, settings, NOW, include_backlog=True)

    assert [item.intro for item in capped] == [False, True]
    assert [item.intro for item in backlog] == [False, False, False, True]


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


def test_new_card_intervals_follow_learning_steps(session: Session) -> None:
    intervals = preview_intervals(
        build_scheduler(get_app_settings(session)), _add(session, "give up"), NOW
    )

    assert (intervals[1], intervals[3], intervals[4]) == (60, DAY, 2 * DAY)


def test_learning_card_good_graduates_and_easy_doubles_good(session: Session) -> None:
    settings = get_app_settings(session)
    card = _add(session, "give up")
    grade_card(session, settings, card, _grade(card), NOW)  # learning step 1: due in 1 day
    later = NOW + timedelta(days=1)

    intervals = preview_intervals(build_scheduler(settings), card, later)
    assert intervals[3] >= DAY
    assert intervals[4] == 2 * intervals[3]

    grade_card(session, settings, card, _grade(card), later)
    assert card.srs_state == "review"
    assert as_utc(card.srs_due_at) == later + timedelta(seconds=intervals[3])


@pytest.mark.parametrize("graded_before", [0, 1])
def test_grade_easy_stores_previewed_due(session: Session, graded_before: int) -> None:
    settings = get_app_settings(session)
    card = _add(session, "give up")
    for _ in range(graded_before):
        grade_card(session, settings, card, _grade(card), NOW)
    later = NOW + timedelta(days=graded_before)

    intervals = preview_intervals(build_scheduler(settings), card, later)
    grade_card(session, settings, card, _grade(card, rating=4), later)

    assert card.srs_state == "review"
    assert as_utc(card.srs_due_at) == later + timedelta(seconds=intervals[4])


@pytest.mark.parametrize(
    ("stability", "elapsed_days", "difficulty"),
    [(10.0, 10, 5.0), (1.0, 1, 1.0), (0.3, 30, 10.0)],
)
def test_review_easy_between_good_plus_day_and_double_good(
    session: Session, stability: float, elapsed_days: int, difficulty: float
) -> None:
    card = _schedule(
        session,
        _add(session, "take on"),
        State.Review,
        NOW,
        stability=stability,
        difficulty=difficulty,
        last_review=NOW - timedelta(days=elapsed_days),
    )

    intervals = preview_intervals(build_scheduler(get_app_settings(session)), card, NOW)

    assert intervals[3] + DAY <= intervals[4] <= 2 * intervals[3]


def test_review_easy_clamped_to_double_good(session: Session) -> None:
    # A huge easy bonus (w16) makes raw FSRS Easy far more than twice Good.
    parameters = list(build_scheduler(get_app_settings(session)).parameters)
    parameters[16] = 6.0
    scheduler = Scheduler(parameters=parameters, enable_fuzzing=False)
    card = _schedule(session, _add(session, "take on"), State.Review, NOW)

    intervals = preview_intervals(scheduler, card, NOW)

    assert intervals[4] == 2 * intervals[3]


def test_grade_tolerates_subsecond_drift_in_expected_due(session: Session) -> None:
    settings = get_app_settings(session)
    card = _add(session, "drift")
    grade_card(session, settings, card, _grade(card), NOW)

    grade = _grade(card)
    grade.expected_due_at = card.srs_due_at + timedelta(milliseconds=500)
    grade_card(session, settings, card, grade, NOW + timedelta(minutes=11))

    assert card.srs_reps == 2


# Raw FSRS gives Hard == Good (4, 4, 6 days) and Good == Easy (2, 3, 3 days) for these cards.
@pytest.mark.parametrize(("stability", "elapsed_days"), [(3.0, 3), (2.0, 1)])
def test_review_intervals_strictly_ordered_and_graded_as_previewed(
    session: Session, stability: float, elapsed_days: int
) -> None:
    settings = get_app_settings(session)
    card = _schedule(
        session,
        _add(session, "take on"),
        State.Review,
        NOW,
        stability=stability,
        difficulty=10.0,
        last_review=NOW - timedelta(days=elapsed_days),
    )

    intervals = preview_intervals(build_scheduler(settings), card, NOW)
    hard, good, easy = (intervals[r] // 86400 for r in (2, 3, 4))
    assert 0 < hard < good < easy

    grade_card(session, settings, card, _grade(card, rating=3), NOW)
    assert as_utc(card.srs_due_at) == NOW + timedelta(seconds=intervals[3])


def test_ordered_intervals_never_exceed_maximum(session: Session) -> None:
    settings = get_app_settings(session)
    scheduler = build_scheduler(settings)
    card = _schedule(
        session,
        _add(session, "ancient"),
        State.Review,
        NOW,
        stability=60000.0,
        last_review=NOW - timedelta(days=36500),
    )

    intervals = preview_intervals(scheduler, card, NOW)

    assert max(intervals.values()) <= scheduler.maximum_interval * 86400


def test_day_scale_due_dates_are_available_from_start_of_study_day(session: Session) -> None:
    settings = get_app_settings(session)
    later_today = NOW + timedelta(hours=8)  # 20:00 Moscow, same study day
    tomorrow = NOW + timedelta(hours=20)  # 08:00 Moscow next day
    review_today = _schedule(session, _add(session, "review today"), State.Review, later_today)
    _schedule(session, _add(session, "review tomorrow"), State.Review, tomorrow)
    interday = _schedule(
        session,
        _add(session, "interday step"),
        State.Learning,
        later_today,
        last_review=NOW - timedelta(days=1),
    )
    _schedule(
        session,
        _add(session, "intraday step"),
        State.Learning,
        NOW + timedelta(hours=3),
        last_review=NOW - timedelta(hours=1),
    )

    served = {item.card.id for item in build_session(session, settings, NOW, size=10)}

    assert served == {review_today.id, interday.id}
    assert build_summary(session, settings, NOW).due_today == 2


def test_daily_cap_takes_most_overdue_reviews_first(session: Session) -> None:
    settings = get_app_settings(session)
    settings.reviews_per_day = 1
    session.commit()
    overdue = _schedule(
        session, _add(session, "overdue"), State.Review, NOW - timedelta(days=10), stability=5.0
    )
    _schedule(session, _add(session, "later today"), State.Review, NOW + timedelta(hours=8))

    served = [item.card.id for item in build_session(session, settings, NOW, size=10)]

    assert served == [overdue.id]


def test_lookahead_does_not_cross_into_next_study_day(session: Session) -> None:
    settings = get_app_settings(session)
    before_midnight = datetime(2026, 10, 20, 20, 50, tzinfo=UTC)  # 23:50 Moscow
    _schedule(
        session,
        _add(session, "after midnight"),
        State.Learning,
        before_midnight + timedelta(minutes=15),  # 00:05 Moscow, next study day
        last_review=before_midnight - timedelta(minutes=5),
    )

    assert build_session(session, settings, before_midnight, size=10) == []
    assert build_summary(session, settings, before_midnight).due_today == 0


@pytest.mark.parametrize(
    ("moment", "hours"),
    [
        (datetime(2026, 3, 29, 10, 0, tzinfo=UTC), 23),  # Berlin springs forward
        (datetime(2026, 10, 25, 10, 0, tzinfo=UTC), 25),  # Berlin falls back
    ],
)
def test_day_window_spans_local_day_across_dst(moment: datetime, hours: int) -> None:
    start, end = day_window(moment, "Europe/Berlin")

    assert end - start == timedelta(hours=hours)
    assert start.astimezone(ZoneInfo("Europe/Berlin")).hour == 0
