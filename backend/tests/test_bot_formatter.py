from __future__ import annotations

from app.bot.formatter import format_card_payload, format_rare_word_prompt
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
        word_family_json=[
            {
                "word": "takeoff",
                "part_of_speech": "noun",
                "translation": "взлёт",
            }
        ],
        explanation="To leave the ground or remove clothing.",
        examples_json=[
            "The plane will take off in ten minutes.",
            "Please take off your shoes.",
            "Sales started to take off in spring.",
        ],
        frequency=4,
        frequency_note="Common in everyday English.",
        is_learning=True,
        llm_model="test-model",
    )


def test_format_card_payload_renders_primary_translation_and_synonyms() -> None:
    card = _make_card(["взлетать", "снимать", "резко начинаться"])

    payload = format_card_payload(card)

    assert "🌍 Primary translation: <b>взлетать</b>" in payload
    assert "🧩 Synonyms: <b>снимать; резко начинаться</b>" in payload
    assert "🧬 Word family" in payload
    assert "<b>takeoff</b> (noun) — взлёт" in payload


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
    card.examples_json = ["A < B & C > D.", "Not shown.", "Plain example."]
    card.frequency_note = "Common & useful."

    payload = format_card_payload(card)

    assert "Word: <b>look &lt;up&gt; &amp; go</b>" in payload
    assert "Transcription: /lʊk &amp; ɡoʊ/" in payload
    assert "Primary translation: <b>меньше &lt; больше</b>" in payload
    assert "Synonyms: <b>A &amp; B</b>" in payload
    assert "Use &lt; and &amp; literally." in payload
    assert "A &lt; B &amp; C &gt; D." in payload
    assert "Common &amp; useful." in payload


def test_format_card_payload_shows_chunks() -> None:
    card = _make_card(["бросить", "сдаться"])
    card.chunks_json = [
        {"text": "give up smoking", "target": "give up", "translation": "бросить курить"},
        {"text": "never give up", "target": "give up", "translation": "никогда не сдаваться"},
    ]

    payload = format_card_payload(card)

    assert "🧩 Usage" in payload
    assert "give up smoking — бросить курить" in payload
    assert "never give up — никогда не сдаваться" in payload
    assert payload.index("Usage") < payload.index("The plane will take off")
    assert "Please take off your shoes." not in payload


def test_format_rare_word_prompt() -> None:
    card = _make_card(["взлетать"])
    card.frequency = 2

    assert format_rare_word_prompt(card) == "Rare word (2/10). Learn it?"
