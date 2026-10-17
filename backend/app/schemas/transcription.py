from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError, field_validator

from app.schemas.llm import CYRILLIC_PATTERN

FORBIDDEN_PATTERN = re.compile(r"[\[\](){}\d]")
# Syllable dots or a second pair of slashes mean the model ignored the one-pair format.
INNER_FORBIDDEN_PATTERN = re.compile(r"[/.·\n]")
# Stress, length and spaces alone are not a pronunciation.
STRESS_AND_SPACE = re.compile(r"[ˈˌːˑ\s]")
# British-only vowels: the cards must be General American. The centring diphthongs ɪə and ʊə are
# British after a consonant (near /nɪə/, tour /tʊə/) but legitimate inside the American
# aɪər / eɪər / ɔɪər / aʊər sequences (wire, layer, employer, hour).
BRITISH_VOWELS = re.compile(r"ɒ|əʊ|eə|(?<![aeɔ])ɪə|(?<!a)ʊə")


class TranscriptionItem(BaseModel):
    id: int
    transcription: str

    @field_validator("transcription")
    @classmethod
    def validate_transcription(cls, value: str) -> str:
        value = value.strip()
        if not 3 <= len(value) <= 120 or not (value.startswith("/") and value.endswith("/")):
            raise ValueError("transcription must be 3..120 chars wrapped in slashes")
        if CYRILLIC_PATTERN.search(value) or FORBIDDEN_PATTERN.search(value):
            raise ValueError("transcription must not contain Cyrillic, brackets or digits")
        inner = value[1:-1]
        if INNER_FORBIDDEN_PATTERN.search(inner) or not STRESS_AND_SPACE.sub("", inner):
            raise ValueError("transcription must be one pair of slashes around plain IPA")
        if BRITISH_VOWELS.search(inner):
            raise ValueError("transcription must be General American, not British")
        return " ".join(value.split())


def parse_transcriptions_response(
    payload: str | dict[str, Any], allowed_ids: set[int] | None = None
) -> dict[int, str]:
    """Return {id: transcription}; invalid or unrequested items are dropped, not fatal."""
    try:
        raw_payload = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as exc:
        raise ValueError("LLM payload is not valid JSON") from exc

    items = raw_payload.get("items") if isinstance(raw_payload, dict) else None
    if not isinstance(items, list):
        raise ValueError("LLM payload does not match the transcriptions contract")

    result: dict[int, str] = {}
    for raw_item in items:
        try:
            item = TranscriptionItem.model_validate(raw_item)
        except ValidationError:
            continue
        if allowed_ids is None or item.id in allowed_ids:
            result.setdefault(item.id, item.transcription)
    return result
