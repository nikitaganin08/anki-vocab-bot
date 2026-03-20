from __future__ import annotations

from app.models.card import Card


def format_card_payload(card: Card) -> str:
    translations = card.translation_variants_json
    primary_translation = translations[0] if translations else "—"
    synonyms = "; ".join(translations[1:]) if len(translations) > 1 else "—"
    numbered_labels = ("1️⃣", "2️⃣", "3️⃣")
    examples = "\n".join(
        f"{numbered_labels[idx]} {example}" for idx, example in enumerate(card.examples_json[:3])
    )
    transcription = card.transcription or "—"
    frequency_note = card.frequency_note or "—"

    return (
        f"🔍 Word: <b>{card.canonical_text}</b>\n"
        f"🗣 Transcription: {transcription}\n"
        f"🌍 Primary translation: <b>{primary_translation}</b>\n"
        f"🧩 Synonyms: <b>{synonyms}</b>\n\n"
        "📝 Explanation\n"
        f"{card.explanation}\n\n"
        "🪧 Examples\n"
        f"{examples}\n\n"
        f"📊 Frequency: {card.frequency}/10 — {frequency_note}"
    )


def format_created_message(card: Card) -> str:
    return "✅ Added to dictionary\n\n" + format_card_payload(card)


def format_duplicate_message(card: Card) -> str:
    return "ℹ️ Already in dictionary\n\n" + format_card_payload(card)


def format_description_lookup_candidates(candidates: list[str]) -> str:
    numbered_candidates = "\n".join(
        f"{idx}. {candidate}" for idx, candidate in enumerate(candidates, start=1)
    )
    return (
        "Possible matches:\n"
        f"{numbered_candidates}\n\n"
        "Send one of these back if you want to add a card."
    )


def format_rate_limit_message() -> str:
    return "Rate limit reached: max 5 requests per minute."
