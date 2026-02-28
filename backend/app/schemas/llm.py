from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from app.models.card import EntryType, SourceLanguage

CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
WHITESPACE_PATTERN = re.compile(r"\s+")


def _normalize_whitespace(value: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", value.strip())


def _ensure_non_cyrillic(value: str, field_name: str) -> str:
    normalized = _normalize_whitespace(value)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if CYRILLIC_PATTERN.search(normalized):
        raise ValueError(f"{field_name} must be English-only")
    return normalized


def _ensure_contains_cyrillic(value: str) -> str:
    normalized = _normalize_whitespace(value)
    if not normalized:
        raise ValueError("translation variants must not be empty")
    if not CYRILLIC_PATTERN.search(normalized):
        raise ValueError("translation variants must contain Russian text")
    return normalized


class AcceptedLlmResponse(BaseModel):
    accepted: Literal[True]
    source_text: str
    source_language: SourceLanguage
    entry_type: EntryType
    canonical_text: str
    canonical_text_normalized: str
    transcription: str | None = None
    translation_variants: list[str] = Field(min_length=2, max_length=3)
    explanation: str
    examples: list[str] = Field(min_length=3, max_length=3)
    frequency: int = Field(ge=0, le=10)
    frequency_note: str | None = None
    llm_model: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("source_text", "canonical_text_normalized", "llm_model")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized = _normalize_whitespace(value)
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("canonical_text")
    @classmethod
    def validate_canonical_text(cls, value: str) -> str:
        return _ensure_non_cyrillic(value, "canonical_text")

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        return _ensure_non_cyrillic(value, "explanation")

    @field_validator("examples")
    @classmethod
    def validate_examples(cls, value: list[str]) -> list[str]:
        return [_ensure_non_cyrillic(item, "examples") for item in value]

    @field_validator("translation_variants")
    @classmethod
    def validate_translation_variants(cls, value: list[str]) -> list[str]:
        return [_ensure_contains_cyrillic(item) for item in value]

    @field_validator("transcription", "frequency_note")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_whitespace(value)
        return normalized or None


class RejectedLlmResponse(BaseModel):
    accepted: Literal[False]
    reason: str
    message_for_user: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("reason", "message_for_user")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized = _normalize_whitespace(value)
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


LlmResponse = AcceptedLlmResponse | RejectedLlmResponse
LLM_RESPONSE_ADAPTER = TypeAdapter(LlmResponse)


def parse_llm_response(payload: str | dict[str, Any]) -> LlmResponse:
    try:
        raw_payload = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as exc:
        raise ValueError("LLM payload is not valid JSON") from exc

    try:
        return LLM_RESPONSE_ADAPTER.validate_python(raw_payload)
    except Exception as exc:  # pydantic validation errors are normalized for callers
        raise ValueError("LLM payload does not match the contract") from exc
