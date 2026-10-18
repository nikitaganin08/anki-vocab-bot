from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.schemas.llm import valid_chunks

CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
RU_TO_EN_LAYOUT = str.maketrans(
    "йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ",
    "qwertyuiop[]asdfghjkl;'zxcvbnm,.`QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>~",
)


def normalize_answer(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("’", "'").replace("‘", "'")
    return " ".join(text.split()).rstrip(".,!?;: ")


def ru_layout_to_en(text: str) -> str:
    return text.translate(RU_TO_EN_LAYOUT)


@dataclass(slots=True)
class AnswerCheck:
    verdict: Literal["correct", "typo", "form", "wrong"]
    expected: str


def _strip_prefix(text: str, prefixes: tuple[str, ...]) -> str:
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text


def _dl_distance(a: str, b: str) -> int:
    # Optimal string alignment: insert, delete, substitute, adjacent transposition.
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + (a[i - 1] != b[j - 1]),
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def check_answer(
    typed: str,
    expected: str,
    *,
    optional_prefixes: tuple[str, ...] = (),
    base_form: str | None = None,
) -> AnswerCheck:
    if CYRILLIC_PATTERN.search(typed):
        typed = ru_layout_to_en(typed)
    answer = _strip_prefix(normalize_answer(typed), optional_prefixes)
    target = _strip_prefix(normalize_answer(expected), optional_prefixes)
    if not answer:
        return AnswerCheck("wrong", expected)
    if answer == target:
        return AnswerCheck("correct", expected)
    # The right word in its dictionary form where the sentence needs an inflected one.
    if base_form and answer == _strip_prefix(normalize_answer(base_form), optional_prefixes):
        return AnswerCheck("form", expected)
    if len(target) >= 5 and _dl_distance(answer, target) == 1:
        return AnswerCheck("typo", expected)
    return AnswerCheck("wrong", expected)


def auto_rating(verdict: str, hint_used: bool) -> int:
    if verdict == "wrong":
        return 1
    return 2 if hint_used or verdict == "form" else 3


@dataclass(slots=True)
class Prompt:
    kind: Literal["chunk", "translation"]
    index: int
    masked: str
    hint_translation: str
    expected: str


def build_prompt(
    chunks: list[dict[str, str]],
    translations: list[str],
    canonical_text: str,
    review_count: int,
) -> Prompt:
    # Stored chunks may predate validation. A target wider than the word itself
    # ("general ledger" for "ledger") still shows on the back but is not asked.
    max_words = len(canonical_text.split())
    valid = [c for c in valid_chunks(chunks) if len(c.target.split()) <= max_words]
    if valid:
        index = review_count % len(valid)
        chunk = valid[index]
        match = re.search(re.escape(chunk.target), chunk.text, re.IGNORECASE)
        if match:
            text = chunk.text
            masked = f"{text[: match.start()]}___{text[match.end() :]}"
            return Prompt("chunk", index, masked, chunk.translation, match.group(0))
    return Prompt("translation", 0, ", ".join(translations), "", canonical_text)
