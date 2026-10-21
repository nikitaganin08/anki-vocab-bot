from __future__ import annotations

from app.services.llm_prompt import SYSTEM_PROMPT, build_llm_messages


def test_system_prompt_excludes_backend_derived_fields() -> None:
    assert "canonical_text_normalized" not in SYSTEM_PROMPT
    assert '"source_text":' not in SYSTEM_PROMPT
    assert '"llm_model":' not in SYSTEM_PROMPT
    assert '"reason":' not in SYSTEM_PROMPT


def test_system_prompt_requires_same_contract_for_ru_and_en() -> None:
    assert (
        'Use the same accepted contract for both source_language values ("ru" and "en").'
        in SYSTEM_PROMPT
    )
    assert (
        "source_language describes the language of input only "
        "and must not change the response shape." in SYSTEM_PROMPT
    )


def test_system_prompt_requires_english_rejection_message() -> None:
    assert "message_for_user must be written in English." in SYSTEM_PROMPT


def test_system_prompt_requires_primary_translation_and_synonyms_order() -> None:
    assert (
        "translation_variants[0] must be the primary Russian translation of canonical_text."
    ) in SYSTEM_PROMPT
    assert (
        "translation_variants[1..] must be Russian synonyms or near-synonymous variants"
        in SYSTEM_PROMPT
    )
    assert "of the primary translation." in SYSTEM_PROMPT
    assert (
        "Preserve translation_variants ordering: primary translation first, then synonyms/variants."
    ) in SYSTEM_PROMPT


def test_system_prompt_requires_word_family_items_and_examples() -> None:
    assert '"word_family": [' in SYSTEM_PROMPT
    assert (
        'For entry_type "word", word_family may contain 0 to 3 established English derivational'
        in SYSTEM_PROMPT
    )
    assert (
        'For entry_type "phrasal_verb", "collocation", "idiom", or "expression", word_family'
        in SYSTEM_PROMPT
    )
    assert "do not derive forms from individual words in a multi-word unit." in SYSTEM_PROMPT
    assert "forms naturally in" in SYSTEM_PROMPT


def test_build_llm_messages_includes_source_text() -> None:
    messages = build_llm_messages("привет")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "source_text: привет" in messages[1]["content"]


def test_prompt_requests_chunks_and_rejects_function_words() -> None:
    assert '"chunks"' in SYSTEM_PROMPT
    assert '"target"' in SYSTEM_PROMPT
    assert "function words" in SYSTEM_PROMPT


def test_prompt_requires_general_american_ipa_in_slashes() -> None:
    assert "General American" in SYSTEM_PROMPT
    assert "never use square brackets" in SYSTEM_PROMPT
    assert "always wrapped in slashes" in SYSTEM_PROMPT
    assert "ɒ, əʊ, ɪə, eə, ʊə" in SYSTEM_PROMPT
    assert "Never provide transcription for the Russian source term" in SYSTEM_PROMPT


def test_system_prompt_anchors_the_frequency_scale() -> None:
    assert "10 = top 1000" in SYSTEM_PROMPT
    assert "5 = top 20000" in SYSTEM_PROMPT
    assert "0 = practically never used" in SYSTEM_PROMPT
