from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.clients.anki_connect import AnkiConnectError, AnkiNotePayload
from app.clients.backend_sync_api import BackendSyncApiError, PendingCard

ANKI_DECK_NAME = "English::Inbox"
ANKI_NOTE_TYPE = "VocabularyCard"
CARD_TAG_PREFIX = "avb-card"


@dataclass(slots=True)
class SyncSummary:
    total: int = 0
    synced: int = 0
    failed: int = 0


class BackendSyncGateway(Protocol):
    def get_pending(self, limit: int = 50) -> list[PendingCard]: ...

    def ack(self, card_id: int, anki_note_id: int) -> None: ...

    def fail(self, card_id: int, error_message: str) -> None: ...


class AnkiGateway(Protocol):
    def find_notes_by_tag(self, tag: str) -> list[int]: ...

    def add_note(self, payload: AnkiNotePayload) -> int: ...


def build_card_tag(card_id: int) -> str:
    return f"{CARD_TAG_PREFIX}-{card_id}"


def map_card_to_anki_payload(card: PendingCard) -> AnkiNotePayload:
    translation = ", ".join(card.translation_variants)
    example = "\n".join(card.examples[:2])
    fields = {
        "Word": card.canonical_text,
        "Transcription": card.transcription or "",
        "Translation": translation,
        "Explanation": card.explanation,
        "Example": example,
    }
    return AnkiNotePayload(
        deck_name=ANKI_DECK_NAME,
        model_name=ANKI_NOTE_TYPE,
        fields=fields,
        tags=[build_card_tag(card.id)],
    )


def sync_pending_cards(
    *,
    backend_client: BackendSyncGateway,
    anki_client: AnkiGateway,
    limit: int = 50,
) -> SyncSummary:
    pending_cards = backend_client.get_pending(limit=limit)
    summary = SyncSummary(total=len(pending_cards))

    for card in pending_cards:
        existing_note_ids = anki_client.find_notes_by_tag(build_card_tag(card.id))
        if existing_note_ids:
            backend_client.ack(card.id, existing_note_ids[0])
            summary.synced += 1
            continue

        try:
            payload = map_card_to_anki_payload(card)
            anki_note_id = anki_client.add_note(payload)
        except AnkiConnectError as exc:
            _report_failure(backend_client, card.id, exc.user_message)
            summary.failed += 1
            continue

        backend_client.ack(card.id, anki_note_id)
        summary.synced += 1

    return summary


def _report_failure(backend_client: BackendSyncGateway, card_id: int, message: str) -> None:
    try:
        backend_client.fail(card_id, message)
    except BackendSyncApiError as exc:
        raise RuntimeError(f"Failed to report sync failure for card {card_id}") from exc
