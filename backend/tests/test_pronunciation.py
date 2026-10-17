from __future__ import annotations

import base64
import json
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_tts_client
from app.main import app
from app.services.pronunciation import GoogleTtsClient, PronunciationAudioError

from .conftest import anki_headers, make_card, telegram_headers

CACHE_CONTROL = "private, max-age=31536000, immutable"


def _tts(handler: Callable[[httpx.Request], httpx.Response]) -> GoogleTtsClient:
    return GoogleTtsClient(
        api_key="google-key",
        voice="en-US-Chirp3-HD-Aoede",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_synthesize_posts_text_and_decodes_mp3() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://texttospeech.googleapis.com/v1/text:synthesize"
        assert request.headers["X-Goog-Api-Key"] == "google-key"
        assert json.loads(request.content) == {
            "input": {"text": "take off"},
            "voice": {"languageCode": "en-US", "name": "en-US-Chirp3-HD-Aoede"},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        return httpx.Response(200, json={"audioContent": base64.b64encode(b"mp3").decode()})

    assert _tts(handler).synthesize("take off") == b"mp3"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, json={"error": {"message": "API not enabled"}}),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"audioContent": ""}),
        httpx.Response(200, text="not json"),
    ],
)
def test_synthesize_raises_on_error_or_missing_audio(response: httpx.Response) -> None:
    with pytest.raises(PronunciationAudioError):
        _tts(lambda _: response).synthesize("take off")


def test_synthesize_raises_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(PronunciationAudioError):
        _tts(handler).synthesize("take off")


class FakeTts:
    def __init__(self, error: PronunciationAudioError | None = None) -> None:
        self.error = error
        self.texts: list[str] = []

    def synthesize(self, text: str) -> bytes:
        self.texts.append(text)
        if self.error is not None:
            raise self.error
        return b"mp3"


Headers = Callable[[], dict[str, str]]
AUDIO_ROUTES = [
    ("/api/cards/{id}/audio", telegram_headers),
    ("/api/anki/cards/{id}/audio", anki_headers),
]


@pytest.mark.parametrize(("route", "headers"), AUDIO_ROUTES)
def test_audio_endpoint_returns_mp3(
    client: TestClient, session: Session, route: str, headers: Headers
) -> None:
    card = make_card(canonical_text="Take Off")
    session.add(card)
    session.commit()
    fake = FakeTts()
    app.dependency_overrides[get_tts_client] = lambda: fake

    resp = client.get(route.format(id=card.id), headers=headers())

    assert resp.status_code == 200
    assert resp.content == b"mp3"
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.headers["cache-control"] == CACHE_CONTROL
    assert fake.texts == ["Take Off"]


@pytest.mark.parametrize(("route", "headers"), AUDIO_ROUTES)
def test_audio_endpoint_is_503_without_key(
    client: TestClient, session: Session, route: str, headers: Headers
) -> None:
    card = make_card()
    session.add(card)
    session.commit()

    resp = client.get(route.format(id=card.id), headers=headers())

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Pronunciation is not configured"}


@pytest.mark.parametrize(("route", "headers"), AUDIO_ROUTES)
def test_audio_endpoint_is_404_for_unknown_card(
    client: TestClient, route: str, headers: Headers
) -> None:
    app.dependency_overrides[get_tts_client] = lambda: FakeTts()

    resp = client.get(route.format(id=999), headers=headers())

    assert resp.status_code == 404


@pytest.mark.parametrize(("route", "headers"), AUDIO_ROUTES)
def test_audio_endpoint_is_502_when_tts_fails(
    client: TestClient, session: Session, route: str, headers: Headers
) -> None:
    card = make_card()
    session.add(card)
    session.commit()
    error = PronunciationAudioError("403", user_message="Pronunciation service returned status 403")
    app.dependency_overrides[get_tts_client] = lambda: FakeTts(error)

    resp = client.get(route.format(id=card.id), headers=headers())

    assert resp.status_code == 502
    assert resp.json() == {"detail": "Pronunciation service returned status 403"}


@pytest.mark.parametrize(("route", "_headers"), AUDIO_ROUTES)
def test_audio_endpoint_requires_auth(client: TestClient, route: str, _headers: Headers) -> None:
    app.dependency_overrides[get_tts_client] = lambda: FakeTts()

    assert client.get(route.format(id=1)).status_code in (401, 403)
