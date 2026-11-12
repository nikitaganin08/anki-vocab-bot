from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.sentence_check import SentenceIssue, _clean

IssueCategory = Literal[
    "article",
    "tense",
    "verb_pattern",
    "preposition",
    "collocation",
    "word_choice",
    "word_order",
    "agreement",
    "grammar_other",
]
ISSUE_CATEGORIES: tuple[str, ...] = get_args(IssueCategory)
MAX_FIXES = 20  # a sanity cap; all real mistakes are stored, the chat shows the top ones


class SpeakingTopic(BaseModel):
    """Today's speaking topic, written by the text model."""

    topic: str = Field(min_length=3, max_length=120)
    questions: list[str] = Field(min_length=2, max_length=3)

    model_config = ConfigDict(extra="forbid")

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        return _clean(value) or ""

    @field_validator("questions")
    @classmethod
    def normalize_questions(cls, value: list[str]) -> list[str]:
        cleaned = [_clean(item) for item in value]
        if not all(cleaned):
            raise ValueError("questions must not be empty")
        return [item for item in cleaned if item]


class SpeakingFix(SentenceIssue):
    category: IssueCategory


class WordUse(BaseModel):
    word: str
    used: bool

    model_config = ConfigDict(extra="forbid")


class SpeakingFeedback(BaseModel):
    ok: Literal[True]
    transcript: str = Field(min_length=1)
    words_used: list[WordUse] = Field(default_factory=list)
    fixes: list[SpeakingFix] = Field(default_factory=list, max_length=MAX_FIXES)
    natural_version: str | None = None
    next_time: str = Field(min_length=1, max_length=300)
    focus_check: Literal["better", "same", "worse"] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("transcript", "natural_version", "next_time")
    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        return _clean(value)


class SpeakingRejected(BaseModel):
    """No English speech in the recording (silence, another language)."""

    ok: Literal[False]
    message_for_user: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


SpeakingResult = SpeakingFeedback | SpeakingRejected


def _load(payload: str | dict[str, Any]) -> Any:
    return json.loads(payload) if isinstance(payload, str) else payload


def parse_speaking_topic(
    payload: str | dict[str, Any], target_words: Sequence[str] = ()
) -> SpeakingTopic:
    """The task must not give the target words away: any of their longer tokens (or a form
    starting with one) in the topic or questions is invalid, so the client asks again."""
    try:
        topic = SpeakingTopic.model_validate(_load(payload))
    except Exception as exc:
        raise ValueError("Speaking topic does not match the contract") from exc
    text = " ".join([topic.topic, *topic.questions]).casefold()
    for word in target_words:
        for token in re.findall(r"[a-z']+", word.casefold()):
            if len(token) >= 4 and re.search(rf"\b{re.escape(token)}", text):
                raise ValueError(f"Speaking topic gives away the target word {word!r}")
    return topic


def parse_speaking_result(payload: str | dict[str, Any]) -> SpeakingResult:
    try:
        raw = _load(payload)
        if isinstance(raw, dict) and raw.get("ok") is False:
            return SpeakingRejected.model_validate(raw)
        return SpeakingFeedback.model_validate(raw)
    except Exception as exc:
        raise ValueError("Speaking feedback does not match the contract") from exc
