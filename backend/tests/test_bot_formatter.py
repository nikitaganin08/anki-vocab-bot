from __future__ import annotations

from app.bot.formatter import format_card_payload
from app.models.card import Card, EntryType, SourceLanguage


def _make_card(translations: list[str]) -> Card:
    return Card(
        source_text="take off",
        source_language=SourceLanguage.EN,
        entry_type=EntryType.PHRASAL_VERB,
        canonical_text="take off",
        canonical_text_normalized="take off",
        transcription="teik of",
        translation_variants_json=translations,
        explanation="To leave the ground or remove clothing.",
        examples_json=[
            "The plane will take off in ten minutes.",
            "Please take off your shoes.",
            "Sales started to take off in spring.",
        ],
        frequency=4,
        frequency_note="Common in everyday English.",
        eligible_for_anki=True,
        llm_model="test-model",
    )


def test_format_card_payload_renders_primary_translation_and_synonyms() -> None:
    card = _make_card(["взлетать", "снимать", "резко начинаться"])

    payload = format_card_payload(card)

    assert "🌍 Primary translation: <b>взлетать</b>" in payload
    assert "🧩 Synonyms: <b>снимать; резко начинаться</b>" in payload


def test_format_card_payload_handles_missing_synonyms_fallback() -> None:
    card = _make_card(["взлетать"])

    payload = format_card_payload(card)

    assert "🌍 Primary translation: <b>взлетать</b>" in payload
    assert "🧩 Synonyms: <b>—</b>" in payload
