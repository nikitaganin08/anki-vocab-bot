from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterError
from app.db.base import Base
from app.models.card import Card
from app.schemas.llm import AcceptedLlmResponse, RejectedLlmResponse
from app.services.card_service import apply_source_text, normalize_source_text


@dataclass
class FakeGenerator:
    result: AcceptedLlmResponse | RejectedLlmResponse | None = None
    error: Exception | None = None
    call_count: int = 0
    model: str = "test-model"

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
        "source_language": "en",
        "entry_type": "phrasal_verb",
        "canonical_text": "take off",
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
    }
    payload.update(overrides)
    return AcceptedLlmResponse.model_validate(payload)


def test_normalize_source_text() -> None:
    assert normalize_source_text("  take   off  ") == "take off"


def test_card_service_creates_new_card(session: Session) -> None:
    generator = FakeGenerator(result=make_accepted_response(canonical_text="  Take   OFF  "))
    result = apply_source_text(session, generator, "  take   off  ")

    assert result.status == "created"
    assert result.card is not None
    assert result.card.eligible_for_anki is True
    assert result.card.source_text == "take off"
    assert result.card.canonical_text_normalized == "take off"
    assert result.card.llm_model == "test-model"
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
    result = apply_source_text(session, generator, "take off")

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

    generator = FakeGenerator(result=make_accepted_response(canonical_text="take off"))
    result = apply_source_text(session, generator, "take the shoes off")

    assert result.status == "duplicate_canonical"
    assert result.card is not None
    assert result.card.id == existing.id
    assert generator.call_count == 1


def test_card_service_returns_rejected_without_persisting(session: Session) -> None:
    generator = FakeGenerator(
        result=RejectedLlmResponse.model_validate(
            {
                "accepted": False,
                "message_for_user": (
                    "This looks like a free-form phrase, not a stable lexical unit."
                ),
            }
        )
    )
    result = apply_source_text(session, generator, "this is a sentence")

    assert result.status == "rejected"
    assert result.rejection is not None
    assert session.scalar(select(Card)) is None


def test_card_service_surfaces_upstream_error(session: Session) -> None:
    generator = FakeGenerator(
        error=OpenRouterError(
            "timeout",
            code="openrouter_timeout",
            user_message="The language model timed out. Please try again.",
        )
    )
    with pytest.raises(OpenRouterError) as exc_info:
        apply_source_text(session, generator, "take off")

    assert exc_info.value.code == "openrouter_timeout"
