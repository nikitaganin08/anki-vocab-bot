from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.openrouter import (
    OpenRouterError,
    OpenRouterProtocolError,
    OpenRouterTimeoutError,
    OpenRouterTransportError,
)
from app.models.card import Card
from app.schemas.llm import AcceptedLlmResponse, RejectedLlmResponse

WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_source_text(value: str) -> str:
    normalized = WHITESPACE_PATTERN.sub(" ", value.strip())
    if not normalized:
        raise ValueError("source_text must not be empty")
    return normalized


def tokenize_source_text(value: str) -> list[str]:
    return normalize_source_text(value).split(" ")


def normalize_canonical_text(value: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", value.strip().lower())


class CardGenerator(Protocol):
    def generate_card(self, source_text: str) -> AcceptedLlmResponse | RejectedLlmResponse:
        ...


class CardServiceUpstreamError(RuntimeError):
    def __init__(self, message: str, *, code: str, user_message: str) -> None:
        super().__init__(message)
        self.code = code
        self.user_message = user_message


@dataclass(slots=True)
class CardServiceResult:
    status: Literal["created", "duplicate_source", "duplicate_canonical", "rejected"]
    card: Card | None = None
    rejection: RejectedLlmResponse | None = None


@dataclass(slots=True)
class CardService:
    session: Session
    generator: CardGenerator

    def apply_source_text(self, raw_source_text: str) -> CardServiceResult:
        source_text = normalize_source_text(raw_source_text)

        existing_source = self.session.scalar(select(Card).where(Card.source_text == source_text))
        if existing_source is not None:
            return CardServiceResult(status="duplicate_source", card=existing_source)

        try:
            llm_result = self.generator.generate_card(source_text)
        except OpenRouterTimeoutError as exc:
            raise CardServiceUpstreamError(
                "LLM request timed out",
                code=exc.code,
                user_message=exc.user_message,
            ) from exc
        except OpenRouterTransportError as exc:
            raise CardServiceUpstreamError(
                "LLM transport failed",
                code=exc.code,
                user_message=exc.user_message,
            ) from exc
        except OpenRouterProtocolError as exc:
            raise CardServiceUpstreamError(
                "LLM returned invalid contract payload",
                code=exc.code,
                user_message=exc.user_message,
            ) from exc
        except OpenRouterError as exc:
            raise CardServiceUpstreamError(
                "LLM request failed",
                code=exc.code,
                user_message=exc.user_message,
            ) from exc

        if isinstance(llm_result, RejectedLlmResponse):
            return CardServiceResult(status="rejected", rejection=llm_result)

        llm_source_text = normalize_source_text(llm_result.source_text)
        if llm_source_text != source_text:
            raise CardServiceUpstreamError(
                "LLM response source_text does not match request",
                code="openrouter_source_text_mismatch",
                user_message=(
                    "The language model returned an inconsistent response. Please try again."
                ),
            )

        canonical_text_normalized = normalize_canonical_text(llm_result.canonical_text)
        existing_canonical = self.session.scalar(
            select(Card).where(Card.canonical_text_normalized == canonical_text_normalized)
        )
        if existing_canonical is not None:
            return CardServiceResult(status="duplicate_canonical", card=existing_canonical)

        card = Card(
            source_text=source_text,
            source_language=llm_result.source_language,
            entry_type=llm_result.entry_type,
            canonical_text=llm_result.canonical_text,
            canonical_text_normalized=canonical_text_normalized,
            transcription=llm_result.transcription,
            translation_variants_json=llm_result.translation_variants,
            explanation=llm_result.explanation,
            examples_json=llm_result.examples,
            frequency=llm_result.frequency,
            frequency_note=llm_result.frequency_note,
            eligible_for_anki=llm_result.frequency > 2,
            llm_model=llm_result.llm_model,
        )
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return CardServiceResult(status="created", card=card)
