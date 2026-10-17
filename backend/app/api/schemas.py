from __future__ import annotations

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.card import AnkiSyncStatus, Card, EntryType, SourceLanguage
from app.schemas.llm import CardChunk, WordFamilyItem


class CardResponse(BaseModel):
    id: int
    source_text: str
    source_language: SourceLanguage
    entry_type: EntryType
    canonical_text: str
    canonical_text_normalized: str
    transcription: str | None
    translation_variants: list[str]
    word_family: list[WordFamilyItem]
    explanation: str
    examples: list[str]
    chunks: list[CardChunk]
    frequency: int
    frequency_note: str | None
    is_learning: bool
    anki_sync_status: AnkiSyncStatus
    anki_note_id: int | None
    anki_sync_error: str | None
    llm_model: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_card(cls, c: Card) -> "CardResponse":
        return cls(
            id=c.id,
            source_text=c.source_text,
            source_language=c.source_language,
            entry_type=c.entry_type,
            canonical_text=c.canonical_text,
            canonical_text_normalized=c.canonical_text_normalized,
            transcription=c.transcription,
            translation_variants=c.translation_variants_json,
            word_family=c.word_family_json or [],
            explanation=c.explanation,
            examples=c.examples_json,
            chunks=c.chunks_json,
            frequency=c.frequency,
            frequency_note=c.frequency_note,
            is_learning=c.is_learning,
            anki_sync_status=c.anki_sync_status,
            anki_note_id=c.anki_note_id,
            anki_sync_error=c.anki_sync_error,
            llm_model=c.llm_model,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class CardListResponse(BaseModel):
    items: list[CardResponse]
    total: int
    offset: int
    limit: int


BatchImportItemStatus = Literal[
    "created",
    "duplicate_source",
    "duplicate_canonical",
    "rejected",
    "invalid_input",
    "upstream_error",
]

MobileLookupStatus = BatchImportItemStatus


class CardBatchImportRequest(BaseModel):
    source_texts: list[str] = Field(min_length=1, max_length=50)


class CardBatchImportItemResponse(BaseModel):
    source_text: str
    status: BatchImportItemStatus
    card_id: int | None = None
    canonical_text: str | None = None
    message: str | None = None


class CardBatchImportSummaryResponse(BaseModel):
    total: int
    created: int
    duplicate_source: int
    duplicate_canonical: int
    rejected: int
    invalid_input: int
    upstream_error: int


class CardBatchImportResponse(BaseModel):
    items: list[CardBatchImportItemResponse]
    summary: CardBatchImportSummaryResponse


class MobileLookupRequest(BaseModel):
    text: str
    send_to_telegram: bool = False


class MobileCardPreview(BaseModel):
    card_id: int
    canonical_text: str
    transcription: str | None
    translation_variants: list[str]
    word_family: list[WordFamilyItem]
    explanation: str
    examples: list[str]
    frequency: int
    frequency_note: str | None
    is_learning: bool

    @classmethod
    def from_card(cls, c: Card) -> "MobileCardPreview":
        return cls(
            card_id=c.id,
            canonical_text=c.canonical_text,
            transcription=c.transcription,
            translation_variants=c.translation_variants_json,
            word_family=c.word_family_json or [],
            explanation=c.explanation,
            examples=c.examples_json[:3],
            frequency=c.frequency,
            frequency_note=c.frequency_note,
            is_learning=c.is_learning,
        )


class MobileLookupResponse(BaseModel):
    status: MobileLookupStatus
    message: str
    preview: MobileCardPreview | None
    telegram_sent: bool


class AnkiPendingCardResponse(BaseModel):
    id: int
    canonical_text: str
    canonical_text_normalized: str
    transcription: str | None
    translation_variants: list[str]
    word_family: list[WordFamilyItem]
    explanation: str
    examples: list[str]
    chunks: list[CardChunk]

    @classmethod
    def from_card(cls, c: Card) -> "AnkiPendingCardResponse":
        return cls(
            id=c.id,
            canonical_text=c.canonical_text,
            canonical_text_normalized=c.canonical_text_normalized,
            transcription=c.transcription,
            translation_variants=c.translation_variants_json,
            word_family=c.word_family_json or [],
            explanation=c.explanation,
            examples=c.examples_json,
            chunks=c.chunks_json,
        )


class CardPatchRequest(BaseModel):
    is_learning: bool


PromptKind = Literal["chunk", "translation"]


class ReviewPromptResponse(BaseModel):
    kind: PromptKind
    index: int
    masked: str
    hint_translation: str
    expected_length: int
    hint_letter: str


class ReviewSessionItemResponse(BaseModel):
    card: CardResponse
    intro: bool
    prompt: ReviewPromptResponse
    srs_due_at: datetime | None


class ReviewSessionResponse(BaseModel):
    items: list[ReviewSessionItemResponse]


class ReviewCheckRequest(BaseModel):
    typed: str = Field(max_length=200)
    prompt_kind: PromptKind
    prompt_index: int = Field(ge=0)
    hint_used: bool


class ReviewCheckResponse(BaseModel):
    verdict: Literal["correct", "typo", "wrong"]
    expected: str
    auto_rating: int
    intervals: dict[int, int]


class ReviewGradeRequest(BaseModel):
    rating: int = Field(ge=1, le=4)
    auto_rating: int = Field(ge=1, le=4)
    overridden: bool
    typed: str = Field(max_length=200)
    prompt_kind: PromptKind
    prompt_index: int = Field(ge=0)
    verdict: Literal["correct", "typo", "wrong", "skipped"]
    hint_used: bool
    response_ms: int = Field(ge=0)
    expected_due_at: datetime | None


class ReviewGradeResponse(BaseModel):
    srs_due_at: datetime
    srs_state: str


class ReviewUndoResponse(BaseModel):
    card_id: int


class AppSettingsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timezone: str = Field(max_length=64)
    reminder_hour: int = Field(ge=0, le=23)
    reminder_anchor: str | None = Field(max_length=255)
    new_per_day: int = Field(ge=0, le=100)
    reviews_per_day: int = Field(ge=0, le=1000)
    desired_retention: float = Field(ge=0.7, le=0.97)
    learn_threshold: int = Field(ge=0, le=10)

    @field_validator("timezone")
    @classmethod
    def _timezone_exists(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
            raise ValueError(f"unknown timezone {value!r}") from exc
        return value


class AnkiAckRequest(BaseModel):
    card_id: int
    anki_note_id: int


class AnkiFailRequest(BaseModel):
    card_id: int
    error_message: str
