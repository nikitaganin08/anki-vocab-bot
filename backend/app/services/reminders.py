from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bot.handler import _web_app_keyboard
from app.core.config import get_settings
from app.models.app_settings import AppSettings
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings
from app.services.review_stats import ReviewSummary, build_summary
from app.services.srs import DAY_START_HOUR, as_utc

logger = logging.getLogger(__name__)

BACKOFF_AFTER_IGNORED = 3
PAUSE_AFTER_IGNORED = 7

# Draft copy: no streaks, no guilt; "{cards}" is "12 cards", "{minutes}" a number.
REMINDER_TEMPLATES: tuple[str, ...] = (
    "{cards} for today, ~{minutes} min.",
    "Your words are waiting: {cards}, ~{minutes} min.",
    "A short session: {cards} in ~{minutes} min.",
    "Today's batch of words: {cards}, ~{minutes} min.",
    "Time to refresh your words: {cards}, ~{minutes} min.",
    "Your words for today: {cards}, ~{minutes} min.",
    "A little workout: {cards}, ~{minutes} min.",
    "Shall we refresh your memory? {cards}, ~{minutes} min.",
    "A ~{minutes} min review: {cards}.",
    "Time to review: {cards}, ~{minutes} min.",
    "Today's words are ready: {cards}, ~{minutes} min.",
    "A minute of English: {cards}, ~{minutes} min.",
)


def should_send(
    settings: AppSettings,
    now_local: datetime,
    reviewed_today: bool,
    due_total: int,
    today_local: date,
) -> bool:
    if now_local.hour < settings.reminder_hour or settings.last_reminder_on == today_local:
        return False
    if reviewed_today or due_total <= 0:
        return False
    if settings.ignored_reminders >= PAUSE_AFTER_IGNORED:
        return False
    return settings.ignored_reminders < BACKOFF_AFTER_IGNORED or today_local.toordinal() % 2 == 0


def _cards(count: int) -> str:
    return f"{count} card" if count == 1 else f"{count} cards"


def build_reminder_text(
    summary: ReviewSummary,
    anchor: str | None,
    template_index: int,
    weekly: str | None,
) -> str:
    template = REMINDER_TEMPLATES[template_index % len(REMINDER_TEMPLATES)]
    text = template.format(
        cards=_cards(summary.due_today + summary.new_today),
        minutes=max(summary.est_minutes, 1),
    )
    if anchor:
        text = f"{anchor[:1].upper()}{anchor[1:]} — {text[:1].lower()}{text[1:]}"
    return f"{text}\n\n{weekly}" if weekly else text


def _weekly_block(summary: ReviewSummary) -> str:
    active_days = sum(count > 0 for count in summary.heatmap[-8:-1])  # the 7 days before today
    lines = [
        "Weekly summary",
        f"Days reviewed: {active_days} of 7",
        f"Learned: +{summary.learned_delta_7d}",
    ]
    if summary.retention_30d is not None:
        lines.append(f"30-day retention: {round(summary.retention_30d * 100)}%")
    return "\n".join(lines)


def _reviewed_since(session: Session, since: datetime) -> bool:
    query = select(ReviewLogEntry.id).where(ReviewLogEntry.reviewed_at >= since).limit(1)
    return session.scalar(query) is not None


async def send_reminder_if_due(
    session_factory: Callable[[], Session], bot: Bot, now: datetime
) -> bool:
    now = as_utc(now)
    with session_factory() as session:
        settings = get_app_settings(session)
        tz = ZoneInfo(settings.timezone)
        now_local = now.astimezone(tz)
        today = (now_local - timedelta(hours=DAY_START_HOUR)).date()

        def day_start(day: date) -> datetime:
            return datetime.combine(day, time(DAY_START_HOUR), tzinfo=tz).astimezone(UTC)

        reviewed_today = _reviewed_since(session, day_start(today))
        last = settings.last_reminder_on
        # Logs on the reminder's day all follow it: it is only sent before any review that day.
        answered = last is not None and _reviewed_since(session, day_start(last))
        summary = build_summary(session, settings, now)

        if answered:
            settings.ignored_reminders = 0
        elif last is not None and last < today:
            # Saved only together with a new reminder, so idle ticks never count it twice.
            settings.ignored_reminders += 1

        due_total = summary.due_today + summary.new_today
        if not should_send(settings, now_local, reviewed_today, due_total, today):
            if answered:
                session.commit()
            return False

        weekly = _weekly_block(summary) if today.weekday() == 0 else None
        text = build_reminder_text(summary, settings.reminder_anchor, today.toordinal(), weekly)
        config = get_settings()
        await bot.send_message(
            config.telegram_allowed_user_id,
            text,
            reply_markup=_web_app_keyboard(
                "Review", f"{config.resolved_telegram_webapp_url}?view=review"
            ),
        )
        settings.last_reminder_on = today
        session.commit()
        return True


async def run_reminder_loop(
    session_factory: Callable[[], Session], bot: Bot, interval_seconds: int = 300
) -> None:
    # ponytail: single uvicorn worker; use an atomic DB claim if workers > 1
    while True:
        try:
            await send_reminder_if_due(session_factory, bot, datetime.now(UTC))
        except Exception:
            logger.exception("Reminder check failed")
        await asyncio.sleep(interval_seconds)
