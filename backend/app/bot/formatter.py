from __future__ import annotations

from app.models.card import Card


def format_card_payload(card: Card) -> str:
    translations = ", ".join(card.translation_variants_json)
    examples = "\n".join(f"{idx + 1}. {example}" for idx, example in enumerate(card.examples_json))
    transcription = card.transcription or "—"
    frequency_note = card.frequency_note or "—"

    return (
        f"Word: {card.canonical_text}\n"
        f"Transcription: {transcription}\n"
        f"Translations: {translations}\n"
        f"Explanation: {card.explanation}\n"
        f"Examples:\n{examples}\n"
        f"Frequency: {card.frequency}/10\n"
        f"Frequency note: {frequency_note}"
    )


def format_created_message(card: Card) -> str:
    return "Added to dictionary.\n\n" + format_card_payload(card)


def format_duplicate_message(card: Card) -> str:
    return "Already in dictionary.\n\n" + format_card_payload(card)


def format_rate_limit_message() -> str:
    return "Rate limit reached: max 5 requests per minute."
