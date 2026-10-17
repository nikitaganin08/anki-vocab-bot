from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import fsrs
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.review_log import ReviewLogEntry
from app.services.answer_check import Prompt, build_prompt

# ponytail: SRS state on cards (single user); move to user_cards for multi-user

DAY_START_HOUR = 4
LEARNING_LOOKAHEAD = timedelta(minutes=20)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def day_window(now: datetime, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    day = (as_utc(now).astimezone(tz) - timedelta(hours=DAY_START_HOUR)).date()
    start = datetime.combine(day, time(DAY_START_HOUR), tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time(DAY_START_HOUR), tzinfo=tz)
    return start.astimezone(UTC), end.astimezone(UTC)


def build_scheduler(settings: AppSettings) -> fsrs.Scheduler:
    # Anki-like steps: a new card comes back in 1 minute, then in 1 day.
    return fsrs.Scheduler(
        desired_retention=settings.desired_retention,
        learning_steps=(timedelta(minutes=1), timedelta(days=1)),
        relearning_steps=(timedelta(minutes=10),),
        enable_fuzzing=False,
    )


def load_fsrs_card(card: Card) -> fsrs.Card:
    if card.srs_card_json is None:
        return fsrs.Card(card_id=card.id)
    fsrs_card = fsrs.Card.from_json(card.srs_card_json)
    fsrs_card.due = as_utc(fsrs_card.due)
    if fsrs_card.last_review is not None:
        fsrs_card.last_review = as_utc(fsrs_card.last_review)
    return fsrs_card


def _outcomes(scheduler: fsrs.Scheduler, card: Card, now: datetime) -> dict[int, fsrs.Card]:
    # review_card works on a copy, so the stored card is untouched.
    fsrs_card = load_fsrs_card(card)
    out = {rating.value: scheduler.review_card(fsrs_card, rating, now)[0] for rating in fsrs.Rating}
    # Anki's ordering for review outcomes: Good >= Hard + 1 day, Easy >= Good + 1 day,
    # never past the scheduler's maximum interval.
    cap = now + timedelta(days=scheduler.maximum_interval)
    for lower, higher in (
        (fsrs.Rating.Hard, fsrs.Rating.Good),
        (fsrs.Rating.Good, fsrs.Rating.Easy),
    ):
        if out[lower].state == out[higher].state == fsrs.State.Review:
            bumped = out[lower].due + timedelta(days=1)
            if bumped > out[higher].due:
                out[higher].due = min(bumped, cap)
    # Easy is twice Good once Good is a day or more away: exactly that for new/learning
    # cards, at most that for review ones (2 x Good >= Good + 1 day keeps the order).
    good = out[fsrs.Rating.Good].due - now
    if good >= timedelta(days=1):
        doubled = min(now + 2 * good, cap)
        easy = out[fsrs.Rating.Easy]
        learning = fsrs_card.state == fsrs.State.Learning
        easy.due = doubled if learning else min(easy.due, doubled)
    return out


def preview_intervals(scheduler: fsrs.Scheduler, card: Card, now: datetime) -> dict[int, int]:
    now = as_utc(now)
    return {
        rating: int((after.due - now).total_seconds())
        for rating, after in _outcomes(scheduler, card, now).items()
    }


def is_due(card: Card, now: datetime, start: datetime, end: datetime) -> bool:
    """Day-scale due dates count from the start of their study day, as in Anki.

    Review cards and learning cards on an interday step (last answered before today)
    are due all day; intraday learning steps keep their exact time (+ look-ahead).
    """
    due = as_utc(card.srs_due_at)
    if card.srs_state == "review":
        return due < end
    if due <= now + LEARNING_LOOKAHEAD:
        return True
    last_review = load_fsrs_card(card).last_review
    return due < end and (last_review is None or as_utc(last_review) < start)


@dataclass(slots=True)
class SessionItem:
    card: Card
    prompt: Prompt
    intro: bool


def _item(card: Card, intro: bool = False) -> SessionItem:
    prompt = build_prompt(
        card.chunks_json, card.translation_variants_json, card.canonical_text, card.srs_reps
    )
    return SessionItem(card=card, prompt=prompt, intro=intro)


def _logs_today(session: Session, start: datetime, end: datetime, *conditions: object) -> int:
    query = select(func.count()).select_from(ReviewLogEntry)
    query = query.where(ReviewLogEntry.reviewed_at >= start, ReviewLogEntry.reviewed_at < end)
    return session.scalar(query.where(*conditions)) or 0


def build_session(
    session: Session,
    settings: AppSettings,
    now: datetime,
    size: int = 10,
    include_backlog: bool = False,
) -> list[SessionItem]:
    now = as_utc(now)
    start, end = day_window(now, settings.timezone)
    learning_cards = select(Card).where(Card.is_learning == True)  # noqa: E712

    learning = [
        card
        for card in session.scalars(
            learning_cards.where(
                Card.srs_state.in_(("learning", "relearning")), Card.srs_due_at < end
            ).order_by(Card.srs_due_at, Card.id)
        )
        if is_due(card, now, start, end)
    ]

    # Only answers on review-state cards spend the review limit (learning steps don't).
    reviews_left = settings.reviews_per_day - _logs_today(
        session, start, end, ReviewLogEntry.state_before == "review"
    )
    reviews: list[Card] = []
    # include_backlog ("all at once" after a break) serves every due review.
    if include_backlog or reviews_left > 0:
        scheduler = build_scheduler(settings)
        due = session.scalars(
            learning_cards.where(Card.srs_state == "review", Card.srs_due_at < end)
        ).all()
        due = sorted(
            due,
            key=lambda c: scheduler.get_card_retrievability(load_fsrs_card(c), now),
            reverse=True,
        )
        reviews = due if include_backlog else due[:reviews_left]

    # A log with no previous state is a card's first answer, i.e. a new card introduced.
    new_left = settings.new_per_day - _logs_today(
        session, start, end, ReviewLogEntry.state_before.is_(None)
    )
    new: list[Card] = []
    if new_left > 0:
        new = list(
            session.scalars(
                learning_cards.where(Card.srs_card_json.is_(None))
                .order_by(Card.created_at, Card.id)
                .limit(new_left)
            )
        )

    items = [_item(c) for c in [*learning, *reviews]] + [_item(c, intro=True) for c in new]
    return items[:size]


@dataclass(slots=True)
class GradeInput:
    rating: int
    auto_rating: int
    overridden: bool
    typed_answer: str
    prompt_kind: str
    prompt_index: int
    verdict: str
    hint_used: bool
    response_ms: int
    expected_due_at: datetime | None


class StaleReviewError(Exception):
    pass


def grade_card(
    session: Session, settings: AppSettings, card: Card, grade: GradeInput, now: datetime
) -> Card:
    expected = as_utc(grade.expected_due_at) if grade.expected_due_at else None
    current = as_utc(card.srs_due_at) if card.srs_due_at else None
    # Tolerate sub-second drift from clients that round timestamps (JS Date keeps ms).
    if (expected is None) != (current is None) or (
        expected is not None and abs(expected - current) > timedelta(seconds=1)
    ):
        raise StaleReviewError(f"card {card.id} was already graded")

    now = as_utc(now)
    scheduler = build_scheduler(settings)
    before = load_fsrs_card(card)
    retrievability = (
        None if before.last_review is None else scheduler.get_card_retrievability(before, now)
    )
    after = _outcomes(scheduler, card, now)[grade.rating]

    session.add(
        ReviewLogEntry(
            card_id=card.id,
            reviewed_at=now,
            rating=grade.rating,
            auto_rating=grade.auto_rating,
            overridden=grade.overridden,
            prompt_kind=grade.prompt_kind,
            prompt_index=grade.prompt_index,
            typed_answer=grade.typed_answer,
            verdict=grade.verdict,
            hint_used=grade.hint_used,
            response_ms=grade.response_ms,
            retrievability=retrievability,
            card_before_json=card.srs_card_json,
            state_before=card.srs_state,
        )
    )
    if grade.rating == fsrs.Rating.Again and card.srs_state == "review":
        card.srs_lapses += 1
    card.srs_reps += 1
    card.srs_card_json = after.to_json()
    card.srs_due_at = after.due
    card.srs_state = after.state.name.lower()
    session.commit()
    return card


def undo_last(session: Session) -> Card | None:
    log = session.scalars(select(ReviewLogEntry).order_by(ReviewLogEntry.id.desc())).first()
    if log is None:
        return None
    card = session.get_one(Card, log.card_id)
    card.srs_card_json = log.card_before_json
    card.srs_state = log.state_before
    card.srs_due_at = None if log.card_before_json is None else load_fsrs_card(card).due
    card.srs_reps -= 1
    if log.rating == fsrs.Rating.Again and log.state_before == "review":
        card.srs_lapses -= 1
    session.delete(log)
    session.commit()
    return card
