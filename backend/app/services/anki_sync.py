from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.clients.anki_connect import AnkiConnectError, AnkiNotePayload
from app.clients.backend_sync_api import BackendSyncApiError, PendingCard
from app.services.pronunciation import (
    PronunciationAudioError,
    build_pronunciation_filename,
    build_pronunciation_sound_field,
)

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

    def store_media_file(self, filename: str, data: bytes) -> None: ...

    def add_note(self, payload: AnkiNotePayload) -> int: ...


class PronunciationGateway(Protocol):
    @property
    def file_extension(self) -> str: ...

    def generate_audio(self, text: str) -> bytes: ...


def build_card_tag(card_id: int) -> str:
    return f"{CARD_TAG_PREFIX}-{card_id}"


def map_card_to_anki_payload(card: PendingCard, *, pronunciation_field: str) -> AnkiNotePayload:
    translation = ", ".join(card.translation_variants)
    example = "\n".join(card.examples[:2])
    fields = {
        "Word": card.canonical_text_normalized,
        "Transcription": card.transcription or "",
        "PronunciationAudio": pronunciation_field,
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
    pronunciation_generator: PronunciationGateway,
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
            file_extension = pronunciation_generator.file_extension
            filename = build_pronunciation_filename(card.id, file_extension)
            audio_bytes = pronunciation_generator.generate_audio(card.canonical_text)
            anki_client.store_media_file(filename, audio_bytes)
            payload = map_card_to_anki_payload(
                card,
                pronunciation_field=build_pronunciation_sound_field(card.id, file_extension),
            )
            anki_note_id = anki_client.add_note(payload)
        except PronunciationAudioError as exc:
            _report_failure(backend_client, card.id, exc.user_message)
            summary.failed += 1
            continue
        except AnkiConnectError as exc:
            _report_failure(backend_client, card.id, _format_anki_error_message(exc))
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


def _format_anki_error_message(exc: AnkiConnectError) -> str:
    if "PronunciationAudio" in exc.user_message:
        return "Anki note type is missing PronunciationAudio field."

    if "storeMediaFile" in str(exc):
        return f"Pronunciation audio upload failed: {exc.user_message}"

    return exc.user_message
