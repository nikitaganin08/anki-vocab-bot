from __future__ import annotations

import pytest

import app.scripts.sync_anki as sync_anki
from app.clients.anki_connect import AnkiConnectTransportError
from app.scripts.sync_anki import ensure_anki_connect_available

OFFLINE = AnkiConnectTransportError("offline", user_message="offline")


class FakeAnkiClient:
    def __init__(self, responses: list[int | Exception]) -> None:
        self._responses = iter(responses)
        self.version_calls = 0

    def get_version(self) -> int:
        self.version_calls += 1
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def launches(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(sync_anki.subprocess, "Popen", lambda command, **_: calls.append(command))
    monkeypatch.setattr(sync_anki.time, "sleep", lambda _: None)
    return calls


def test_skips_launch_when_already_running(launches: list[list[str]]) -> None:
    client = FakeAnkiClient([6])

    ensure_anki_connect_available(anki_client=client, startup_timeout_seconds=5.0)

    assert launches == []
    assert client.version_calls == 1


def test_launches_and_waits_until_ready(launches: list[list[str]]) -> None:
    client = FakeAnkiClient([OFFLINE, OFFLINE, 6])

    ensure_anki_connect_available(anki_client=client, startup_timeout_seconds=5.0)

    assert launches == [["open", "-a", "Anki"]]
    assert client.version_calls == 3


def test_raises_when_anki_never_comes_up(launches: list[list[str]]) -> None:
    client = FakeAnkiClient([OFFLINE])

    with pytest.raises(RuntimeError, match="did not become reachable"):
        ensure_anki_connect_available(anki_client=client, startup_timeout_seconds=0.0)
