from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.bot.handler import TelegramTextHandler
from app.bot.rate_limiter import InMemoryRateLimiter
from app.models.card import Card, EntryType, SourceLanguage
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

    @property
    def from_user(self) -> StubUser | None:
        if self.user_id is None:
            return None
        return StubUser(id=self.user_id)

    async def answer(self, text: str) -> None:
        self.answers.append(text)


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
    assert message.answers[0].startswith("Added to dictionary.\n\nWord: take off")


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
    assert message.answers[0].startswith("Already in dictionary.\n\nWord: take off")


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
