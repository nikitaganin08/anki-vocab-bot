from app.bot.input_validation import (
    EMPTY_DESCRIPTION_MESSAGE,
    EMPTY_INPUT_MESSAGE,
    TOO_LONG_DESCRIPTION_MESSAGE,
    TOO_LONG_INPUT_MESSAGE,
    validate_description_input,
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


def test_validate_description_input_accepts_longer_free_form_text() -> None:
    result = validate_description_input("  to move snow away with a shovel  ")

    assert result.ok is True
    assert result.normalized_text == "to move snow away with a shovel"
    assert result.error_message is None
    assert result.token_count == 7


def test_validate_description_input_rejects_empty_text() -> None:
    result = validate_description_input("   ")

    assert result.ok is False
    assert result.normalized_text is None
    assert result.error_message == EMPTY_DESCRIPTION_MESSAGE
    assert result.token_count == 0


def test_validate_description_input_rejects_overly_long_description() -> None:
    result = validate_description_input(
        "one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
        "twentyone twentytwo twentythree twentyfour twentyfive"
    )

    assert result.ok is False
    assert result.normalized_text is None
    assert result.error_message == TOO_LONG_DESCRIPTION_MESSAGE
    assert result.token_count == 25
