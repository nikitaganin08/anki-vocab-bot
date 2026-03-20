from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from aiogram.types import InlineKeyboardMarkup

import app.models.anki_sync_attempt as anki_sync_attempt_model  # noqa: F401
from app.bot.handler import (
    TelegramAdminWebAppHandler,
    TelegramDescriptionLookupHandler,
    TelegramTextHandler,
)
from app.bot.rate_limiter import InMemoryRateLimiter
from app.models.card import Card, EntryType, SourceLanguage
from app.schemas.description_lookup import (
    FoundDescriptionLookupResponse,
    RejectedDescriptionLookupResponse,
)
from app.schemas.llm import RejectedLlmResponse
from app.services.card_service import CardServiceResult, CardServiceUpstreamError


@dataclass
class StubUser:
    id: int


@dataclass
class StubMessage:
    text: str
    user_id: int | None
    answers: list[str] = field(default_factory=list)
    parse_modes: list[str | None] = field(default_factory=list)
    reply_markups: list[InlineKeyboardMarkup | None] = field(default_factory=list)

    @property
    def from_user(self) -> StubUser | None:
        if self.user_id is None:
            return None
        return StubUser(id=self.user_id)

    async def answer(
        self,
        text: str,
        parse_mode: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        self.answers.append(text)
        self.parse_modes.append(parse_mode)
        self.reply_markups.append(reply_markup)


@dataclass
class ApplySourceTextStub:
    result: CardServiceResult | None = None
    error: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def __call__(self, source_text: str) -> CardServiceResult:
        self.calls.append(source_text)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@dataclass
class LookupCandidatesStub:
    result: object | None = None
    error: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def __call__(self, description: str) -> object:
        self.calls.append(description)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def make_card() -> Card:
    return Card(
        source_text="take off",
        source_language=SourceLanguage.EN,
        entry_type=EntryType.PHRASAL_VERB,
        canonical_text="take off",
        canonical_text_normalized="take off",
        transcription="teik of",
        translation_variants_json=["взлетать", "снимать", "резко начинаться"],
        explanation="To leave the ground or remove clothing.",
        examples_json=[
            "The plane will take off in ten minutes.",
            "Please take off your shoes.",
            "Sales started to take off in spring.",
        ],
        frequency=4,
        frequency_note="Common in everyday English.",
        eligible_for_anki=True,
        llm_model="test-model",
    )


def test_handler_ignores_messages_from_other_users() -> None:
    stub = ApplySourceTextStub(result=CardServiceResult(status="created", card=make_card()))
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="take off", user_id=7)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == []
    assert message.answers == []


def test_handler_rejects_too_long_input_before_service_call() -> None:
    stub = ApplySourceTextStub(result=CardServiceResult(status="created", card=make_card()))
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="one two three four five six seven eight nine", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == []
    assert message.answers == ["Please send up to 8 words."]


def test_handler_maps_created_result() -> None:
    stub = ApplySourceTextStub(result=CardServiceResult(status="created", card=make_card()))
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="  take   off ", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == ["take off"]
    assert len(message.answers) == 1
    assert message.answers[0].startswith("✅ Added to dictionary\n\n🔍 Word: <b>take off</b>")
    assert message.parse_modes == ["HTML"]


def test_handler_maps_duplicate_result() -> None:
    stub = ApplySourceTextStub(
        result=CardServiceResult(status="duplicate_source", card=make_card())
    )
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="take off", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == ["take off"]
    assert len(message.answers) == 1
    assert message.answers[0].startswith("ℹ️ Already in dictionary\n\n🔍 Word: <b>take off</b>")
    assert message.parse_modes == ["HTML"]


def test_handler_returns_rejected_message() -> None:
    rejection = RejectedLlmResponse.model_validate(
        {
            "accepted": False,
            "reason": "not_lexical_unit",
            "message_for_user": "This looks like a free-form sentence.",
        }
    )
    stub = ApplySourceTextStub(result=CardServiceResult(status="rejected", rejection=rejection))
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="this is a sentence", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == ["this is a sentence"]
    assert message.answers == ["This looks like a free-form sentence."]
    assert message.parse_modes == [None]


