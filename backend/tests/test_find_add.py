from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from aiogram.types import InlineKeyboardMarkup

from app.bot.handler import TelegramAddCallbackHandler, build_candidates_keyboard
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterError
from app.services.card_service import CardServiceResult

from .conftest import make_card


@dataclass
class StubMessage:
    answers: list[tuple[str, str | None, InlineKeyboardMarkup | None]] = field(default_factory=list)

    async def answer(
        self,
        text: str,
        parse_mode: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        self.answers.append((text, parse_mode, reply_markup))


@dataclass
class StubUser:
    id: int


@dataclass
class StubCallback:
    data: str
    user_id: int = 42
    message: StubMessage = field(default_factory=StubMessage)
    toasts: list[tuple[str | None, bool]] = field(default_factory=list)

    @property
    def from_user(self) -> StubUser:
        return StubUser(id=self.user_id)

    async def answer(self, text: str | None = None, show_alert: bool = False) -> None:
        self.toasts.append((text, show_alert))


@dataclass
class ApplyStub:
    result: CardServiceResult | Exception
    calls: list[str] = field(default_factory=list)

    def __call__(self, source_text: str) -> CardServiceResult:
        self.calls.append(source_text)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _run(callback: StubCallback, apply: ApplyStub, limiter: InMemoryRateLimiter | None = None):
    handler = TelegramAddCallbackHandler(
        allowed_user_id=42,
        apply_source_text=apply,
        rate_limiter=limiter or InMemoryRateLimiter(),
    )
    asyncio.run(handler.handle_callback(callback))


def test_add_button_adds_the_candidate_and_writes_the_card_to_the_chat() -> None:
    apply = ApplyStub(CardServiceResult(status="created", card=make_card(id=3)))
    callback = StubCallback(data="add:shovel away")

    _run(callback, apply)

    assert apply.calls == ["shovel away"]
    assert callback.toasts == [("Adding…", False)]
    text, parse_mode, markup = callback.message.answers[0]
    assert text.startswith("✅ Added to dictionary")
    assert parse_mode == "HTML"
    assert markup is None
    assert len(callback.message.answers) == 1


def test_add_button_for_a_rare_word_also_asks_to_learn_it() -> None:
    card = make_card(id=3, frequency=2, is_learning=False, common_synonym="hug")
    callback = StubCallback(data="add:cuddle")

    _run(callback, ApplyStub(CardServiceResult(status="created", card=card)))

    prompt, _, markup = callback.message.answers[1]
    assert "Rare word (2/10)" in prompt
    assert markup is not None
    assert [b.callback_data for row in markup.inline_keyboard for b in row] == [
        "learn:3",
        "skip:3",
        "alt:3",
    ]


def test_add_button_reports_llm_failures_and_ignores_strangers() -> None:
    failed = StubCallback(data="add:remove")
    _run(failed, ApplyStub(OpenRouterError("boom", code="x", user_message="Try again later.")))
    assert failed.message.answers == [("Try again later.", None, None)]

    stranger = StubCallback(data="add:remove", user_id=7)
    apply = ApplyStub(CardServiceResult(status="created", card=make_card(id=3)))
    _run(stranger, apply)
    assert apply.calls == [] and stranger.toasts == []


def test_add_button_rejects_invalid_text_and_respects_the_rate_limit() -> None:
    long_text = StubCallback(data="add:" + "word " * 9)
    apply = ApplyStub(CardServiceResult(status="created", card=make_card(id=3)))
    _run(long_text, apply)
    assert apply.calls == [] and long_text.toasts[0][1] is True

    limiter = InMemoryRateLimiter(limit=0)
    limited = StubCallback(data="add:remove")
    _run(limited, apply, limiter)
    assert apply.calls == [] and limited.toasts[0][1] is True


def test_candidate_buttons_skip_words_that_do_not_fit_callback_data() -> None:
    too_long = "x" * 70
    markup = build_candidates_keyboard(["remove", too_long])

    assert markup is not None
    assert [row[0].callback_data for row in markup.inline_keyboard] == ["add:remove"]
    assert build_candidates_keyboard([too_long]) is None
