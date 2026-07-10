from __future__ import annotations

from dataclasses import dataclass

from app.services.card_service import normalize_source_text

MAX_TOKENS = 8
MAX_DESCRIPTION_TOKENS = 24

EMPTY_INPUT_MESSAGE = "Please send a single word or a stable expression."
TOO_LONG_INPUT_MESSAGE = "Please send up to 8 words."
EMPTY_DESCRIPTION_MESSAGE = "Use /find followed by a short description."
TOO_LONG_DESCRIPTION_MESSAGE = "Please keep /find descriptions under 24 words."


@dataclass(slots=True)
class InputValidationResult:
    normalized_text: str | None
    error_message: str | None


def validate_source_input(raw_text: str) -> InputValidationResult:
    try:
        normalized = normalize_source_text(raw_text)
    except ValueError:
        return InputValidationResult(
            normalized_text=None,
            error_message=EMPTY_INPUT_MESSAGE,
        )

    if len(normalized.split()) > MAX_TOKENS:
        return InputValidationResult(
            normalized_text=None,
            error_message=TOO_LONG_INPUT_MESSAGE,
        )

    return InputValidationResult(
        normalized_text=normalized,
        error_message=None,
    )


def validate_description_input(raw_text: str) -> InputValidationResult:
    try:
        normalized = normalize_source_text(raw_text)
    except ValueError:
        return InputValidationResult(
            normalized_text=None,
            error_message=EMPTY_DESCRIPTION_MESSAGE,
        )

    if len(normalized.split()) > MAX_DESCRIPTION_TOKENS:
        return InputValidationResult(
            normalized_text=None,
            error_message=TOO_LONG_DESCRIPTION_MESSAGE,
        )

    return InputValidationResult(
        normalized_text=normalized,
        error_message=None,
    )
