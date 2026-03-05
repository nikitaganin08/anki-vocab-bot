from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.card import AnkiSyncStatus, EntryType, SourceLanguage


class CardResponse(BaseModel):
    id: int
    source_text: str
    source_language: SourceLanguage
    entry_type: EntryType
    canonical_text: str
    canonical_text_normalized: str
    transcription: str | None
    translation_variants: list[str]
    explanation: str
    examples: list[str]
    frequency: int
    frequency_note: str | None
    eligible_for_anki: bool
    anki_sync_status: AnkiSyncStatus
    anki_note_id: int | None
    llm_model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_card(cls, card: object) -> "CardResponse":
        from app.models.card import Card

        c: Card = card  # type: ignore[assignment]
        return cls(
            id=c.id,
            source_text=c.source_text,
            source_language=c.source_language,
            entry_type=c.entry_type,
            canonical_text=c.canonical_text,
            canonical_text_normalized=c.canonical_text_normalized,
            transcription=c.transcription,
            translation_variants=c.translation_variants_json,
            explanation=c.explanation,
            examples=c.examples_json,
            frequency=c.frequency,
            frequency_note=c.frequency_note,
            eligible_for_anki=c.eligible_for_anki,
            anki_sync_status=c.anki_sync_status,
            anki_note_id=c.anki_note_id,
            llm_model=c.llm_model,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class CardListResponse(BaseModel):
    items: list[CardResponse]
    total: int
    offset: int
    limit: int


class AnkiPendingCardResponse(BaseModel):
    id: int
    canonical_text: str
    transcription: str | None
    translation_variants: list[str]
    explanation: str
    examples: list[str]

    model_config = {"from_attributes": True}

    @classmethod
    def from_card(cls, card: object) -> "AnkiPendingCardResponse":
        from app.models.card import Card

        c: Card = card  # type: ignore[assignment]
        return cls(
            id=c.id,
            canonical_text=c.canonical_text,
            transcription=c.transcription,
            translation_variants=c.translation_variants_json,
            explanation=c.explanation,
            examples=c.examples_json,
        )


class AnkiAckRequest(BaseModel):
    card_id: int
    anki_note_id: int


class AnkiFailRequest(BaseModel):
    card_id: int
    error_message: str
