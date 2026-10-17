from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


class PronunciationAudioError(RuntimeError):
    def __init__(self, message: str, *, user_message: str) -> None:
        super().__init__(message)
        self.user_message = user_message


def build_pronunciation_filename(card_id: int) -> str:
    return f"avb-pronunciation-{card_id}.mp3"


def build_pronunciation_sound_field(card_id: int) -> str:
    filename = build_pronunciation_filename(card_id)
    return f"[sound:{filename}]"


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
        headers = {"X-Goog-Api-Key": self.api_key}
        try:
            if self.http_client is not None:
                response = self.http_client.post(GOOGLE_TTS_URL, json=body, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(GOOGLE_TTS_URL, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise PronunciationAudioError(
                f"Google TTS request failed: {exc!r}",
                user_message="Pronunciation service is unreachable",
            ) from exc

        if response.is_error:
            raise PronunciationAudioError(
                f"Google TTS returned status {response.status_code}: {response.text[:300]}",
                user_message=f"Pronunciation service returned status {response.status_code}",
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
