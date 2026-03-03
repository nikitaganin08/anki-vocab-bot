from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

DEFAULT_ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DEFAULT_ANKI_CONNECT_VERSION = 6


class AnkiConnectError(RuntimeError):
    def __init__(self, message: str, *, code: str, user_message: str) -> None:
        super().__init__(message)
        self.code = code
        self.user_message = user_message


class AnkiConnectTransportError(AnkiConnectError):
    pass


class AnkiConnectTimeoutError(AnkiConnectError):
    pass


class AnkiConnectProtocolError(AnkiConnectError):
    pass


@dataclass(slots=True)
class AnkiNotePayload:
    deck_name: str
    model_name: str
    fields: dict[str, str]
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnkiConnectClient:
    endpoint: str = DEFAULT_ANKI_CONNECT_URL
    version: int = DEFAULT_ANKI_CONNECT_VERSION
    timeout_seconds: float = 10.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.3
    http_client: httpx.Client | None = None
    sleeper: Callable[[float], None] = time.sleep

    def add_note(self, payload: AnkiNotePayload) -> int:
        params = {
            "note": {
                "deckName": payload.deck_name,
                "modelName": payload.model_name,
                "fields": payload.fields,
                "tags": payload.tags,
            }
        }
        result = self._request_with_retry("addNote", params)
        if not isinstance(result, int):
            raise AnkiConnectProtocolError(
                "AnkiConnect addNote result is not an integer note id",
                code="anki_connect_invalid_note_id",
                user_message="AnkiConnect returned an invalid note ID.",
            )
        return result

    def find_notes_by_tag(self, tag: str) -> list[int]:
        result = self._request_with_retry("findNotes", {"query": f"tag:{tag}"})
        if not isinstance(result, list) or not all(isinstance(item, int) for item in result):
            raise AnkiConnectProtocolError(
                "AnkiConnect findNotes result is not a list of note ids",
                code="anki_connect_invalid_find_notes_result",
                user_message="AnkiConnect returned invalid findNotes response.",
            )
        return result

    def _request_with_retry(self, action: str, params: dict[str, Any]) -> Any:
        attempt = 0
        while True:
            try:
                return self._request(action, params)
            except (AnkiConnectTransportError, AnkiConnectTimeoutError):
                if attempt >= self.max_retries:
                    raise
                attempt += 1
                self.sleeper(self.retry_backoff_seconds * attempt)

    def _request(self, action: str, params: dict[str, Any]) -> Any:
        payload = {
            "action": action,
            "version": self.version,
            "params": params,
        }

        if self.http_client is not None:
            return self._send(self.http_client, payload)

        with httpx.Client(timeout=self.timeout_seconds) as client:
            return self._send(client, payload)

    def _send(self, client: httpx.Client, payload: dict[str, Any]) -> Any:
        try:
            response = client.post(self.endpoint, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AnkiConnectTimeoutError(
                "AnkiConnect request timed out",
                code="anki_connect_timeout",
                user_message="AnkiConnect timed out.",
            ) from exc
        except httpx.HTTPError as exc:
            raise AnkiConnectTransportError(
                "AnkiConnect request failed",
                code="anki_connect_transport",
                user_message="Could not reach AnkiConnect.",
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise AnkiConnectProtocolError(
                "AnkiConnect returned non-JSON payload",
                code="anki_connect_non_json",
                user_message="AnkiConnect returned unreadable payload.",
            ) from exc

        if not isinstance(data, dict) or "error" not in data or "result" not in data:
            raise AnkiConnectProtocolError(
                "AnkiConnect response is missing required keys",
                code="anki_connect_missing_keys",
                user_message="AnkiConnect response format is invalid.",
            )

        error = data["error"]
        if error is not None:
            error_message = str(error)
            raise AnkiConnectTransportError(
                f"AnkiConnect action failed: {error_message}",
                code="anki_connect_action_error",
                user_message=error_message,
            )

        return data["result"]
