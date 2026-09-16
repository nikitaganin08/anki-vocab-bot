from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterClient
from app.models.card import Card
from app.schemas.llm import RejectedLlmResponse

WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_source_text(value: str) -> str:
    normalized = WHITESPACE_PATTERN.sub(" ", value.strip())
    if not normalized:
        raise ValueError("source_text must not be empty")
    return normalized


def normalize_canonical_text(value: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", value.strip().lower())


@dataclass(slots=True)
class CardServiceResult:
    status: Literal["created", "duplicate_source", "duplicate_canonical", "rejected"]
    card: Card | None = None
    rejection: RejectedLlmResponse | None = None


def apply_source_text(
    session: Session,
    openrouter_client: OpenRouterClient,
    raw_source_text: str,
) -> CardServiceResult:
    source_text = normalize_source_text(raw_source_text)

    existing_source = session.scalar(select(Card).where(Card.source_text == source_text))
    if existing_source is not None:
        return CardServiceResult(status="duplicate_source", card=existing_source)

    llm_result = openrouter_client.generate_card(source_text)

    if isinstance(llm_result, RejectedLlmResponse):
        return CardServiceResult(status="rejected", rejection=llm_result)

    canonical_text_normalized = normalize_canonical_text(llm_result.canonical_text)
    existing_canonical = session.scalar(
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
        word_family_json=[item.model_dump() for item in llm_result.word_family],
        word_family_backfilled=True,
        explanation=llm_result.explanation,
        examples_json=llm_result.examples,
        frequency=llm_result.frequency,
        frequency_note=llm_result.frequency_note,
        eligible_for_anki=llm_result.frequency > 2,
        llm_model=openrouter_client.model,
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    return CardServiceResult(status="created", card=card)