def test_handler_surfaces_upstream_error_message() -> None:
    stub = ApplySourceTextStub(
        error=CardServiceUpstreamError(
            "failed",
            code="openrouter_timeout",
            user_message="Model timed out. Please try again.",
        )
    )
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="take off", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == ["take off"]
    assert message.answers == ["Model timed out. Please try again."]
    assert message.parse_modes == [None]


def test_handler_enforces_rate_limit() -> None:
    stub = ApplySourceTextStub(result=CardServiceResult(status="created", card=make_card()))
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(limit=1, window_seconds=60.0),
    )
    first = StubMessage(text="take off", user_id=42)
    second = StubMessage(text="take off", user_id=42)

    asyncio.run(handler.handle_message(first))
    asyncio.run(handler.handle_message(second))

    assert stub.calls == ["take off"]
    assert second.answers == ["Rate limit reached: max 5 requests per minute."]
    assert second.parse_modes == [None]


def test_text_handler_ignores_command_messages() -> None:
    stub = ApplySourceTextStub(result=CardServiceResult(status="created", card=make_card()))
    handler = TelegramTextHandler(
        allowed_user_id=42,
        apply_source_text=stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="/admin", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert stub.calls == []
    assert message.answers == []


def test_admin_handler_sends_webapp_button() -> None:
    handler = TelegramAdminWebAppHandler(
        allowed_user_id=42,
        webapp_url="https://bot.example.com/telegram/webapp",
    )
    message = StubMessage(text="/admin", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert message.answers == ["Open the dictionary panel inside Telegram."]
    markup = message.reply_markups[0]
    assert markup is not None
    assert markup.inline_keyboard[0][0].text == "Open admin panel"
    assert markup.inline_keyboard[0][0].web_app is not None
    assert markup.inline_keyboard[0][0].web_app.url == "https://bot.example.com/telegram/webapp"


def test_admin_handler_ignores_other_users() -> None:
    handler = TelegramAdminWebAppHandler(
        allowed_user_id=42,
        webapp_url="https://bot.example.com/telegram/webapp",
    )
    message = StubMessage(text="/admin", user_id=7)

    asyncio.run(handler.handle_message(message))

    assert message.answers == []
    assert message.reply_markups == []


def test_description_lookup_handler_returns_candidate_list() -> None:
    lookup_stub = LookupCandidatesStub(
        result=FoundDescriptionLookupResponse.model_validate(
            {"found": True, "candidates": ["shovel away", "clear away", "remove"]}
        )
    )
    handler = TelegramDescriptionLookupHandler(
        allowed_user_id=42,
        lookup_candidates_from_description=lookup_stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="/find to move snow away with a shovel", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert lookup_stub.calls == ["to move snow away with a shovel"]
    assert message.answers == [
        "Possible matches:\n"
        "1. shovel away\n"
        "2. clear away\n"
        "3. remove\n\n"
        "Send one of these back if you want to add a card."
    ]
    assert message.parse_modes == [None]


def test_description_lookup_handler_returns_lookup_rejection() -> None:
    rejection = RejectedDescriptionLookupResponse.model_validate(
        {
            "found": False,
            "message_for_user": "I could not infer one clear lexical unit from that description.",
        }
    )
    lookup_stub = LookupCandidatesStub(result=rejection)
    handler = TelegramDescriptionLookupHandler(
        allowed_user_id=42,
        lookup_candidates_from_description=lookup_stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="/find something vague and ambiguous", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert lookup_stub.calls == ["something vague and ambiguous"]
    assert message.answers == ["I could not infer one clear lexical unit from that description."]
    assert message.parse_modes == [None]


def test_description_lookup_handler_requires_description_argument() -> None:
    lookup_stub = LookupCandidatesStub(
        result=FoundDescriptionLookupResponse.model_validate(
            {"found": True, "candidates": ["shovel away", "clear away", "remove"]}
        )
    )
    handler = TelegramDescriptionLookupHandler(
        allowed_user_id=42,
        lookup_candidates_from_description=lookup_stub,
        rate_limiter=InMemoryRateLimiter(),
    )
    message = StubMessage(text="/find", user_id=42)

    asyncio.run(handler.handle_message(message))

    assert lookup_stub.calls == []
    assert message.answers == ["Use /find followed by a short description."]
    assert message.parse_modes == [None]
