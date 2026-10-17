from __future__ import annotations

import pytest

from app.schemas.llm import AcceptedLlmResponse, parse_llm_response


def test_parse_llm_response_accepts_valid_payload() -> None:
    result = parse_llm_response(
        {
            "accepted": True,
            "source_language": "en",
            "entry_type": "phrasal_verb",
            "canonical_text": "take off",
            "transcription": "teik of",
            "translation_variants": ["взлетать", "снимать"],
            "word_family": [
                {
                    "word": "takeoff",
                    "part_of_speech": "noun",
                    "translation": "взлёт",
                }
            ],
            "explanation": "To leave the ground.",
            "examples": [
                "The plane will take off soon.",
                "Please take off your jacket.",
                "Sales began to take off in spring.",
            ],
            "frequency": 5,
            "frequency_note": "Common in spoken English.",
        }
    )

    assert isinstance(result, AcceptedLlmResponse)
    assert result.entry_type.value == "phrasal_verb"
    assert result.word_family[0].word == "takeoff"


def test_parse_llm_response_rejects_duplicate_word_family_items() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_language": "en",
                "entry_type": "word",
                "canonical_text": "accommodate",
                "transcription": "/əˈkɑːmədeɪt/",
                "translation_variants": ["размещать", "приспосабливать"],
                "word_family": [
                    {
                        "word": "accommodation",
                        "part_of_speech": "noun",
                        "translation": "размещение",
                    },
                    {
                        "word": "ACCOMMODATION",
                        "part_of_speech": "noun",
                        "translation": "жильё",
                    },
                ],
                "explanation": "To provide space or adjust to a situation.",
                "examples": [
                    "The hotel can accommodate more guests.",
                    "The accommodation was close to the station.",
                    "The flexible schedule accommodated everyone.",
                ],
                "frequency": 7,
                "frequency_note": "Common.",
            }
        )


def test_parse_llm_response_accepts_russian_source_with_same_contract() -> None:
    result = parse_llm_response(
        {
            "accepted": True,
            "source_language": "ru",
            "entry_type": "word",
            "canonical_text": "take off",
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
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "take off",
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
            }
        )


def test_parse_llm_response_rejects_duplicate_translation_variants() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "take off",
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
            }
        )


def test_parse_llm_response_rejects_infinitive_marker_in_phrasal_verb_canonical() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_language": "ru",
                "entry_type": "phrasal_verb",
                "canonical_text": "to shovel away",
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
            }
        )


def test_parse_llm_response_rejects_examples_not_aligned_with_canonical_text() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_language": "ru",
                "entry_type": "phrasal_verb",
                "canonical_text": "shovel away",
                "transcription": "/ˈʃʌv.əl əˈweɪ/",
                "translation_variants": ["разгребать", "расчищать", "разбирать"],
                "explanation": "To move material away with a shovel or by hand.",
                "examples": [
                    "I have mountains of paperwork to deal with this week.",
                    "He had to shovel away the snow blocking the path.",
                    "We need to resolve the backlog by Friday.",
                ],
                "frequency": 6,
                "frequency_note": "Used in literal and figurative contexts.",
            }
        )


def test_parse_llm_response_accepts_single_word_with_irregular_inflections_in_examples() -> None:
    result = parse_llm_response(
        {
            "accepted": True,
            "source_language": "ru",
            "entry_type": "word",
            "canonical_text": "go",
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
        }
    )

    assert isinstance(result, AcceptedLlmResponse)
    assert result.canonical_text == "go"


def test_parse_llm_response_rejects_cyrillic_in_english_fields() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            {
                "accepted": True,
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "взлетать",
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
            }
        )


def test_parse_llm_response_rejects_malformed_json() -> None:
    with pytest.raises(ValueError):
        parse_llm_response("{not valid json")


def _give_up_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "accepted": True,
        "source_language": "en",
        "entry_type": "phrasal_verb",
        "canonical_text": "give up",
        "transcription": "/ɡɪv ʌp/",
        "translation_variants": ["бросить", "сдаться"],
        "explanation": "To stop trying or stop doing something.",
        "examples": ["She finally gave up smoking last year."],
        "chunks": [
            {"text": "gave up on him", "target": "gave up", "translation": "разуверился в нём"}
        ],
        "frequency": 8,
        "frequency_note": "Very common.",
    }
    payload.update(overrides)
    return payload


def test_accepts_chunks_with_inflected_target() -> None:
    result = parse_llm_response(_give_up_payload())

    assert isinstance(result, AcceptedLlmResponse)
    assert result.chunks[0].text == "gave up on him"
    assert result.chunks[0].target == "gave up"
    assert result.chunks[0].translation == "разуверился в нём"


def test_rejects_chunk_target_not_in_text() -> None:
    with pytest.raises(ValueError):
        parse_llm_response(
            _give_up_payload(
                chunks=[{"text": "quit smoking", "target": "give up", "translation": "бросить"}]
            )
        )


def test_accepts_single_example_and_empty_chunks() -> None:
    result = parse_llm_response(_give_up_payload(chunks=[]))

    assert isinstance(result, AcceptedLlmResponse)
    assert result.examples == ["She finally gave up smoking last year."]
    assert result.chunks == []
