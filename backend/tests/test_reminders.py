from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from fsrs import Card as FsrsCard
from fsrs import State
from sqlalchemy.orm import Session, sessionmaker

import app.main as main_mod
import app.services.reminders as reminders_mod
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings
from app.services.reminders import (
    REMINDER_TEMPLATES,
    build_reminder_text,
    send_reminder_if_due,
    should_send,
)
from app.services.review_stats import ReviewSummary

from .conftest import TELEGRAM_ALLOWED_USER_ID, make_card

MOSCOW = ZoneInfo("Europe/Moscow")
TUESDAY = date(2026, 10, 20)  # odd ordinal
WEDNESDAY = date(2026, 10, 21)  # even ordinal


def _moscow(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=MOSCOW).astimezone(UTC)


def _summary(**overrides: Any) -> ReviewSummary:
    values: dict[str, Any] = dict(
        due_today=10,
        new_today=2,
        est_minutes=4,
        backlog=0,
        retention_30d=None,
        learned_total=0,
        learned_delta_7d=0,
        streak_days=0,
        best_streak_days=0,
        heatmap=[0] * 98,
        forecast_tomorrow=0,
        forecast_week_avg=0,
    )
    values.update(overrides)
    return ReviewSummary(**values)


def _should_send(session: Session, *, day: date = TUESDAY, hour: int = 11, **kwargs: Any) -> bool:
    settings = get_app_settings(session)
    now_local = datetime(day.year, day.month, day.day, hour, tzinfo=MOSCOW)
    return should_send(
        settings,
        now_local,
        kwargs.get("reviewed_today", False),
        kwargs.get("due_total", 12),
        day,
    )


def test_not_before_hour(session: Session) -> None:
    assert not _should_send(session, hour=9)
    assert _should_send(session, hour=10)


def test_not_twice_same_day(session: Session) -> None:
    get_app_settings(session).last_reminder_on = TUESDAY
    assert not _should_send(session)
    assert _should_send(session, day=TUESDAY + timedelta(days=2))


def test_not_when_reviewed_today(session: Session) -> None:
    assert not _should_send(session, reviewed_today=True)


def test_not_when_nothing_due(session: Session) -> None:
    assert not _should_send(session, due_total=0)


def test_backoff_every_other_day_after_three_ignored(session: Session) -> None:
    settings = get_app_settings(session)
    settings.ignored_reminders = 2
    assert _should_send(session, day=TUESDAY)
    settings.ignored_reminders = 3
    assert not _should_send(session, day=TUESDAY)
    assert _should_send(session, day=WEDNESDAY)


def test_paused_after_seven_ignored(session: Session) -> None:
    get_app_settings(session).ignored_reminders = 7
    assert not _should_send(session, day=TUESDAY)
    assert not _should_send(session, day=WEDNESDAY)


def test_text_has_counts_and_no_streak_word() -> None:
    assert len(REMINDER_TEMPLATES) == 12
    for index in range(len(REMINDER_TEMPLATES)):
        text = build_reminder_text(_summary(), None, None, index, None)
        assert "12 карточек" in text
        assert "4 мин" in text
        assert "серия" not in text.casefold()
        assert "streak" not in text.casefold()

    assert "1 карточка" in build_reminder_text(
        _summary(due_today=1, new_today=0), None, None, 0, None
    )
    anchored = build_reminder_text(_summary(), "после кофе", ("___ smoking", "бросить"), 0, None)
    assert anchored.startswith("После кофе — ")
    assert "___ smoking — бросить" in anchored


@dataclass
class FakeBot:
    sent: list[dict[str, Any]] = field(default_factory=list)

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> None:
        self.sent.append({"chat_id": chat_id, "text": text, **kwargs})


