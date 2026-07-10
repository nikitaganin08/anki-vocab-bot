from __future__ import annotations

import asyncio
from dataclasses import dataclass

import edge_tts


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
class EdgeTtsPronunciationGenerator:
    voice: str

    def generate_audio(self, text: str) -> bytes:
        if not text.strip():
            raise PronunciationAudioError(
                "Pronunciation text must not be empty",
                user_message="Pronunciation audio generation failed: empty source text.",
            )

        try:
            audio_bytes = asyncio.run(self._generate_audio_bytes(text))
        except PronunciationAudioError:
            raise
        except Exception as exc:
            raise PronunciationAudioError(
                "edge-tts failed to synthesize pronunciation audio",
                user_message="Pronunciation audio generation failed.",
            ) from exc

        if not audio_bytes:
            raise PronunciationAudioError(
                "edge-tts produced empty audio output",
                user_message="Pronunciation audio generation failed: empty audio output.",
            )

        return audio_bytes

    async def _generate_audio_bytes(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
        )
        audio_chunks: list[bytes] = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data = chunk.get("data")
                if isinstance(data, bytes):
                    audio_chunks.append(data)

        return b"".join(audio_chunks)
