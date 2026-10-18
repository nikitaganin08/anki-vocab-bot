from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fsrs import Card as FsrsCard
from fsrs import State
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings
from app.services.review_stats import ReviewSummary, build_summary

from .conftest import make_card

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)  # Tuesday, 12:00 in Moscow


def _add(
    session: Session,
    name: str,
    state: str | None = None,
    due: datetime | None = None,
    **overrides: object,
) -> Card:
    card = make_card(
        canonical_text=name,
        canonical_text_normalized=name,
        srs_state=state,
        srs_due_at=due,
        srs_card_json=None if state is None else _fsrs_json(state, due),
        **overrides,
    )
    session.add(card)
    session.commit()
    return card


def _fsrs_json(state: str, due: datetime | None) -> str:
    # Last answered an hour ago, i.e. learning cards sit on an intraday step.
    return FsrsCard(
        card_id=1,
        state=State[state.capitalize()],
        step=None if state == "review" else 0,
        stability=10.0,
        difficulty=5.0,
        due=due,
        last_review=NOW - timedelta(hours=1),
    ).to_json()


def _log(
    session: Session,
    card: Card,
    reviewed_at: datetime,
    *,
    rating: int = 3,
    state_before: str | None = "review",
    previous_review: datetime | None = None,
) -> None:
    before = None
    if previous_review is not None:
        before = FsrsCard(
            card_id=card.id,
            state=State.Review,
            stability=10.0,
            difficulty=5.0,
            due=reviewed_at,
            last_review=previous_review,
        ).to_json()
    session.add(
        ReviewLogEntry(
            card_id=card.id,
            reviewed_at=reviewed_at,
            rating=rating,
            auto_rating=rating,
            overridden=False,
            prompt_kind="chunk",
            prompt_index=0,
            typed_answer="x",
            verdict="correct" if rating > 1 else "wrong",
            hint_used=False,
            response_ms=1000,
            card_before_json=before,
            state_before=state_before,
        )
    )
    session.commit()


def _answers(session: Session, card: Card, days_ago: int, count: int) -> None:
    for _ in range(count):
        _log(session, card, NOW - timedelta(days=days_ago))


def test_empty_db_summary(session: Session) -> None:
    summary = build_summary(session, get_app_settings(session), NOW)

    assert summary == ReviewSummary(
        done_today=0,
        due_today=0,
        new_today=0,
        est_minutes=0,
        backlog=0,
        due_all=0,
        retention_30d=None,
        hard_share_30d=None,
        again_share_30d=None,
        learned_total=0,
        learned_delta_7d=0,
        streak_days=0,
        best_streak_days=0,
        heatmap=[0] * 98,
        forecast_tomorrow=0,
        forecast_week_avg=0,
        days_away=None,
    )


def test_done_today_counts_distinct_cards_that_are_not_due(session: Session) -> None:
    settings = get_app_settings(session)
    hour_ago = NOW - timedelta(hours=1)

    passed = _add(session, "passed", "review", NOW + timedelta(days=10))
    _log(session, passed, hour_ago, rating=3)
    assert build_summary(session, settings, NOW).done_today == 1

    # Again on a new card: it comes back within the look-ahead, so it is not done yet.
    again = _add(session, "again", "learning", NOW + timedelta(minutes=1))
    _log(session, again, hour_ago, rating=1, state_before=None)
    summary = build_summary(session, settings, NOW)
    assert (summary.done_today, summary.due_today) == (1, 1)

    # Two answers on one card count once.
    twice = _add(session, "twice", "review", NOW + timedelta(days=4))
    _log(session, twice, hour_ago - timedelta(minutes=5), rating=1)
    _log(session, twice, hour_ago, rating=3)
    assert build_summary(session, settings, NOW).done_today == 2

    # Answered yesterday: not part of today.
    old = _add(session, "old", "review", NOW + timedelta(days=4))
    _log(session, old, NOW - timedelta(days=1))
    assert build_summary(session, settings, NOW).done_today == 2


def test_backlog_beyond_limit(session: Session) -> None:
    for i in range(60):
        _add(session, f"review {i}", "review", NOW - timedelta(days=1))
    _add(session, "learning due", "learning", NOW)
    for i in range(6):
        _add(session, f"new {i}")
    _add(session, "rare new", is_learning=False)

    summary = build_summary(session, get_app_settings(session), NOW)

    assert (summary.due_today, summary.backlog, summary.new_today) == (51, 10, 5)
    # (51 due + 5 new × 2) × default 15 s per answer = 15.25 min.
    assert summary.est_minutes == 16


def test_due_all_ignores_limit(session: Session) -> None:
    for i in range(60):
        _add(session, f"review {i}", "review", NOW - timedelta(days=1))

    summary = build_summary(session, get_app_settings(session), NOW)

    assert (summary.due_today, summary.due_all) == (50, 60)


def test_days_away_counts_study_days(session: Session) -> None:
    settings = get_app_settings(session)
    assert build_summary(session, settings, NOW).days_away is None

    card = _add(session, "give up", "review", NOW + timedelta(days=10))
    _log(session, card, datetime(2026, 10, 16, 20, 30, tzinfo=UTC))  # 23:30 on the 16th, Moscow
    assert build_summary(session, settings, NOW).days_away == 4

    _log(session, card, datetime(2026, 10, 16, 21, 30, tzinfo=UTC))  # 00:30 on the 17th, Moscow
    assert build_summary(session, settings, NOW).days_away == 3

    _log(session, card, NOW - timedelta(hours=1))
    assert build_summary(session, settings, NOW).days_away == 0