@pytest.fixture
def session_factory(session: Session, monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    monkeypatch.setattr(
        reminders_mod,
        "get_settings",
        lambda: SimpleNamespace(
            telegram_allowed_user_id=TELEGRAM_ALLOWED_USER_ID,
            resolved_telegram_webapp_url="https://example.test/webapp",
        ),
    )
    return sessionmaker(bind=session.get_bind(), expire_on_commit=False)


def _send(factory: sessionmaker[Session], bot: FakeBot, now: datetime) -> bool:
    return asyncio.run(send_reminder_if_due(factory, bot, now))


def test_send_if_due_updates_last_reminder_on(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    session.add(make_card())  # one new learning card
    session.commit()
    bot = FakeBot()

    assert not _send(session_factory, bot, _moscow(20, 9))
    assert _send(session_factory, bot, _moscow(20, 11))
    assert not _send(session_factory, bot, _moscow(20, 11, 5))

    assert len(bot.sent) == 1
    message = bot.sent[0]
    assert message["chat_id"] == TELEGRAM_ALLOWED_USER_ID
    assert "1 карточка" in message["text"]
    assert "Итоги недели" not in message["text"]
    button = message["reply_markup"].inline_keyboard[0][0]
    assert button.text == "Повторить"
    assert button.web_app.url == "https://example.test/webapp?view=review"
    session.expire_all()
    assert get_app_settings(session).last_reminder_on == TUESDAY


def test_monday_includes_weekly_block(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    now = _moscow(19, 11)  # Monday
    card = make_card(
        chunks_json=[
            {"text": "give up smoking", "target": "give up", "translation": "бросить курить"}
        ],
        srs_state="review",
        srs_due_at=now - timedelta(hours=1),
    )
    session.add(card)
    session.commit()
    card.srs_card_json = FsrsCard(
        card_id=card.id,
        state=State.Review,
        step=None,
        stability=10.0,
        difficulty=5.0,
        due=now - timedelta(hours=1),
        last_review=now - timedelta(days=10),
    ).to_json()
    get_app_settings(session).reminder_anchor = "после кофе"
    session.commit()
    bot = FakeBot()

    assert _send(session_factory, bot, now)

    text = bot.sent[0]["text"]
    assert text.startswith("После кофе — ")
    assert "Разминка: ___ smoking — бросить курить" in text
    assert "Итоги недели" in text


def _log(session: Session, reviewed_at: datetime) -> None:
    session.add(
        ReviewLogEntry(
            card_id=1,
            reviewed_at=reviewed_at,
            rating=3,
            auto_rating=3,
            overridden=False,
            prompt_kind="translation",
            prompt_index=0,
            typed_answer="take off",
            verdict="correct",
            hint_used=False,
            response_ms=1000,
            state_before=None,
        )
    )
    session.commit()


def test_ignored_reminders_counted_once_and_reset_by_review(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    session.add(make_card())
    session.commit()
    bot = FakeBot()

    assert _send(session_factory, bot, _moscow(20, 11))
    assert _send(session_factory, bot, _moscow(21, 11))  # Tuesday's reminder went unanswered
    assert not _send(session_factory, bot, _moscow(21, 11, 5))
    session.expire_all()
    assert get_app_settings(session).ignored_reminders == 1

    _log(session, _moscow(21, 12))
    assert not _send(session_factory, bot, _moscow(21, 12, 5))
    session.expire_all()
    assert get_app_settings(session).ignored_reminders == 0


def test_lifespan_starts_reminder_loop_unless_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[object] = []

    async def fake_loop(_session_factory: object, bot: object) -> None:
        started.append(bot)
        await asyncio.Event().wait()

    monkeypatch.setattr(main_mod, "run_reminder_loop", fake_loop)
    monkeypatch.setattr(main_mod, "get_settings", lambda: SimpleNamespace(telegram_bot_token="t"))
    monkeypatch.setattr(main_mod, "get_bot_runtime", lambda: SimpleNamespace(bot="bot"))

    with TestClient(main_mod.app) as client:
        client.get("/api/health")
    assert started == []  # conftest sets DISABLE_REMINDERS=1

    monkeypatch.delenv("DISABLE_REMINDERS")
    with TestClient(main_mod.app) as client:
        client.get("/api/health")
    assert started == ["bot"]
