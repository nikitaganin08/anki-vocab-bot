from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas.llm import LlmResponse, parse_llm_response
from app.services.llm_prompt import build_llm_messages

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterError(RuntimeError):
    def __init__(self, message: str, *, code: str, user_message: str) -> None:
        super().__init__(message)
        self.code = code
        self.user_message = user_message


class OpenRouterTransportError(OpenRouterError):
    pass


class OpenRouterTimeoutError(OpenRouterError):
    pass


class OpenRouterProtocolError(OpenRouterError):
    pass


@dataclass(slots=True)
class OpenRouterClient:
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    base_url: str = OPENROUTER_BASE_URL
    app_name: str = "anki-vocab-bot"
    http_client: httpx.Client | None = None

    def generate_card(self, source_text: str) -> LlmResponse:
        payload = {
            "model": self.model,
            "messages": build_llm_messages(source_text),
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.anki-vocab-bot",
            "X-Title": self.app_name,
        }
        url = f"{self.base_url}/chat/completions"

        if self.http_client is not None:
            response = self._send_request(self.http_client, url, payload, headers)
            return self._parse_response(response)

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = self._send_request(client, url, payload, headers)
            return self._parse_response(response)

    def _send_request(
        self,
        client: httpx.Client,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        try:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OpenRouterTimeoutError(
                "OpenRouter request timed out",
                code="openrouter_timeout",
                user_message="The language model timed out. Please try again.",
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenRouterTransportError(
                "OpenRouter request failed",
                code="openrouter_transport_error",
                user_message="The language model is temporarily unavailable. Please try again.",
            ) from exc

        return response

    def _parse_response(self, response: httpx.Response) -> LlmResponse:
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise OpenRouterProtocolError(
                "OpenRouter returned non-JSON response",
                code="openrouter_non_json",
                user_message=(
                    "The language model returned an unreadable response. Please try again."
                ),
            ) from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as exc:
            raise OpenRouterProtocolError(
                "OpenRouter payload is missing message content",
                code="openrouter_missing_content",
                user_message=(
                    "The language model returned an incomplete response. Please try again."
                ),
            ) from exc

        try:
            return parse_llm_response(self._extract_content(content))
        except ValueError as exc:
            raise OpenRouterProtocolError(
                "OpenRouter payload did not contain valid contract JSON",
                code="openrouter_invalid_contract",
                user_message=(
                    "The language model returned an invalid card response. Please try again."
                ),
            ) from exc

    @staticmethod
    def _extract_content(content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, Sequence):
            text_chunks: list[str] = []
            for item in content:
                if (
                    isinstance(item, dict)
                    and item.get("type") == "text"
                    and isinstance(item.get("text"), str)
                ):
                    text_chunks.append(item["text"])
            if text_chunks:
                return "".join(text_chunks)

        raise ValueError("OpenRouter message content must be a string or text parts")
