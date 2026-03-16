from __future__ import annotations

from app.services.llm_prompt import SYSTEM_PROMPT, build_llm_messages


def test_system_prompt_requires_same_contract_for_ru_and_en() -> None:
    assert (
        'Use the same accepted contract for both source_language values ("ru" and "en").'
        in SYSTEM_PROMPT
    )
    assert (
        "source_language describes the language of input only "
        "and must not change the response shape."
        in SYSTEM_PROMPT
    )


def test_system_prompt_requires_primary_translation_and_synonyms_order() -> None:
    assert (
        "translation_variants[0] must be the primary Russian translation "
        "of canonical_text."
    ) in SYSTEM_PROMPT
    assert (
        "translation_variants[1..] must be Russian synonyms or near-synonymous variants"
        in SYSTEM_PROMPT
    )
    assert "of the primary translation." in SYSTEM_PROMPT
    assert (
        "Preserve translation_variants ordering: primary translation first, "
        "then synonyms/variants."
    ) in SYSTEM_PROMPT


def test_build_llm_messages_includes_source_text() -> None:
    messages = build_llm_messages("привет")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "source_text: привет" in messages[1]["content"]
