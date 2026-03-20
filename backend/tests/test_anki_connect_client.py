from __future__ import annotations

import httpx
import pytest

from app.clients.anki_connect import (
    AnkiConnectClient,
    AnkiConnectProtocolError,
    AnkiConnectTimeoutError,
    AnkiConnectTransportError,
    AnkiNotePayload,
)


def _note_payload() -> AnkiNotePayload:
    return AnkiNotePayload(
        deck_name="English::Inbox",
        model_name="VocabularyCard",
        fields={
            "Word": "take off",
            "Transcription": "/teik of/",
            "Translation": "взлетать, снимать",
            "Explanation": "To leave the ground.",
            "Example": "The plane took off.\nTake off your shoes.",
        },
    )


def test_add_note_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode("utf-8")
        assert '"action":"addNote"' in payload
        assert '"version":6' in payload
        assert '"tags":[]' in payload
        return httpx.Response(200, json={"result": 12345, "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.add_note(_note_payload()) == 12345


def test_add_note_retries_then_succeeds() -> None:
    class FlakyClient:
        def __init__(self) -> None:
            self.calls = 0

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            self.calls += 1
            if self.calls == 1:
                raise httpx.TimeoutException("timeout")
            return httpx.Response(
                200,
                json={"result": 42, "error": None},
                request=httpx.Request("POST", "http://127.0.0.1:8765"),
            )

    flaky = FlakyClient()
    client = AnkiConnectClient(
        http_client=flaky,  # type: ignore[arg-type]
        max_retries=2,
        sleeper=lambda _: None,
    )

    note_id = client.add_note(_note_payload())

    assert note_id == 42
    assert flaky.calls == 2


def test_add_note_raises_transport_error_for_action_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": None, "error": "duplicate note"})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AnkiConnectTransportError):
        client.add_note(_note_payload())


def test_add_note_raises_protocol_error_for_invalid_result() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": "not-an-int", "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AnkiConnectProtocolError):
        client.add_note(_note_payload())


def test_add_note_raises_timeout_after_retries() -> None:
    class TimeoutClient:
        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

    client = AnkiConnectClient(
        http_client=TimeoutClient(),  # type: ignore[arg-type]
        max_retries=1,
        sleeper=lambda _: None,
    )

    with pytest.raises(AnkiConnectTimeoutError):
        client.add_note(_note_payload())


def test_find_notes_by_tag_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode("utf-8")
        assert '"action":"findNotes"' in payload
        assert '"query":"tag:avb-card-7"' in payload
        return httpx.Response(200, json={"result": [777], "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.find_notes_by_tag("avb-card-7") == [777]


def test_get_version_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode("utf-8")
        assert '"action":"version"' in payload
        return httpx.Response(200, json={"result": 6, "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.get_version() == 6


def test_get_version_raises_protocol_error_for_invalid_result() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": "6", "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AnkiConnectProtocolError):
        client.get_version()


def test_find_notes_by_tag_raises_protocol_error_for_non_int_list() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": ["not-int"], "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AnkiConnectProtocolError):
        client.find_notes_by_tag("avb-card-7")


def test_store_media_file_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode("utf-8")
        assert '"action":"storeMediaFile"' in payload
        assert '"filename":"avb-pronunciation-7.mp3"' in payload
        assert '"data":"YXVkaW8="' in payload
        return httpx.Response(200, json={"result": "avb-pronunciation-7.mp3", "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    client.store_media_file("avb-pronunciation-7.mp3", b"audio")


def test_store_media_file_accepts_null_result() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": None, "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    client.store_media_file("avb-pronunciation-7.mp3", b"audio")


def test_store_media_file_raises_protocol_error_for_unexpected_result() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": "unexpected", "error": None})

    client = AnkiConnectClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AnkiConnectProtocolError):
        client.store_media_file("avb-pronunciation-7.mp3", b"audio")
