from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


class PronunciationAudioError(RuntimeError):
    def __init__(self, message: str, *, user_message: str) -> None:
        super().__init__(message)
        self.user_message = user_message


def build_pronunciation_filename(card_id: int) -> str:
    return f"avb-pronunciation-{card_id}.mp3"


def build_pronunciation_sound_field(card_id: int) -> str:
    filename = build_pronunciation_filename(card_id)
    return f"[sound:{filename}]"


class TtsClient(Protocol):
    def synthesize(self, text: str) -> bytes: ...


def _post(
    provider: str,
    url: str,
    *,
    http_client: httpx.Client | None,
    timeout_seconds: float,
    **request: Any,
) -> httpx.Response:
    """POST and map network errors and non-2xx statuses to PronunciationAudioError."""
    try:
        if http_client is not None:
            response = http_client.post(url, **request)
        else:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(url, **request)
    except httpx.HTTPError as exc:
        raise PronunciationAudioError(
            f"{provider} TTS request failed: {exc!r}",
            user_message="Pronunciation service is unreachable",
        ) from exc
    if response.is_error:
        raise PronunciationAudioError(
            f"{provider} TTS returned status {response.status_code}: {response.text[:300]}",
            user_message=f"Pronunciation service returned status {response.status_code}",
        )
    return response


@dataclass(slots=True)
class GoogleTtsClient:
    api_key: str
    voice: str
    http_client: httpx.Client | None = None
    timeout_seconds: float = 15.0

    def synthesize(self, text: str) -> bytes:
        body = {
            "input": {"text": text},
            # "en-US-Chirp3-HD-Aoede" -> "en-US"
            "voice": {"languageCode": "-".join(self.voice.split("-")[:2]), "name": self.voice},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        # The key goes in a header, not ?key=, so httpx request logs never show it.
        response = _post(
            "Google",
            GOOGLE_TTS_URL,
            http_client=self.http_client,
            timeout_seconds=self.timeout_seconds,
            json=body,
            headers={"X-Goog-Api-Key": self.api_key},
        )
        try:
            audio = base64.b64decode(response.json()["audioContent"])
        except (ValueError, KeyError, TypeError) as exc:
            raise PronunciationAudioError(
                "Google TTS response has no audioContent",
                user_message="Pronunciation service returned no audio",
            ) from exc
        if not audio:
            raise PronunciationAudioError(
                "Google TTS returned empty audioContent",
                user_message="Pronunciation service returned no audio",
            )
        return audio


@dataclass(slots=True)
class YandexTtsClient:
    api_key: str
    voice: str
    http_client: httpx.Client | None = None
    timeout_seconds: float = 15.0

    def synthesize(self, text: str) -> bytes:
        # SpeechKit v1 accepts up to 5000 characters; our texts are 1-8 tokens.
        response = _post(
            "Yandex",
            YANDEX_TTS_URL,
            http_client=self.http_client,
            timeout_seconds=self.timeout_seconds,
            # No folderId: a service-account API key already knows its folder.
            data={"text": text, "lang": "en-US", "voice": self.voice, "format": "mp3"},
            headers={"Authorization": f"Api-Key {self.api_key}"},
        )
        if not response.content:
            raise PronunciationAudioError(
                "Yandex TTS returned an empty body",
                user_message="Pronunciation service returned no audio",
            )
        return response.content
