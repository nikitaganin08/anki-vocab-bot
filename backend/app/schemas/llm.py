from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from app.models.card import EntryType, SourceLanguage

CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
WHITESPACE_PATTERN = re.compile(r"\s+")
ENGLISH_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
CANONICAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


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


def _extract_english_tokens(value: str) -> set[str]:
    return {match.group(0).casefold() for match in ENGLISH_WORD_PATTERN.finditer(value)}


def _tokens_related(lhs: str, rhs: str) -> bool:
    if lhs == rhs:
        return True

    common_prefix_len = 0
    while (
        common_prefix_len < len(lhs)
        and common_prefix_len < len(rhs)
        and lhs[common_prefix_len] == rhs[common_prefix_len]
    ):
        common_prefix_len += 1

    return common_prefix_len >= 4


def _example_references_canonical(example: str, canonical_tokens: set[str]) -> bool:
    example_tokens = _extract_english_tokens(example)
    return any(
        _tokens_related(example_token, canonical_token)
        for example_token in example_tokens
        for canonical_token in canonical_tokens
    )


class WordFamilyItem(BaseModel):
    word: str
    part_of_speech: str
    translation: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("word", "part_of_speech")
    @classmethod
    def validate_english_text(cls, value: str) -> str:
        return _ensure_non_cyrillic(value, "word family item")

    @field_validator("translation")
    @classmethod
    def validate_translation(cls, value: str) -> str:
        return _ensure_contains_cyrillic(value)


class AcceptedLlmResponse(BaseModel):
    accepted: Literal[True]
    source_language: SourceLanguage
    entry_type: EntryType
    canonical_text: str
    transcription: str | None = None
    # Contract semantics: index 0 is the primary Russian translation,
    # remaining items are Russian synonyms/near-synonymous variants.
    translation_variants: list[str] = Field(min_length=2, max_length=3)
    word_family: list[WordFamilyItem] = Field(default_factory=list, max_length=5)
    explanation: str
    examples: list[str] = Field(min_length=3, max_length=3)
    frequency: int = Field(ge=0, le=10)
    frequency_note: str | None = None

    model_config = ConfigDict(extra="forbid")

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
        normalized_items = [_ensure_contains_cyrillic(item) for item in value]
        seen: set[str] = set()
        for item in normalized_items:
            key = item.casefold()
            if key in seen:
                raise ValueError("translation variants must be unique")
            seen.add(key)
        return normalized_items

    @field_validator("word_family")
    @classmethod
    def validate_word_family(cls, value: list[WordFamilyItem]) -> list[WordFamilyItem]:
        seen: set[str] = set()
        for item in value:
            key = item.word.casefold()
            if key in seen:
                raise ValueError("word family items must be unique")
            seen.add(key)
        return value

    @field_validator("transcription", "frequency_note")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_whitespace(value)
        return normalized or None

    @model_validator(mode="after")
    def validate_contract_semantics(self) -> "AcceptedLlmResponse":
        canonical_text_casefolded = self.canonical_text.casefold()
        if any(item.word.casefold() == canonical_text_casefolded for item in self.word_family):
            raise ValueError("word family must not repeat canonical_text")

        if self.entry_type in {
            EntryType.WORD,
            EntryType.PHRASAL_VERB,
        } and canonical_text_casefolded.startswith("to "):
            raise ValueError("canonical_text for words and phrasal verbs must not start with 'to '")

        raw_canonical_tokens = _extract_english_tokens(self.canonical_text)
        if len(raw_canonical_tokens) < 2:
            return self

        canonical_tokens = {
            token for token in raw_canonical_tokens if token not in CANONICAL_STOPWORDS
        }
        if not canonical_tokens:
            return self

        aligned_examples_count = sum(
            1
            for example in self.examples
            if _example_references_canonical(example, canonical_tokens)
        )
        if aligned_examples_count < 2:
            raise ValueError("at least two examples must reference canonical_text")

        return self


class RejectedLlmResponse(BaseModel):
    accepted: Literal[False]
    message_for_user: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("message_for_user")
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
