from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WHITESPACE_PATTERN = re.compile(r"\s+")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    return WHITESPACE_PATTERN.sub(" ", value.strip()) or None


class SentenceIssue(BaseModel):
    """One fix: `wrong` -> `right` with a short reason; both null for a general note."""

    wrong: str | None = None
    right: str | None = None
    why: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("wrong", "right", "why")
    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        return _clean(value)

    @model_validator(mode="after")
    def check(self) -> SentenceIssue:
        if not self.why:
            raise ValueError("why must not be empty")
        if (self.wrong is None) != (self.right is None):
            raise ValueError("wrong and right go together")
        return self


class SentenceFeedback(BaseModel):
    """The model's verdict on a learner's own sentence with a card's word."""

    ok: bool
    corrected: str | None = None
    issues: list[SentenceIssue] = Field(default_factory=list, max_length=4)

    model_config = ConfigDict(extra="forbid")

    @field_validator("corrected")
    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        return _clean(value)

    @model_validator(mode="after")
    def fix_needs_issues(self) -> SentenceFeedback:
        if not self.ok and not self.issues:
            raise ValueError("a sentence that needs a fix must list its issues")
        return self


def parse_sentence_feedback(payload: str | dict[str, Any]) -> SentenceFeedback:
    try:
        raw = json.loads(payload) if isinstance(payload, str) else payload
        return SentenceFeedback.model_validate(raw)
    except Exception as exc:
        raise ValueError("Sentence feedback does not match the contract") from exc
