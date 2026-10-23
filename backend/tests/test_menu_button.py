from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from aiogram.types import MenuButtonDefault, MenuButtonWebApp, WebAppInfo

import app.bot.runtime as runtime_mod
from app.bot.runtime import ensure_menu_button

from .conftest import TELEGRAM_ALLOWED_USER_ID

URL = "https://example.test/anki/telegram/webapp"


@dataclass
class SettingsStub:
    telegram_allowed_user_id: int | None = TELEGRAM_ALLOWED_USER_ID
    resolved_telegram_webapp_url: str | None = URL


@dataclass
class FakeBot:
    current: Any
    set_calls: list[dict[str, Any]] = field(default_factory=list)

    async def get_chat_menu_button(self, chat_id: int) -> Any:
        return self.current

    async def set_chat_menu_button(self, chat_id: int, menu_button: Any) -> None:
        self.set_calls.append({"chat_id": chat_id, "menu_button": menu_button})


def _run(bot: FakeBot, monkeypatch: pytest.MonkeyPatch, settings: SettingsStub | None = None):
    monkeypatch.setattr(runtime_mod, "get_settings", lambda: settings or SettingsStub())
    asyncio.run(ensure_menu_button(bot))  # type: ignore[arg-type]


def test_menu_button_is_set_for_the_owner_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = FakeBot(current=MenuButtonDefault())

    _run(bot, monkeypatch)

    assert len(bot.set_calls) == 1
    assert bot.set_calls[0]["chat_id"] == TELEGRAM_ALLOWED_USER_ID
    assert bot.set_calls[0]["menu_button"].web_app.url == URL


def test_menu_button_is_left_alone_when_already_right(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = FakeBot(
        current=MenuButtonWebApp(text="Wordloop", web_app=WebAppInfo(url=URL)),
    )

    _run(bot, monkeypatch)

    assert bot.set_calls == []


def test_menu_button_needs_a_url_and_an_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = FakeBot(current=MenuButtonDefault())

    _run(bot, monkeypatch, SettingsStub(resolved_telegram_webapp_url=None))
    _run(bot, monkeypatch, SettingsStub(telegram_allowed_user_id=None))

    assert bot.set_calls == []
