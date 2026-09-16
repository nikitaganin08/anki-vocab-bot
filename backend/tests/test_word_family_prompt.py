from app.services.word_family_prompt import SYSTEM_PROMPT, build_word_family_messages


def test_word_family_prompt_contains_card_context_and_contract() -> None:
    messages = build_word_family_messages(
        "accommodate",
        explanation="To provide space or adjust to a situation.",
        translation_variants=["размещать", "приспосабливать"],
    )

    assert '"word_family": [' in SYSTEM_PROMPT
    assert len(messages) == 2
    assert "canonical_text: accommodate" in messages[1]["content"]
    assert "translation_variants: размещать, приспосабливать" in messages[1]["content"]
