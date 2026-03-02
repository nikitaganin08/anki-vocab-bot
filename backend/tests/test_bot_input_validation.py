from app.bot.input_validation import (
    EMPTY_INPUT_MESSAGE,
    TOO_LONG_INPUT_MESSAGE,
    validate_source_input,
)


def test_validate_source_input_accepts_and_normalizes_whitespace() -> None:
    result = validate_source_input("  take   off ")

    assert result.ok is True
    assert result.normalized_text == "take off"
    assert result.error_message is None
    assert result.token_count == 2


def test_validate_source_input_rejects_empty_text() -> None:
    result = validate_source_input("   ")

    assert result.ok is False
    assert result.normalized_text is None
    assert result.error_message == EMPTY_INPUT_MESSAGE
    assert result.token_count == 0


def test_validate_source_input_rejects_more_than_eight_tokens() -> None:
    result = validate_source_input("one two three four five six seven eight nine")

    assert result.ok is False
    assert result.normalized_text is None
    assert result.error_message == TOO_LONG_INPUT_MESSAGE
    assert result.token_count == 9