def test_retention_counts_only_mature(session: Session) -> None:
    card = _add(session, "give up", "review", NOW + timedelta(days=10))
    day = timedelta(days=1)
    _log(session, card, NOW - day, rating=3, previous_review=NOW - 11 * day)
    _log(session, card, NOW - 2 * day, rating=1, previous_review=NOW - 12 * day)
    _log(session, card, NOW - day, rating=1, previous_review=NOW - 3 * day)  # young
    _log(session, card, NOW - 40 * day, rating=1, previous_review=NOW - 50 * day)  # old
    _log(session, card, NOW - day, rating=1, state_before=None)  # first answer

    summary = build_summary(session, get_app_settings(session), NOW)

    assert summary.retention_30d == 0.5
    assert (summary.hard_share_30d, summary.again_share_30d) == (0.0, 0.5)


def test_hard_and_again_shares_of_mature_answers(session: Session) -> None:
    card = _add(session, "give up", "review", NOW + timedelta(days=10))
    day = timedelta(days=1)
    for rating in (1, 2, 2, 3, 3, 3, 4, 4):  # mature: 1 Again, 2 Hard, 5 Good/Easy
        _log(session, card, NOW - day, rating=rating, previous_review=NOW - 11 * day)
    _log(session, card, NOW - day, rating=2, previous_review=NOW - 3 * day)  # young

    summary = build_summary(session, get_app_settings(session), NOW)

    assert summary.retention_30d == 7 / 8
    assert summary.hard_share_30d == 2 / 8
    assert summary.again_share_30d == 1 / 8


def test_streak_forgives_two_days_per_week(session: Session) -> None:
    card = _add(session, "give up", "review", NOW + timedelta(days=10))
    _answers(session, card, 5, 5)  # Thu
    # Fri, Sat missed: both forgiven in the week of Oct 12.
    _answers(session, card, 2, 5)  # Sun
    # Mon missed: forgiven in the new week; today (Tue) is still in progress.

    summary = build_summary(session, get_app_settings(session), NOW)

    assert (summary.streak_days, summary.best_streak_days) == (2, 2)
    assert summary.heatmap[-6:] == [5, 0, 0, 5, 0, 0]


def test_day_with_four_answers_breaks_streak_without_freeze(session: Session) -> None:
    card = _add(session, "give up", "review", NOW + timedelta(days=10))
    for days_ago in range(10, 5, -1):  # Sat Oct 10 .. Wed Oct 14
        _answers(session, card, days_ago, 5)
    # Thu, Fri missed: both freezes of the week used.
    _answers(session, card, 3, 4)  # Sat: 4 answers, no freeze left
    for days_ago in (2, 1, 0):
        _answers(session, card, days_ago, 5)

    summary = build_summary(session, get_app_settings(session), NOW)

    assert (summary.streak_days, summary.best_streak_days) == (3, 5)
    assert summary.heatmap[-4] == 4


def test_learned_delta_counts_first_graduation_only(session: Session) -> None:
    later = NOW + timedelta(days=30)
    recent = _add(session, "recent", "review", later)
    _log(session, recent, NOW - timedelta(days=3), state_before="learning")
    old = _add(session, "old", "review", later)
    _log(session, old, NOW - timedelta(days=10), state_before="learning")
    _log(session, old, NOW - timedelta(days=2), state_before="review")
    relearned = _add(session, "relearned", "review", later)
    _log(session, relearned, NOW - timedelta(days=2), state_before="relearning")
    learning = _add(session, "learning", "learning", later)
    _log(session, learning, NOW - timedelta(hours=1), state_before=None)

    summary = build_summary(session, get_app_settings(session), NOW)

    assert (summary.learned_total, summary.learned_delta_7d) == (3, 1)


def test_forecast_tomorrow_and_week(session: Session) -> None:
    _add(session, "learning soon", "learning", NOW + timedelta(minutes=5))  # due now
    _add(session, "later today", "review", NOW + timedelta(hours=11))  # 23:00 Moscow
    _add(session, "tomorrow", "review", NOW + timedelta(days=1))
    for i in range(5):
        _add(session, f"this week {i}", "review", NOW + timedelta(days=6))
    _add(session, "next week", "review", NOW + timedelta(days=9))
    _add(session, "rare", "review", NOW + timedelta(days=1), is_learning=False)

    summary = build_summary(session, get_app_settings(session), NOW)

    # Review cards due later today count today (study day starts at midnight), like Anki.
    assert summary.due_today == 2
    assert (summary.forecast_tomorrow, summary.forecast_week_avg) == (1, 1)


def test_forecast_skips_learning_steps_due_later_today(session: Session) -> None:
    _add(session, "hard step", "learning", NOW + timedelta(hours=6))  # still today, intraday

    summary = build_summary(session, get_app_settings(session), NOW)

    assert (summary.due_today, summary.forecast_tomorrow) == (0, 0)
