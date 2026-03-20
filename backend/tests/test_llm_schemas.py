from __future__ import annotations

import pytest

from app.schemas.llm import AcceptedLlmResponse, parse_llm_response


def test_parse_llm_response_accepts_valid_payload() -> None:
    result = parse_llm_response(
        {
            "accepted": True,
            "source_text": "take off",
            "source_language": "en",
            "entry_type": "phrasal_verb",
            "canonical_text": "take off",
            "canonical_text_normalized": "take off",
            "transcription": "teik of",
            "translation_variants": ["взлетать", "снимать"],
            "explanation": "To leave the ground.",
            "examples": [
                "The plane will take off soon.",
                "Please take off your jacket.",
                "Sales began to take off in spring.",
            ],
            "frequency": 5,
            "frequency_note": "Common in spoken English.",
            "llm_model": "test-model",
        }
    )

    assert isinstance(result, AcceptedLlmResponse)
    assert result.entry_type.value == "phrasal_verb"


def test_parse_llm_response_accepts_russian_source_with_same_contract() -> None:
    result = parse_llm_response(
        {
            "accepted": True,
            "source_text": "взлетать",
            "source_language": "ru",
            "entry_type": "word",
            "canonical_text": "take off",
            "canonical_text_normalized": "take off",
            "transcription": "teik of",
            "translation_variants": ["взлетать", "подниматься", "стартовать"],
            "explanation": "To leave the ground.",
            "examples": [
                "The plane will take off soon.",
                "The helicopter can take off vertically.",
                "The rocket will take off at dawn.",
            ],
            "frequency": 5,
            "frequency_note": "Common in aviation contexts.",
            "llm_model": "test-model",
        }
    )

    assert isinstance(result, AcceptedLlmResponse)
    assert result.source_language.value == "ru"
    assert result.translation_variants[0] == "взлетать"


def test_parse_llm_response_rejects_invalid_translation_count() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_text": "take off",
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "take off",
                "canonical_text_normalized": "take off",
                "transcription": "teik of",
                "translation_variants": ["взлетать"],
                "explanation": "To leave the ground.",
                "examples": [
                    "The plane will take off soon.",
                    "Please take off your jacket.",
                    "Sales began to take off in spring.",
                ],
                "frequency": 5,
                "frequency_note": "Common in spoken English.",
                "llm_model": "test-model",
            }
        )


def test_parse_llm_response_rejects_duplicate_translation_variants() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_text": "take off",
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "take off",
                "canonical_text_normalized": "take off",
                "transcription": "teik of",
                "translation_variants": ["взлетать", "  ВЗЛЕТАТЬ  "],
                "explanation": "To leave the ground.",
                "examples": [
                    "The plane will take off soon.",
                    "Please take off your jacket.",
                    "Sales began to take off in spring.",
                ],
                "frequency": 5,
                "frequency_note": "Common in spoken English.",
                "llm_model": "test-model",
            }
        )


def test_parse_llm_response_rejects_infinitive_marker_in_phrasal_verb_canonical() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_text": "разгребать",
                "source_language": "ru",
                "entry_type": "phrasal_verb",
                "canonical_text": "to shovel away",
                "canonical_text_normalized": "to shovel away",
                "transcription": "/ˈʃʌv.əl əˈweɪ/",
                "translation_variants": ["разгребать", "расчищать", "разбирать"],
                "explanation": "To move material away with a shovel or by hand.",
                "examples": [
                    "He shoveled away the snow before sunrise.",
                    "She shoveled away leaves after the storm.",
                    "They were shoveling away sand from the gate.",
                ],
                "frequency": 5,
                "frequency_note": "Common in literal contexts.",
                "llm_model": "test-model",
            }
        )


def test_parse_llm_response_rejects_examples_not_aligned_with_canonical_text() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_text": "разгребать",
                "source_language": "ru",
                "entry_type": "phrasal_verb",
                "canonical_text": "shovel away",
                "canonical_text_normalized": "shovel away",
                "transcription": "/ˈʃʌv.əl əˈweɪ/",
                "translation_variants": ["разгребать", "расчищать", "разбирать"],
                "explanation": "To move material away with a shovel or by hand.",
                "examples": [
                    "He had to shovel away the snow blocking the path.",
                    "I have mountains of paperwork to deal with this week.",
                    "We need to resolve the backlog by Friday.",
                ],
                "frequency": 6,
                "frequency_note": "Used in literal and figurative contexts.",
                "llm_model": "test-model",
            }
        )


def test_parse_llm_response_accepts_single_word_with_irregular_inflections_in_examples() -> None:
    result = parse_llm_response(
        {
            "accepted": True,
            "source_text": "идти",
            "source_language": "ru",
            "entry_type": "word",
            "canonical_text": "go",
            "canonical_text_normalized": "go",
            "transcription": "/ɡəʊ/",
            "translation_variants": ["идти", "отправляться"],
            "explanation": "To move from one place to another.",
            "examples": [
                "He went home early.",
                "They go to work by bus.",
                "She had gone before noon.",
            ],
            "frequency": 9,
            "frequency_note": "Very common.",
            "llm_model": "test-model",
        }
    )

    assert isinstance(result, AcceptedLlmResponse)
    assert result.canonical_text == "go"


def test_parse_llm_response_rejects_cyrillic_in_english_fields() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_text": "take off",
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "взлетать",
                "canonical_text_normalized": "взлетать",
                "transcription": "teik of",
                "translation_variants": ["взлетать", "снимать"],
                "explanation": "To leave the ground.",
                "examples": [
                    "The plane will take off soon.",
                    "Please take off your jacket.",
                    "Sales began to take off in spring.",
                ],
                "frequency": 5,
                "frequency_note": "Common in spoken English.",
                "llm_model": "test-model",
            }
        )


def test_parse_llm_response_rejects_malformed_json() -> None:
    with pytest.raises(ValueError):
        parse_llm_response("{not valid json")
