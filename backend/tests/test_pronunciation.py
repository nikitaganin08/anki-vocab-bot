from __future__ import annotations

import base64
import json
from collections.abc import Callable
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.api.deps as deps_mod
from app.api.deps import get_tts_client, is_tts_enabled
from app.main import app
from app.services.pronunciation import GoogleTtsClient, PronunciationAudioError, YandexTtsClient

from .conftest import TelegramSettingsStub, make_card, telegram_headers

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


def _yandex(handler: Callable[[httpx.Request], httpx.Response]) -> YandexTtsClient:
    return YandexTtsClient(
        api_key="yandex-key",
        voice="john",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_yandex_synthesize_posts_form_and_returns_raw_audio() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
        assert request.headers["Authorization"] == "Api-Key yandex-key"
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert parse_qs(request.content.decode()) == {
            "text": ["take off"],
            "lang": ["en-US"],
            "voice": ["john"],
            "format": ["mp3"],
        }
        return httpx.Response(200, content=b"mp3")

    assert _yandex(handler).synthesize("take off") == b"mp3"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"code": 16, "message": "Unauthorized"}),
        httpx.Response(200, content=b""),
    ],
)
def test_yandex_synthesize_raises_on_error_or_empty_body(response: httpx.Response) -> None:
    with pytest.raises(PronunciationAudioError):
        _yandex(lambda _: response).synthesize("take off")


def test_yandex_synthesize_raises_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(PronunciationAudioError):
        _yandex(handler).synthesize("take off")


def _configure(monkeypatch: pytest.MonkeyPatch, **keys: str) -> None:
    monkeypatch.setattr(deps_mod, "get_settings", lambda: TelegramSettingsStub(**keys))


def test_provider_is_yandex_when_only_yandex_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, yandex_tts_api_key="y", yandex_tts_voice="john")

    tts = get_tts_client()

    assert isinstance(tts, YandexTtsClient)
    assert (tts.api_key, tts.voice) == ("y", "john")
    assert is_tts_enabled() is True


def test_provider_is_google_when_only_google_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, google_tts_api_key="g")

    tts = get_tts_client()

    assert isinstance(tts, GoogleTtsClient)
    assert tts.api_key == "g"
    assert is_tts_enabled() is True


def test_yandex_wins_when_both_keys_are_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, yandex_tts_api_key="y", google_tts_api_key="g")

    assert isinstance(get_tts_client(), YandexTtsClient)
    assert is_tts_enabled() is True


def test_no_provider_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        get_tts_client()
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Pronunciation is not configured"
    assert is_tts_enabled() is False


class FakeTts:
    def __init__(self, error: PronunciationAudioError | None = None) -> None:
        self.error = error
        self.texts: list[str] = []

    def synthesize(self, text: str) -> bytes:
        self.texts.append(text)
        if self.error is not None:
            raise self.error
        return b"mp3"


AUDIO_URL = "/api/cards/{id}/audio"


def test_audio_endpoint_returns_mp3(client: TestClient, session: Session) -> None:
    card = make_card(canonical_text="Take Off")
    session.add(card)
    session.commit()
    fake = FakeTts()
    app.dependency_overrides[get_tts_client] = lambda: fake

    resp = client.get(AUDIO_URL.format(id=card.id), headers=telegram_headers())

    assert resp.status_code == 200
    assert resp.content == b"mp3"
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.headers["cache-control"] == CACHE_CONTROL
    assert fake.texts == ["Take Off"]


def test_audio_endpoint_speaks_a_chunk_or_example_of_the_card(
    client: TestClient, session: Session
) -> None:
    card = make_card(
        canonical_text="be had",
        chunks_json=[{"text": "being had by a scam", "target": "being had", "translation": "x"}],
        examples_json=["He felt foolish for being had."],
    )
    session.add(card)
    session.commit()
    fake = FakeTts()
    app.dependency_overrides[get_tts_client] = lambda: fake
    url = AUDIO_URL.format(id=card.id)

    chunk = client.get(url, params={"text": "being had by a scam"}, headers=telegram_headers())
    example = client.get(
        url, params={"text": "He felt foolish for being had."}, headers=telegram_headers()
    )
    other = client.get(url, params={"text": "read this aloud"}, headers=telegram_headers())

    assert chunk.status_code == example.status_code == 200
    assert fake.texts == ["being had by a scam", "He felt foolish for being had."]
    assert other.status_code == 400
    assert other.json() == {"detail": "Text is not part of the card"}


def test_audio_endpoint_is_503_without_key(client: TestClient, session: Session) -> None:
    card = make_card()
    session.add(card)
    session.commit()

    resp = client.get(AUDIO_URL.format(id=card.id), headers=telegram_headers())

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Pronunciation is not configured"}


def test_audio_endpoint_is_404_for_unknown_card(client: TestClient) -> None:
    app.dependency_overrides[get_tts_client] = lambda: FakeTts()

    resp = client.get(AUDIO_URL.format(id=999), headers=telegram_headers())

    assert resp.status_code == 404


def test_audio_endpoint_is_502_when_tts_fails(client: TestClient, session: Session) -> None:
    card = make_card()
    session.add(card)
    session.commit()
    error = PronunciationAudioError("403", user_message="Pronunciation service returned status 403")
    app.dependency_overrides[get_tts_client] = lambda: FakeTts(error)

    resp = client.get(AUDIO_URL.format(id=card.id), headers=telegram_headers())

    assert resp.status_code == 502
    assert resp.json() == {"detail": "Pronunciation service returned status 403"}


def test_audio_endpoint_requires_auth(client: TestClient) -> None:
    app.dependency_overrides[get_tts_client] = lambda: FakeTts()

    assert client.get(AUDIO_URL.format(id=1)).status_code in (401, 403)
