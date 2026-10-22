from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

import app.bot.notify as notify_mod
from app.bot.formatter import format_rare_word_prompt
from app.bot.handler import SynonymSwap, TelegramLearnCallbackHandler, build_learn_keyboard
from app.services.card_service import CardServiceResult

from .conftest import TelegramSettingsStub, make_card
from .test_api import _make_accepted_llm_response


def test_synonym_is_kept_and_dropped_when_equal_to_the_word() -> None:
    data = _make_accepted_llm_response("cuddle", entry_type="word").model_dump()
    data["common_synonym"] = "  hug "
    assert type(_make_accepted_llm_response("cuddle")).model_validate(data).common_synonym == "hug"

    data["common_synonym"] = "Cuddle"
    assert type(_make_accepted_llm_response("cuddle")).model_validate(data).common_synonym is None
    data["common_synonym"] = "обнимать"
    assert type(_make_accepted_llm_response("cuddle")).model_validate(data).common_synonym is None


def test_rare_prompt_offers_the_synonym() -> None:
    card = make_card(frequency=4, canonical_text="cuddle", common_synonym="hug", id=7)

    assert "A more common word with the same meaning: hug." in format_rare_word_prompt(card)
    rows = build_learn_keyboard(7, "hug").inline_keyboard
    assert [b.callback_data for row in rows for b in row] == ["learn:7", "skip:7", "alt:7"]
    assert len(build_learn_keyboard(7).inline_keyboard) == 1


@dataclass
class StubMessage:
    edits: list[str] = field(default_factory=list)

    async def edit_text(self, text: str) -> None:
        self.edits.append(text)


@dataclass
class StubFrom:
    id: int = 42


@dataclass
class StubCallback:
    data: str
    message: StubMessage = field(default_factory=StubMessage)
    from_user: StubFrom = field(default_factory=StubFrom)
    alerts: list[str] = field(default_factory=list)

    async def answer(self, text: str | None = None, show_alert: bool = False) -> None:
        if text:
            self.alerts.append(text)


@pytest.mark.parametrize(
    ("swap", "expected"),
    [
        (SynonymSwap("cuddle", "hug", "created"), "Learning “hug” instead of “cuddle”"),
        (
            SynonymSwap("cuddle", "hug", "duplicate_canonical"),
            "“hug” is already in your dictionary. Removed “cuddle”.",
        ),
        (
            SynonymSwap("cuddle", None, "rejected"),
            "Could not add the synonym. Kept “cuddle” as not learning.",
        ),
        (None, "Card not found"),
    ],
)
def test_alt_callback_swaps_the_word(swap: SynonymSwap | None, expected: str) -> None:
    handler = TelegramLearnCallbackHandler(
        allowed_user_id=42, set_learning=lambda *_: None, swap_for_synonym=lambda _id: swap
    )
    callback = StubCallback(data="alt:7")

    asyncio.run(handler.handle_callback(callback))

    assert callback.message.edits == [expected]


def test_notify_sends_the_card_and_the_rare_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    posts: list[dict[str, Any]] = []

    def fake_post(url: str, json: dict[str, Any], timeout: int) -> httpx.Response:
        posts.append({"url": url, **json})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(notify_mod, "get_settings", lambda: TelegramSettingsStub())
    monkeypatch.setattr(notify_mod.httpx, "post", fake_post)
    card = make_card(id=7, frequency=4, is_learning=False, common_synonym="hug")

    notify_mod.send_card_result(CardServiceResult(status="created", card=card))

    assert len(posts) == 2
    assert "Added to dictionary" in posts[0]["text"]
    assert posts[0]["parse_mode"] == "HTML"
    assert "Rare word (4/10)" in posts[1]["text"]
    buttons = [
        b["callback_data"] for row in posts[1]["reply_markup"]["inline_keyboard"] for b in row
    ]
    assert buttons == ["learn:7", "skip:7", "alt:7"]


def test_notify_never_raises_when_telegram_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_post(*_args: Any, **_kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(notify_mod, "get_settings", lambda: TelegramSettingsStub())
    monkeypatch.setattr(notify_mod.httpx, "post", broken_post)

    notify_mod.send_card_result(CardServiceResult(status="created", card=make_card(id=1)))
