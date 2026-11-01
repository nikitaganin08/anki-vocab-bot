from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

WHITESPACE_PATTERN = re.compile(r"\s+")


class SentenceFeedback(BaseModel):
    """The model's verdict on a learner's own sentence with a card's word."""

    ok: bool
    corrected: str | None = None
    comment: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("corrected", "comment")
    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return WHITESPACE_PATTERN.sub(" ", value.strip()) or None

    @field_validator("comment")
    @classmethod
    def comment_required(cls, value: str | None) -> str | None:
        if not value:
            raise ValueError("comment must not be empty")
        return value


def parse_sentence_feedback(payload: str | dict[str, Any]) -> SentenceFeedback:
    try:
        raw = json.loads(payload) if isinstance(payload, str) else payload
        return SentenceFeedback.model_validate(raw)
    except Exception as exc:
        raise ValueError("Sentence feedback does not match the contract") from exc
