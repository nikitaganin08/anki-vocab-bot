from __future__ import annotations

from app.services.description_lookup_prompt import SYSTEM_PROMPT, build_description_lookup_messages


def test_system_prompt_requires_english_lexical_unit_without_infinitive_marker() -> None:
    assert (
        "source_text must be a single English word or stable English lexical unit."
        in SYSTEM_PROMPT
    )
    assert (
        'For verbs and phrasal verbs, return the lemma-like form without the infinitive '
        'marker "to ".'
    ) in SYSTEM_PROMPT


def test_build_description_lookup_messages_includes_description() -> None:
    messages = build_description_lookup_messages("to move snow away with a shovel")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "description: to move snow away with a shovel" in messages[1]["content"]
