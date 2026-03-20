from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.clients.anki_connect import AnkiConnectTransportError
from app.scripts.sync_anki import ensure_anki_connect_available, resolve_anki_desktop_launch_command


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


def monotonic_clock(values: list[float]) -> Iterator[float]:
    return iter(values)


def test_ensure_anki_connect_available_skips_launch_when_already_running() -> None:
    client = FakeAnkiClient([6])
    launches: list[list[str]] = []

    ensure_anki_connect_available(
        anki_client=client,
        startup_timeout_seconds=5.0,
        system_name="Darwin",
        launch_process=lambda command: launches.append(list(command)),
    )

    assert launches == []
    assert client.version_calls == 1


def test_ensure_anki_connect_available_launches_and_waits_until_ready() -> None:
    client = FakeAnkiClient(
        [
            AnkiConnectTransportError(
                "offline",
                code="anki_connect_transport",
                user_message="offline",
            ),
            AnkiConnectTransportError(
                "still offline",
                code="anki_connect_transport",
                user_message="still offline",
            ),
            6,
        ]
    )
    launches: list[list[str]] = []
    clock = monotonic_clock([0.0, 0.1, 0.2, 0.3])
    sleeps: list[float] = []

    ensure_anki_connect_available(
        anki_client=client,
        startup_timeout_seconds=5.0,
        system_name="Darwin",
        launch_process=lambda command: launches.append(list(command)),
        monotonic=lambda: next(clock),
        sleep=lambda seconds: sleeps.append(seconds),
    )

    assert launches == [["open", "-a", "Anki"]]
    assert sleeps == [0.5]
    assert client.version_calls == 3


def test_ensure_anki_connect_available_raises_without_launch_command() -> None:
    client = FakeAnkiClient(
        [
            AnkiConnectTransportError(
                "offline",
                code="anki_connect_transport",
                user_message="offline",
            )
        ]
    )

    with pytest.raises(RuntimeError, match="no default Anki launch command"):
        ensure_anki_connect_available(
            anki_client=client,
            startup_timeout_seconds=5.0,
            system_name="Plan9",
        )


def test_resolve_anki_desktop_launch_command_uses_platform_default() -> None:
    command = resolve_anki_desktop_launch_command(system_name="Darwin")

    assert command == ["open", "-a", "Anki"]
