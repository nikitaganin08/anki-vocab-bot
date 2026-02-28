from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.clients.openrouter import (
    OpenRouterProtocolError,
    OpenRouterTimeoutError,
    OpenRouterTransportError,
)
from app.db.base import Base
from app.models.card import Card
from app.schemas.llm import AcceptedLlmResponse, RejectedLlmResponse
from app.services.card_service import (
    CardService,
    CardServiceUpstreamError,
    normalize_source_text,
    tokenize_source_text,
)


@dataclass
class FakeGenerator:
    result: AcceptedLlmResponse | RejectedLlmResponse | None = None
    error: Exception | None = None
    call_count: int = 0

    def generate_card(self, source_text: str) -> AcceptedLlmResponse | RejectedLlmResponse:
        self.call_count += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_accepted_response(**overrides: object) -> AcceptedLlmResponse:
    payload = {
        "accepted": True,
        "source_text": "take off",
        "source_language": "en",
        "entry_type": "phrasal_verb",
        "canonical_text": "take off",
        "canonical_text_normalized": "take off",
        "transcription": "teik of",
        "translation_variants": ["взлетать", "снимать", "резко начинаться"],
        "explanation": "To leave the ground or to remove clothing.",
        "examples": [
            "The plane will take off in ten minutes.",
            "Please take off your shoes at the door.",
            "Her new business started to take off this year.",
        ],
        "frequency": 4,
        "frequency_note": "Common in everyday English.",
        "llm_model": "test-model",
    }
    payload.update(overrides)
    return AcceptedLlmResponse.model_validate(payload)


def test_normalize_and_tokenize_source_text() -> None:
    assert normalize_source_text("  take   off  ") == "take off"
    assert tokenize_source_text("  take   off  ") == ["take", "off"]


def test_card_service_creates_new_card(session: Session) -> None:
    generator = FakeGenerator(result=make_accepted_response())
    service = CardService(session=session, generator=generator)

    result = service.apply_source_text("  take   off  ")

    assert result.status == "created"
    assert result.card is not None
    assert result.card.eligible_for_anki is True
    assert result.card.canonical_text_normalized == "take off"
    assert generator.call_count == 1


def test_card_service_returns_duplicate_source_without_llm_call(session: Session) -> None:
    existing = Card(
        source_text="take off",
        source_language="en",
        entry_type="phrasal_verb",
        canonical_text="take off",
        canonical_text_normalized="take off",
        transcription=None,
        translation_variants_json=["взлетать", "снимать"],
        explanation="To leave the ground.",
        examples_json=["A", "B", "C"],
        frequency=2,
        frequency_note=None,
        eligible_for_anki=False,
        llm_model="seed",
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    generator = FakeGenerator(result=make_accepted_response())
    service = CardService(session=session, generator=generator)

    result = service.apply_source_text("take off")

    assert result.status == "duplicate_source"
    assert result.card is not None
    assert result.card.id == existing.id
    assert generator.call_count == 0


def test_card_service_returns_duplicate_canonical_after_llm_call(session: Session) -> None:
    existing = Card(
        source_text="remove clothes",
        source_language="en",
        entry_type="expression",
        canonical_text="take off",
        canonical_text_normalized="take off",
        transcription=None,
        translation_variants_json=["снимать", "сбрасывать"],
        explanation="To remove clothing.",
        examples_json=["A", "B", "C"],
        frequency=2,
        frequency_note=None,
        eligible_for_anki=False,
        llm_model="seed",
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    generator = FakeGenerator(
        result=make_accepted_response(
            source_text="take the shoes off",
            canonical_text="take off",
            canonical_text_normalized="take off",
        )
    )
    service = CardService(session=session, generator=generator)

    result = service.apply_source_text("take the shoes off")

    assert result.status == "duplicate_canonical"
    assert result.card is not None
    assert result.card.id == existing.id
    assert generator.call_count == 1


def test_card_service_returns_rejected_without_persisting(session: Session) -> None:
    generator = FakeGenerator(
        result=RejectedLlmResponse.model_validate(
            {
                "accepted": False,
                "reason": "not_lexical_unit",
                "message_for_user": (
                    "This looks like a free-form phrase, not a stable lexical unit."
                ),
            }
        )
    )
    service = CardService(session=session, generator=generator)

    result = service.apply_source_text("this is a sentence")

    assert result.status == "rejected"
    assert result.rejection is not None
    assert session.scalar(select(Card)) is None


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (
            OpenRouterTimeoutError(
                "timeout",
                code="openrouter_timeout",
                user_message="The language model timed out. Please try again.",
            ),
            "openrouter_timeout",
        ),
        (
            OpenRouterTransportError(
                "transport",
                code="openrouter_transport_error",
                user_message="The language model is temporarily unavailable. Please try again.",
            ),
            "openrouter_transport_error",
        ),
        (
            OpenRouterProtocolError(
                "protocol",
                code="openrouter_invalid_contract",
                user_message=(
                    "The language model returned an invalid card response. Please try again."
                ),
            ),
            "openrouter_invalid_contract",
        ),
    ],
)
def test_card_service_surfaces_upstream_errors(
    session: Session,
    error: Exception,
    expected_code: str,
) -> None:
    generator = FakeGenerator(error=error)
    service = CardService(session=session, generator=generator)

    with pytest.raises(CardServiceUpstreamError) as exc_info:
        service.apply_source_text("take off")

    assert exc_info.value.code == expected_code
