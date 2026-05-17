from __future__ import annotations

import app.models.anki_sync_attempt as anki_sync_attempt_model  # noqa: F401
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


def test_format_card_payload_escapes_html_sensitive_fields() -> None:
    card = _make_card(["меньше < больше", "A & B"])
    card.canonical_text = "look <up> & go"
    card.transcription = "/lʊk & ɡoʊ/"
    card.explanation = "Use < and & literally."
    card.examples_json = ["A < B & C.", "Keep > away.", "Plain example."]
    card.frequency_note = "Common & useful."

    payload = format_card_payload(card)

    assert "Word: <b>look &lt;up&gt; &amp; go</b>" in payload
    assert "Transcription: /lʊk &amp; ɡoʊ/" in payload
    assert "Primary translation: <b>меньше &lt; больше</b>" in payload
    assert "Synonyms: <b>A &amp; B</b>" in payload
    assert "Use &lt; and &amp; literally." in payload
    assert "A &lt; B &amp; C." in payload
    assert "Keep &gt; away." in payload
    assert "Common &amp; useful." in payload
