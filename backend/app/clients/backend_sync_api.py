from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class PendingCard:
    id: int
    canonical_text: str
    transcription: str | None
    translation_variants: list[str]
    explanation: str
    examples: list[str]


class BackendSyncApiError(RuntimeError):
    def __init__(self, message: str, *, code: str, user_message: str) -> None:
        super().__init__(message)
        self.code = code
        self.user_message = user_message


class BackendSyncApiTransportError(BackendSyncApiError):
    pass


class BackendSyncApiTimeoutError(BackendSyncApiError):
    pass


class BackendSyncApiProtocolError(BackendSyncApiError):
    pass


@dataclass(slots=True)
class BackendSyncApiClient:
    base_url: str
    token: str
    timeout_seconds: float = 15.0
    http_client: httpx.Client | None = None

    def get_pending(self, limit: int = 50) -> list[PendingCard]:
        payload = self._request("GET", "/api/anki/pending", params={"limit": limit})
        if not isinstance(payload, list):
            raise BackendSyncApiProtocolError(
                "Pending response must be a list",
                code="backend_sync_invalid_pending",
                user_message="Backend pending payload is invalid.",
            )

        return [self._parse_pending_item(item) for item in payload]

    def ack(self, card_id: int, anki_note_id: int) -> None:
        self._request(
            "POST",
            "/api/anki/ack",
            json={"card_id": card_id, "anki_note_id": anki_note_id},
            expect_json=False,
        )

    def fail(self, card_id: int, error_message: str) -> None:
        self._request(
            "POST",
            "/api/anki/fail",
            json={"card_id": card_id, "error_message": error_message},
            expect_json=False,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> Any:
        url = f"{self.base_url.rstrip('/')}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

        if self.http_client is not None:
            return self._send(
                self.http_client,
                method,
                url,
                headers,
                params=params,
                json=json,
                expect_json=expect_json,
            )

        with httpx.Client(timeout=self.timeout_seconds) as client:
            return self._send(
                client,
                method,
                url,
                headers,
                params=params,
                json=json,
                expect_json=expect_json,
            )

    def _send(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        headers: dict[str, str],
        *,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        expect_json: bool,
    ) -> Any:
        try:
            response = client.request(method, url, headers=headers, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise BackendSyncApiTimeoutError(
                "Backend sync API request timed out",
                code="backend_sync_timeout",
                user_message="Backend sync API timed out.",
            ) from exc
        except httpx.HTTPError as exc:
            raise BackendSyncApiTransportError(
                "Backend sync API request failed",
                code="backend_sync_transport",
                user_message="Backend sync API is unavailable.",
            ) from exc

        if response.status_code >= 400:
            raise BackendSyncApiTransportError(
                f"Backend sync API returned status {response.status_code}",
                code="backend_sync_http_error",
                user_message=f"Backend sync API rejected the request with {response.status_code}.",
            )

        if not expect_json:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise BackendSyncApiProtocolError(
                "Backend sync API returned non-JSON payload",
                code="backend_sync_non_json",
                user_message="Backend sync API returned unreadable payload.",
            ) from exc

    @staticmethod
    def _parse_pending_item(item: Any) -> PendingCard:
        if not isinstance(item, dict):
            raise BackendSyncApiProtocolError(
                "Pending item must be an object",
                code="backend_sync_pending_item_type",
                user_message="Backend pending payload is invalid.",
            )

        required_keys = {
            "id",
            "canonical_text",
            "transcription",
            "translation_variants",
            "explanation",
            "examples",
        }
        if not required_keys.issubset(item.keys()):
            raise BackendSyncApiProtocolError(
                "Pending item is missing required keys",
                code="backend_sync_pending_item_missing_keys",
                user_message="Backend pending payload is missing required fields.",
            )

        card_id = item["id"]
        canonical_text = item["canonical_text"]
        transcription = item["transcription"]
        translation_variants = item["translation_variants"]
        explanation = item["explanation"]
        examples = item["examples"]

        if (
            not isinstance(card_id, int)
            or not isinstance(canonical_text, str)
            or not (transcription is None or isinstance(transcription, str))
            or not isinstance(translation_variants, list)
            or not all(isinstance(v, str) for v in translation_variants)
            or not isinstance(explanation, str)
            or not isinstance(examples, list)
            or not all(isinstance(v, str) for v in examples)
        ):
            raise BackendSyncApiProtocolError(
                "Pending item has invalid field types",
                code="backend_sync_pending_item_invalid_types",
                user_message="Backend pending payload has invalid field types.",
            )

        return PendingCard(
            id=card_id,
            canonical_text=canonical_text,
            transcription=transcription,
            translation_variants=translation_variants,
            explanation=explanation,
            examples=examples,
        )
