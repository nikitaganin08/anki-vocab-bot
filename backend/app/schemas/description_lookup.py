from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

WHITESPACE_PATTERN = re.compile(r"\s+")
CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
MAX_CANDIDATE_TOKENS = 8
MIN_CANDIDATES = 3
MAX_CANDIDATES = 5


def _normalize_text(value: str, *, field_name: str) -> str:
    normalized = WHITESPACE_PATTERN.sub(" ", value.strip())
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


class FoundDescriptionLookupResponse(BaseModel):
    found: Literal[True]
    candidates: list[str] = Field(min_length=MIN_CANDIDATES, max_length=MAX_CANDIDATES)

    model_config = ConfigDict(extra="forbid")

    @field_validator("candidates")
    @classmethod
    def validate_candidates(cls, value: list[str]) -> list[str]:
        normalized_candidates: list[str] = []
        seen: set[str] = set()

        for item in value:
            normalized = _normalize_text(item, field_name="candidates")
            if CYRILLIC_PATTERN.search(normalized):
                raise ValueError("candidates must be English-only")
            if len(normalized.split(" ")) > MAX_CANDIDATE_TOKENS:
                raise ValueError("each candidate must contain at most 8 tokens")

            key = normalized.casefold()
            if key in seen:
                raise ValueError("candidates must be unique")
            seen.add(key)
            normalized_candidates.append(normalized)

        return normalized_candidates


class RejectedDescriptionLookupResponse(BaseModel):
    found: Literal[False]
    message_for_user: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("message_for_user")
    @classmethod
    def validate_message_for_user(cls, value: str) -> str:
        return _normalize_text(value, field_name="message_for_user")


DescriptionLookupResponse = (
    FoundDescriptionLookupResponse | RejectedDescriptionLookupResponse
)
DESCRIPTION_LOOKUP_ADAPTER = TypeAdapter(DescriptionLookupResponse)


def parse_description_lookup_response(
    payload: str | dict[str, Any],
) -> DescriptionLookupResponse:
    try:
        raw_payload = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as exc:
        raise ValueError("Description lookup payload is not valid JSON") from exc

    try:
        return DESCRIPTION_LOOKUP_ADAPTER.validate_python(raw_payload)
    except Exception as exc:
        raise ValueError("Description lookup payload does not match the contract") from exc
