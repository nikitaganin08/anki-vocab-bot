from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

import app.api.telegram_webhook as webhook_api
from app.main import app


@dataclass
class DispatcherStub:
    calls: list[tuple[object, dict[str, Any]]] = field(default_factory=list)

    async def feed_raw_update(self, bot: object, update: dict[str, Any]) -> None:
        self.calls.append((bot, update))


@dataclass
class RuntimeStub:
    bot: object
    dispatcher: DispatcherStub
    webhook_secret: str


def test_webhook_rejects_invalid_secret() -> None:
    runtime = RuntimeStub(bot=object(), dispatcher=DispatcherStub(), webhook_secret="secret")
    original = webhook_api.get_bot_runtime
    webhook_api.get_bot_runtime = lambda: runtime
    try:
        with TestClient(app) as client:
            response = client.post(
                "/telegram/webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
                json={"update_id": 1},
            )
    finally:
        webhook_api.get_bot_runtime = original

    assert response.status_code == 403
    assert runtime.dispatcher.calls == []


def test_webhook_dispatches_valid_update() -> None:
    runtime = RuntimeStub(bot=object(), dispatcher=DispatcherStub(), webhook_secret="secret")
    original = webhook_api.get_bot_runtime
    webhook_api.get_bot_runtime = lambda: runtime
    try:
        with TestClient(app) as client:
            response = client.post(
                "/telegram/webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
                json={"update_id": 2, "message": {"text": "hello"}},
            )
    finally:
        webhook_api.get_bot_runtime = original

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(runtime.dispatcher.calls) == 1
    _, update = runtime.dispatcher.calls[0]
    assert update["update_id"] == 2


def test_webhook_rejects_non_json_payload() -> None:
    runtime = RuntimeStub(bot=object(), dispatcher=DispatcherStub(), webhook_secret="secret")
    original = webhook_api.get_bot_runtime
    webhook_api.get_bot_runtime = lambda: runtime
    try:
        with TestClient(app) as client:
            response = client.post(
                "/telegram/webhook",
                headers={
                    "X-Telegram-Bot-Api-Secret-Token": "secret",
                    "Content-Type": "application/json",
                },
                content="not-json",
            )
    finally:
        webhook_api.get_bot_runtime = original

    assert response.status_code == 400
    assert runtime.dispatcher.calls == []
