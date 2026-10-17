from __future__ import annotations

import pytest

from app.clients.anki_connect import AnkiConnectTransportError, AnkiNotePayload
from app.clients.backend_sync_api import BackendSyncApiError, PendingCard
from app.schemas.llm import CardChunk, WordFamilyItem
from app.services.anki_sync import (
    format_anki_example,
    map_card_to_anki_payload,
    sync_pending_cards,
)


def _pending_card() -> PendingCard:
    return PendingCard(
        id=7,
        canonical_text="Take Off",
        canonical_text_normalized="take off",
        transcription="/teik of/",
        translation_variants=["взлетать", "снимать"],
        explanation="To leave the ground.",
        examples=["The plane took off.", "Take off your coat.", "Sales took off."],
    )


def test_map_card_to_anki_payload_uses_required_field_mapping() -> None:
    payload = map_card_to_anki_payload(
        _pending_card(),
        pronunciation_field="[sound:avb-pronunciation-7.mp3]",
    )

    assert isinstance(payload, AnkiNotePayload)
    assert payload.deck_name == "English::Inbox"
    assert payload.model_name == "VocabularyCard"
    assert payload.fields["Word"] == "take off"
    assert payload.fields["Transcription"] == "/teik of/"
    assert payload.fields["PronunciationAudio"] == "[sound:avb-pronunciation-7.mp3]"
    assert payload.fields["Translation"] == "взлетать, снимать"
    assert payload.fields["Explanation"] == "To leave the ground."
    assert payload.fields["Example"] == "The plane took off."
    assert payload.tags == ["avb-card-7"]


def test_map_card_to_anki_payload_appends_word_family_to_example() -> None:
    card = _pending_card()
    card.word_family = [
        WordFamilyItem(
            word="accommodation",
            part_of_speech="noun",
            translation="размещение",
        )
    ]

    payload = map_card_to_anki_payload(
        card,
        pronunciation_field="[sound:avb-pronunciation-7.mp3]",
    )

    assert payload.fields["Example"] == (
        "The plane took off.\n\nWord family:\naccommodation (noun) - размещение"
    )


def test_anki_example_lists_chunks_then_example() -> None:
    chunks = [
        CardChunk(text="take off your coat", target="take off", translation="снять пальто"),
        CardChunk(text="the plane took off", target="took off", translation="самолёт взлетел"),
    ]
    family = [WordFamilyItem(word="takeoff", part_of_speech="noun", translation="взлёт")]

    assert format_anki_example(chunks, ["Sales took off.", "Unused."], family) == (
        "take off your coat — снять пальто\n"
        "the plane took off — самолёт взлетел\n\n"
        "Sales took off.\n\n"
        "Word family:\ntakeoff (noun) - взлёт"
    )


def test_map_card_to_anki_payload_includes_chunks() -> None:
    card = PendingCard.model_validate(
        {
            **_pending_card().model_dump(),
            "chunks": [
                {"text": "take off your coat", "target": "take off", "translation": "снять пальто"}
            ],
        }
    )

    payload = map_card_to_anki_payload(card, pronunciation_field="")

    assert payload.fields["Example"] == "take off your coat — снять пальто\n\nThe plane took off."


def test_sync_pending_cards_acks_successful_cards() -> None:
    class FakeBackendClient:
        def __init__(self) -> None:
            self.acks: list[tuple[int, int]] = []
            self.audio_calls: list[int] = []

        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            assert limit == 50
            return [_pending_card()]

        def get_card_audio(self, card_id: int) -> bytes:
            self.audio_calls.append(card_id)
            return b"audio"

        def ack(self, card_id: int, anki_note_id: int) -> None:
            self.acks.append((card_id, anki_note_id))

        def fail(self, card_id: int, error_message: str) -> None:
            raise AssertionError(f"Did not expect fail() for card={card_id}: {error_message}")

    class FakeAnkiClient:
        def __init__(self) -> None:
            self.uploads: list[tuple[str, bytes]] = []

        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return []

        def store_media_file(self, filename: str, data: bytes) -> None:
            self.uploads.append((filename, data))

        def add_note(self, payload: AnkiNotePayload) -> int:
            assert payload.fields["Word"] == "take off"
            assert payload.fields["PronunciationAudio"] == "[sound:avb-pronunciation-7.mp3]"
            assert payload.tags == ["avb-card-7"]
            return 555

    backend = FakeBackendClient()
    anki = FakeAnkiClient()

    summary = sync_pending_cards(backend_client=backend, anki_client=anki)

    assert summary.total == 1
    assert summary.synced == 1
    assert summary.failed == 0
    assert backend.acks == [(7, 555)]
    assert anki.uploads == [("avb-pronunciation-7.mp3", b"audio")]
    assert backend.audio_calls == [7]


