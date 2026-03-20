from __future__ import annotations

from app.services.description_lookup_prompt import SYSTEM_PROMPT, build_description_lookup_messages


def test_system_prompt_requires_english_lexical_unit_without_infinitive_marker() -> None:
    assert (
        "each candidate must be a single English word, collocation, or phrasal verb."
        in SYSTEM_PROMPT
    )
    assert (
        "Do not return a definition, explanation, or translation gloss "
        "instead of the lexical unit itself."
        in SYSTEM_PROMPT
    )
    assert "Prefer established lexical units over literal paraphrases." in SYSTEM_PROMPT
    assert (
        'For verbs and phrasal verbs, return the lemma-like form without the infinitive '
        'marker "to ".'
    ) in SYSTEM_PROMPT
    assert "candidates must contain 3 to 5 items." in SYSTEM_PROMPT


def test_build_description_lookup_messages_includes_description() -> None:
    messages = build_description_lookup_messages("to move snow away with a shovel")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "description: to move snow away with a shovel" in messages[1]["content"]
    assert "without returning explanations or translation glosses" in messages[1]["content"]
