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