def test_sync_pending_cards_reports_failures() -> None:
    class FakeBackendClient:
        def __init__(self) -> None:
            self.failures: list[tuple[int, str]] = []

        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            return [_pending_card()]

        def get_card_audio(self, card_id: int) -> bytes:
            return b"audio"

        def ack(self, card_id: int, anki_note_id: int) -> None:
            raise AssertionError(f"Did not expect ack() for card={card_id}, note={anki_note_id}")

        def fail(self, card_id: int, error_message: str) -> None:
            self.failures.append((card_id, error_message))

    class FakeAnkiClient:
        def store_media_file(self, filename: str, data: bytes) -> None:
            assert filename == "avb-pronunciation-7.mp3"
            assert data == b"audio"

        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return []

        def add_note(self, payload: AnkiNotePayload) -> int:
            raise AnkiConnectTransportError(
                "duplicate note",
                user_message="duplicate note",
            )

    backend = FakeBackendClient()
    anki = FakeAnkiClient()

    summary = sync_pending_cards(backend_client=backend, anki_client=anki)

    assert summary.total == 1
    assert summary.synced == 0
    assert summary.failed == 1
    assert backend.failures == [(7, "duplicate note")]


def test_sync_pending_cards_raises_if_fail_reporting_breaks() -> None:
    class FakeBackendClient:
        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            return [_pending_card()]

        def get_card_audio(self, card_id: int) -> bytes:
            return b"audio"

        def ack(self, card_id: int, anki_note_id: int) -> None:
            raise AssertionError(f"Did not expect ack() for card={card_id}, note={anki_note_id}")

        def fail(self, card_id: int, error_message: str) -> None:
            raise BackendSyncApiError("backend down")

    class FakeAnkiClient:
        def store_media_file(self, filename: str, data: bytes) -> None:
            assert filename == "avb-pronunciation-7.mp3"
            assert data == b"audio"

        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return []

        def add_note(self, payload: AnkiNotePayload) -> int:
            raise AnkiConnectTransportError(
                "anki down",
                user_message="anki down",
            )

    with pytest.raises(RuntimeError):
        sync_pending_cards(backend_client=FakeBackendClient(), anki_client=FakeAnkiClient())


def test_sync_pending_cards_uses_existing_tagged_note_idempotently() -> None:
    class FakeBackendClient:
        def __init__(self) -> None:
            self.acks: list[tuple[int, int]] = []

        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            return [_pending_card()]

        def get_card_audio(self, card_id: int) -> bytes:
            raise AssertionError("Did not expect audio for an already synced note")

        def ack(self, card_id: int, anki_note_id: int) -> None:
            self.acks.append((card_id, anki_note_id))

        def fail(self, card_id: int, error_message: str) -> None:
            raise AssertionError(f"Did not expect fail() for card={card_id}: {error_message}")

    class FakeAnkiClient:
        def __init__(self) -> None:
            self.add_note_called = False
            self.store_media_called = False

        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return [777]

        def store_media_file(self, filename: str, data: bytes) -> None:
            self.store_media_called = True

        def add_note(self, payload: AnkiNotePayload) -> int:
            self.add_note_called = True
            return 999

    backend = FakeBackendClient()
    anki = FakeAnkiClient()

    summary = sync_pending_cards(backend_client=backend, anki_client=anki)

    assert summary.total == 1
    assert summary.synced == 1
    assert summary.failed == 0
    assert backend.acks == [(7, 777)]
    assert anki.add_note_called is False
    assert anki.store_media_called is False


def test_sync_pending_cards_adds_note_without_audio_when_backend_audio_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FakeBackendClient:
        def __init__(self) -> None:
            self.acks: list[tuple[int, int]] = []
            self.audio_calls: list[int] = []

        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            second = _pending_card()
            second.id = 8
            return [_pending_card(), second]

        def get_card_audio(self, card_id: int) -> bytes:
            self.audio_calls.append(card_id)
            raise BackendSyncApiError(
                'Backend sync API returned status 503: {"detail":"Pronunciation is not configured"}'
            )

        def ack(self, card_id: int, anki_note_id: int) -> None:
            self.acks.append((card_id, anki_note_id))

        def fail(self, card_id: int, error_message: str) -> None:
            raise AssertionError(f"Did not expect fail() for card={card_id}: {error_message}")

    class FakeAnkiClient:
        def __init__(self) -> None:
            self.audio_fields: list[str] = []

        def find_notes_by_tag(self, tag: str) -> list[int]:
            return []

        def store_media_file(self, filename: str, data: bytes) -> None:
            raise AssertionError("Did not expect media upload after TTS failure")

        def add_note(self, payload: AnkiNotePayload) -> int:
            self.audio_fields.append(payload.fields["PronunciationAudio"])
            return 500 + len(self.audio_fields)

    backend = FakeBackendClient()
    anki = FakeAnkiClient()

    summary = sync_pending_cards(backend_client=backend, anki_client=anki)

    assert summary.total == 2
    assert summary.synced == 2
    assert summary.failed == 0
    assert anki.audio_fields == ["", ""]
    assert backend.acks == [(7, 501), (8, 502)]
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "Pronunciation is not configured" in warnings[0].getMessage()
    # After the first failure the run stops requesting audio.
    assert backend.audio_calls == [7]
