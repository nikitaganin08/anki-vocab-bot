from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import fsrs
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.review_log import ReviewLogEntry
from app.services.srs import DAY_START_HOUR, LEARNING_LOOKAHEAD, as_utc, day_window

HEATMAP_DAYS = 98
STREAK_MIN_ANSWERS = 5
FREEZES_PER_WEEK = 2
DEFAULT_RESPONSE_MS = 15_000
MATURE_ELAPSED = timedelta(days=7)


@dataclass(slots=True)
class ReviewSummary:
    due_today: int
    new_today: int
    est_minutes: int
    backlog: int
    retention_30d: float | None
    learned_total: int
    learned_delta_7d: int
    streak_days: int
    best_streak_days: int
    heatmap: list[int]
    forecast_tomorrow: int
    forecast_week_avg: int


def _study_day(dt: datetime, tz: ZoneInfo) -> date:
    return (as_utc(dt).astimezone(tz) - timedelta(hours=DAY_START_HOUR)).date()


def _previous_review(card_before_json: str | None) -> datetime | None:
    if card_before_json is None:
        return None
    last_review = fsrs.Card.from_json(card_before_json).last_review
    return None if last_review is None else as_utc(last_review)


def _streaks(answers: Counter[date], today: date) -> tuple[int, int]:
    """Current and best streak; a missed day is forgiven up to twice per calendar week."""
    run = best = 0
    freezes: Counter[date] = Counter()
    day = min(answers, default=today)
    while day <= today:
        week = day - timedelta(days=day.weekday())
        if answers[day] >= STREAK_MIN_ANSWERS:
            run += 1
        elif day < today:  # today is still in progress
            if run and freezes[week] < FREEZES_PER_WEEK:
                freezes[week] += 1
            else:
                run = 0
        best = max(best, run)
        day += timedelta(days=1)
    return run, best


def build_summary(session: Session, settings: AppSettings, now: datetime) -> ReviewSummary:
    # ponytail: whole history aggregated in Python (single user); move to SQL if logs reach ~1M
    now = as_utc(now)
    tz = ZoneInfo(settings.timezone)
    start, end = day_window(now, settings.timezone)
    today = _study_day(now, tz)

    cards = session.execute(
        select(Card.id, Card.is_learning, Card.srs_state, Card.srs_due_at)
    ).all()
    logs = session.execute(
        select(
            ReviewLogEntry.card_id,
            ReviewLogEntry.reviewed_at,
            ReviewLogEntry.rating,
            ReviewLogEntry.response_ms,
            ReviewLogEntry.state_before,
            ReviewLogEntry.card_before_json,
        ).order_by(ReviewLogEntry.id)
    ).all()

    # Same "due" rules as build_session, so the dashboard matches what a session serves.
    due_reviews = due_learning = available_new = 0
    upcoming: list[date] = []
    for card in cards:
        if not card.is_learning:
            continue
        if card.srs_state is None:
            available_new += 1
            continue
        due = as_utc(card.srs_due_at)
        if card.srs_state == "review" and due <= now:
            due_reviews += 1
        elif card.srs_state != "review" and due <= now + LEARNING_LOOKAHEAD:
            due_learning += 1
        else:
            upcoming.append(_study_day(due, tz))

    today_logs = [log for log in logs if start <= as_utc(log.reviewed_at) < end]
    reviews_done = sum(log.state_before == "review" for log in today_logs)
    new_done = sum(log.state_before is None for log in today_logs)
    reviews_today = min(due_reviews, max(0, settings.reviews_per_day - reviews_done))
    due_today = reviews_today + due_learning
    new_today = min(available_new, max(0, settings.new_per_day - new_done))

    response_ms = [log.response_ms for log in logs[-200:]]
    median_ms = statistics.median(response_ms) if response_ms else DEFAULT_RESPONSE_MS
    est_minutes = math.ceil((due_today + new_today * 2) * median_ms / 60_000)

    # Previous review comes from the card state before the answer (covers imported cards too).
    mature = []
    for log in logs:
        reviewed_at = as_utc(log.reviewed_at)
        if reviewed_at < now - timedelta(days=30):
            continue
        previous = _previous_review(log.card_before_json)
        if previous is not None and reviewed_at - previous >= MATURE_ELAPSED:
            mature.append(log.rating > 1)

    # Graduation = a learning (or new) card's answer that left it in review; happens once.
    # A log's resulting state is the next log's state_before, or the card's current state.
    state_after = {card.id: card.srs_state for card in cards}
    graduated: set[int] = set()
    for log in reversed(logs):
        if (
            log.state_before in (None, "learning")
            and state_after.get(log.card_id) == "review"
            and as_utc(log.reviewed_at) >= now - timedelta(days=7)
        ):
            graduated.add(log.card_id)
        state_after[log.card_id] = log.state_before
    learned = {card.id for card in cards if card.srs_state == "review"}

    # Every log is a typed answer (intro screens are not logged).
    answers = Counter(_study_day(log.reviewed_at, tz) for log in logs)
    streak, best_streak = _streaks(answers, today)

    # One session a day: cards that come due later today are done tomorrow.
    tomorrow = today + timedelta(days=1)
    week = sum(day <= today + timedelta(days=7) for day in upcoming)

    return ReviewSummary(
        due_today=due_today,
        new_today=new_today,
        est_minutes=est_minutes,
        backlog=due_reviews - reviews_today,
        retention_30d=sum(mature) / len(mature) if mature else None,
        learned_total=len(learned),
        learned_delta_7d=len(graduated & learned),
        streak_days=streak,
        best_streak_days=best_streak,
        heatmap=[answers[today - timedelta(days=i)] for i in reversed(range(HEATMAP_DAYS))],
        forecast_tomorrow=sum(day <= tomorrow for day in upcoming),
        forecast_week_avg=round(week / 7),
    )
