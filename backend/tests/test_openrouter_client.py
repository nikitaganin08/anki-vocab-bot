from __future__ import annotations

import json

import httpx
import pytest

from app.clients.openrouter import (
    OpenRouterClient,
    OpenRouterProtocolError,
    OpenRouterTimeoutError,
    OpenRouterTransportError,
)

VALID_COMPLETION_CONTENT = json.dumps(
    {
        "accepted": True,
        "source_text": "take off",
        "source_language": "en",
        "entry_type": "phrasal_verb",
        "canonical_text": "take off",
        "canonical_text_normalized": "take off",
        "transcription": "teik of",
        "translation_variants": ["взлетать", "снимать"],
        "explanation": "To leave the ground.",
        "examples": [
            "The plane will take off soon.",
            "Please take off your jacket.",
            "Sales began to take off in spring.",
        ],
        "frequency": 5,
        "frequency_note": "Common in spoken English.",
        "llm_model": "test-model",
    }
)


def test_openrouter_client_parses_valid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": VALID_COMPLETION_CONTENT}}]},
        )

    client = OpenRouterClient(
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = client.generate_card("take off")

    assert result.accepted is True
    assert result.canonical_text == "take off"


def test_openrouter_client_raises_transport_error_for_http_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    client = OpenRouterClient(
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(OpenRouterTransportError):
        client.generate_card("take off")


def test_openrouter_client_raises_protocol_error_for_invalid_contract() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        invalid_content = json.dumps({"accepted": True, "source_text": "take off"})
        return httpx.Response(200, json={"choices": [{"message": {"content": invalid_content}}]})

    client = OpenRouterClient(
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(OpenRouterProtocolError):
        client.generate_card("take off")


def test_openrouter_client_raises_timeout_error() -> None:
    class TimeoutClient:
        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

    client = OpenRouterClient(
        api_key="secret",
        model="test-model",
        http_client=TimeoutClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(OpenRouterTimeoutError):
        client.generate_card("take off")
