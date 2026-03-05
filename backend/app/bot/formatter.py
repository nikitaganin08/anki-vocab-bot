from __future__ import annotations

from app.models.card import Card


def format_card_payload(card: Card) -> str:
    translations = "; ".join(card.translation_variants_json)
    numbered_labels = ("1️⃣", "2️⃣", "3️⃣")
    examples = "\n".join(
        f"{numbered_labels[idx]} {example}" for idx, example in enumerate(card.examples_json[:3])
    )
    transcription = card.transcription or "—"
    frequency_note = card.frequency_note or "—"

    return (
        f"🔍 Word: <b>{card.canonical_text}</b>\n"
        f"🗣 Transcription: {transcription}\n"
        f"🌍 Translations: <b>{translations}</b>\n\n"
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


def format_rate_limit_message() -> str:
    return "Rate limit reached: max 5 requests per minute."
