from __future__ import annotations

import html
import re
from datetime import datetime, timedelta

import fsrs
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import AnkiImportRequest
from app.bot.input_validation import validate_source_input
from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.models.card import AnkiSyncStatus, Card
from app.services.card_service import apply_source_text, normalize_canonical_text
from app.services.srs import as_utc

# ponytail: one-off import of the owner's Anki deck; delete with the script after the run.

HTML_TAG = re.compile(r"<[^>]+>")


def _plain_text(value: str) -> str:
    return " ".join(html.unescape(HTML_TAG.sub(" ", value)).split())


def fsrs_card_from_anki(item: AnkiImportRequest, card_id: int, now: datetime) -> fsrs.Card | None:
    if item.card_type == 0:
        return None
    now = as_utc(now)
    last_review = as_utc(item.last_review_at) if item.last_review_at else None
    stability = max(item.interval_days, 1)
    difficulty = min(max(5 + (2.5 - item.ease) * 4, 1), 10)
    if item.card_type == 1:
        # FSRS sets stability/difficulty on the first answer of a learning card.
        return fsrs.Card(
            card_id=card_id, state=fsrs.State.Learning, step=0, due=now, last_review=last_review
        )
    if item.card_type == 3:
        return fsrs.Card(
            card_id=card_id,
            state=fsrs.State.Relearning,
            step=0,
            stability=stability,
            difficulty=difficulty,
            due=now,
            last_review=last_review or now,
        )
    interval = timedelta(days=item.interval_days)
    last_review = last_review or now - interval
    return fsrs.Card(
        card_id=card_id,
        state=fsrs.State.Review,
        stability=stability,
        difficulty=difficulty,
        due=last_review + interval,
        last_review=last_review,
    )


def _find_or_create(
    session: Session, client: OpenRouterClient, item: AnkiImportRequest
) -> tuple[str, Card | None]:
    word = _plain_text(item.word)
    card = session.get(Card, item.backend_card_id) if item.backend_card_id is not None else None
    if card is None:
        card = session.scalar(
            select(Card).where(Card.canonical_text_normalized == normalize_canonical_text(word))
        )
    if card is not None:
        return "linked", card

    validation = validate_source_input(word)
    if validation.normalized_text is None:
        return "rejected", None
    try:
        result = apply_source_text(session, client, validation.normalized_text)
    except OpenRouterError:
        return "upstream_error", None
    if result.card is None:
        return "rejected", None
    if result.status != "created":
        return "linked", result.card

    translation = _plain_text(item.translation)
    variants = result.card.translation_variants_json
    if translation and translation not in variants:
        result.card.translation_variants_json = [translation, *variants][:3]
    return "created", result.card


def import_anki_note(
    session: Session, client: OpenRouterClient, item: AnkiImportRequest, now: datetime
) -> tuple[str, Card | None]:
    status, card = _find_or_create(session, client, item)
    if card is None:
        return status, None

    fsrs_card = fsrs_card_from_anki(item, card.id, now)
    card.srs_card_json = fsrs_card.to_json() if fsrs_card else None
    card.srs_due_at = fsrs_card.due if fsrs_card else None
    card.srs_state = fsrs_card.state.name.lower() if fsrs_card else None
    card.srs_reps = item.reps
    card.srs_lapses = item.lapses
    card.is_learning = not item.suspended
    # Already in Anki: sync_anki must not push it again.
    card.anki_note_id = item.anki_note_id
    card.anki_sync_status = AnkiSyncStatus.SYNCED
    card.anki_sync_error = None
    session.commit()
    return status, card
