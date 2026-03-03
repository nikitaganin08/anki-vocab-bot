from __future__ import annotations

import pytest

from app.clients.anki_connect import AnkiConnectTransportError, AnkiNotePayload
from app.clients.backend_sync_api import BackendSyncApiTransportError, PendingCard
from app.services.anki_sync import map_card_to_anki_payload, sync_pending_cards


def _pending_card() -> PendingCard:
    return PendingCard(
        id=7,
        canonical_text="take off",
        transcription="/teik of/",
        translation_variants=["взлетать", "снимать"],
        explanation="To leave the ground.",
        examples=["The plane took off.", "Take off your coat.", "Sales took off."],
    )


def test_map_card_to_anki_payload_uses_required_field_mapping() -> None:
    payload = map_card_to_anki_payload(_pending_card())

    assert isinstance(payload, AnkiNotePayload)
    assert payload.deck_name == "English::Inbox"
    assert payload.model_name == "VocabularyCard"
    assert payload.fields["Word"] == "take off"
    assert payload.fields["Transcription"] == "/teik of/"
    assert payload.fields["Translation"] == "взлетать, снимать"
    assert payload.fields["Explanation"] == "To leave the ground."
    assert payload.fields["Example"] == "The plane took off.\nTake off your coat."
    assert payload.tags == ["avb-card-7"]


def test_sync_pending_cards_acks_successful_cards() -> None:
    class FakeBackendClient:
        def __init__(self) -> None:
            self.acks: list[tuple[int, int]] = []

        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            assert limit == 50
            return [_pending_card()]

        def ack(self, card_id: int, anki_note_id: int) -> None:
            self.acks.append((card_id, anki_note_id))

        def fail(self, card_id: int, error_message: str) -> None:
            raise AssertionError(f"Did not expect fail() for card={card_id}: {error_message}")

    class FakeAnkiClient:
        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return []

        def add_note(self, payload: AnkiNotePayload) -> int:
            assert payload.fields["Word"] == "take off"
            assert payload.tags == ["avb-card-7"]
            return 555

    backend = FakeBackendClient()
    anki = FakeAnkiClient()

    summary = sync_pending_cards(backend_client=backend, anki_client=anki)

    assert summary.total == 1
    assert summary.synced == 1
    assert summary.failed == 0
    assert backend.acks == [(7, 555)]


def test_sync_pending_cards_reports_failures() -> None:
    class FakeBackendClient:
        def __init__(self) -> None:
            self.failures: list[tuple[int, str]] = []

        def get_pending(self, limit: int = 50) -> list[PendingCard]:
            return [_pending_card()]

        def ack(self, card_id: int, anki_note_id: int) -> None:
            raise AssertionError(f"Did not expect ack() for card={card_id}, note={anki_note_id}")

        def fail(self, card_id: int, error_message: str) -> None:
            self.failures.append((card_id, error_message))

    class FakeAnkiClient:
        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return []

        def add_note(self, payload: AnkiNotePayload) -> int:
            raise AnkiConnectTransportError(
                "duplicate note",
                code="anki_connect_action_error",
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

        def ack(self, card_id: int, anki_note_id: int) -> None:
            raise AssertionError(f"Did not expect ack() for card={card_id}, note={anki_note_id}")

        def fail(self, card_id: int, error_message: str) -> None:
            raise BackendSyncApiTransportError(
                "backend down",
                code="backend_sync_transport",
                user_message="backend down",
            )

    class FakeAnkiClient:
        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return []

        def add_note(self, payload: AnkiNotePayload) -> int:
            raise AnkiConnectTransportError(
                "anki down",
                code="anki_connect_transport",
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

        def ack(self, card_id: int, anki_note_id: int) -> None:
            self.acks.append((card_id, anki_note_id))

        def fail(self, card_id: int, error_message: str) -> None:
            raise AssertionError(f"Did not expect fail() for card={card_id}: {error_message}")

    class FakeAnkiClient:
        def __init__(self) -> None:
            self.add_note_called = False

        def find_notes_by_tag(self, tag: str) -> list[int]:
            assert tag == "avb-card-7"
            return [777]

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
