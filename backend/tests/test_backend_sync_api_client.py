from __future__ import annotations

import httpx
import pytest

from app.clients.backend_sync_api import (
    BackendSyncApiClient,
    BackendSyncApiProtocolError,
    BackendSyncApiTimeoutError,
    PendingCard,
)


def test_get_pending_parses_cards() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sync-token"
        assert request.url.path == "/api/anki/pending"
        assert request.url.params["limit"] == "5"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "canonical_text": "Take Off",
                    "canonical_text_normalized": "take off",
                    "transcription": "/teik of/",
                    "translation_variants": ["взлетать", "снимать"],
                    "explanation": "To leave the ground.",
                    "examples": ["The plane took off.", "Take off your coat.", "Sales took off."],
                }
            ],
        )

    client = BackendSyncApiClient(
        base_url="http://localhost:8000",
        token="sync-token",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    pending = client.get_pending(limit=5)
    assert pending == [
        PendingCard(
            id=1,
            canonical_text="Take Off",
            canonical_text_normalized="take off",
            transcription="/teik of/",
            translation_variants=["взлетать", "снимать"],
            explanation="To leave the ground.",
            examples=["The plane took off.", "Take off your coat.", "Sales took off."],
        )
    ]


def test_get_pending_raises_protocol_error_for_invalid_payload() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    client = BackendSyncApiClient(
        base_url="http://localhost:8000",
        token="sync-token",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(BackendSyncApiProtocolError):
        client.get_pending()


def test_ack_posts_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/anki/ack"
        assert request.method == "POST"
        assert request.read() == b'{"card_id":3,"anki_note_id":55}'
        return httpx.Response(204)

    client = BackendSyncApiClient(
        base_url="http://localhost:8000",
        token="sync-token",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    client.ack(3, 55)


def test_fail_posts_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/anki/fail"
        assert request.method == "POST"
        assert request.read() == b'{"card_id":4,"error_message":"boom"}'
        return httpx.Response(204)

    client = BackendSyncApiClient(
        base_url="http://localhost:8000",
        token="sync-token",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    client.fail(4, "boom")


def test_timeout_raises_timeout_error() -> None:
    class TimeoutClient:
        def request(self, *args: object, **kwargs: object) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

    client = BackendSyncApiClient(
        base_url="http://localhost:8000",
        token="sync-token",
        http_client=TimeoutClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(BackendSyncApiTimeoutError):
        client.get_pending()
