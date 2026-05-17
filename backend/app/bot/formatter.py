from __future__ import annotations

from html import escape

from app.models.card import Card
from app.services.card_service import CardServiceResult


def format_card_payload(card: Card) -> str:
    translations = [_html(value) for value in card.translation_variants_json]
    primary_translation = translations[0] if translations else "—"
    synonyms = "; ".join(translations[1:]) if len(translations) > 1 else "—"
    numbered_labels = ("1️⃣", "2️⃣", "3️⃣")
    examples = "\n".join(
        f"{numbered_labels[idx]} {_html(example)}"
        for idx, example in enumerate(card.examples_json[:3])
    )
    transcription = _html(card.transcription) if card.transcription else "—"
    frequency_note = _html(card.frequency_note) if card.frequency_note else "—"

    return (
        f"🔍 Word: <b>{_html(card.canonical_text)}</b>\n"
        f"🗣 Transcription: {transcription}\n"
        f"🌍 Primary translation: <b>{primary_translation}</b>\n"
        f"🧩 Synonyms: <b>{synonyms}</b>\n\n"
        "📝 Explanation\n"
        f"{_html(card.explanation)}\n\n"
        "🪧 Examples\n"
        f"{examples}\n\n"
        f"📊 Frequency: {card.frequency}/10 — {frequency_note}"
    )


def _html(value: str) -> str:
    return escape(value, quote=False)


def format_created_message(card: Card) -> str:
    return "✅ Added to dictionary\n\n" + format_card_payload(card)


def format_duplicate_message(card: Card) -> str:
    return "ℹ️ Already in dictionary\n\n" + format_card_payload(card)


def format_card_service_result(result: CardServiceResult) -> tuple[str, str | None]:
    if result.status == "rejected" and result.rejection is not None:
        return result.rejection.message_for_user, None

    if result.card is None:
        return "Unexpected bot response state.", None

    if result.status == "created":
        return format_created_message(result.card), "HTML"

    if result.status in {"duplicate_source", "duplicate_canonical"}:
        return format_duplicate_message(result.card), "HTML"

    return "Unexpected bot response state.", None


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
