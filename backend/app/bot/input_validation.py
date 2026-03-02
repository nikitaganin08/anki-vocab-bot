from __future__ import annotations

from dataclasses import dataclass

from app.services.card_service import normalize_source_text, tokenize_source_text

MIN_TOKENS = 1
MAX_TOKENS = 8

EMPTY_INPUT_MESSAGE = "Please send a single word or a stable expression."
TOO_LONG_INPUT_MESSAGE = "Please send up to 8 words."


@dataclass(slots=True)
class InputValidationResult:
    ok: bool
    normalized_text: str | None
    error_message: str | None
    token_count: int


def validate_source_input(raw_text: str) -> InputValidationResult:
    try:
        normalized = normalize_source_text(raw_text)
    except ValueError:
        return InputValidationResult(
            ok=False,
            normalized_text=None,
            error_message=EMPTY_INPUT_MESSAGE,
            token_count=0,
        )

    token_count = len(tokenize_source_text(normalized))
    if token_count < MIN_TOKENS:
        return InputValidationResult(
            ok=False,
            normalized_text=None,
            error_message=EMPTY_INPUT_MESSAGE,
            token_count=token_count,
        )
    if token_count > MAX_TOKENS:
        return InputValidationResult(
            ok=False,
            normalized_text=None,
            error_message=TOO_LONG_INPUT_MESSAGE,
            token_count=token_count,
        )

    return InputValidationResult(
        ok=True,
        normalized_text=normalized,
        error_message=None,
        token_count=token_count,
    )
