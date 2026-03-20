from __future__ import annotations

import argparse
import platform
import shlex
import subprocess
import time
from collections.abc import Callable, Sequence

from app.clients.anki_connect import (
    AnkiConnectClient,
    AnkiConnectError,
    AnkiConnectTimeoutError,
    AnkiConnectTransportError,
)
from app.clients.backend_sync_api import BackendSyncApiClient, BackendSyncApiError
from app.core.config import get_settings
from app.services.anki_sync import sync_pending_cards
from app.services.pronunciation import EdgeTtsPronunciationGenerator

ANKI_CONNECT_POLL_INTERVAL_SECONDS = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync eligible cards from backend to Anki.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of pending cards to sync in one run.",
    )
    return parser.parse_args()


def ensure_anki_connect_available(
    *,
    anki_client: AnkiConnectClient,
    configured_launch_command: str | None,
    startup_timeout_seconds: float,
    system_name: str | None = None,
    launch_process: Callable[[Sequence[str]], None] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if _anki_connect_is_available(anki_client):
        return
    if startup_timeout_seconds <= 0:
        raise RuntimeError("ANKI_DESKTOP_STARTUP_TIMEOUT_SECONDS must be greater than zero")

    launch_command = resolve_anki_desktop_launch_command(
        configured_launch_command,
        system_name=system_name,
    )
    if launch_command is None:
        raise RuntimeError(
            "AnkiConnect is not reachable and no default Anki launch command is available "
            "for this platform. Set ANKI_DESKTOP_LAUNCH_COMMAND."
        )

    launcher = launch_process or launch_anki_desktop
    print(f"AnkiConnect unavailable, launching Anki with: {format_shell_command(launch_command)}")
    launcher(launch_command)
    wait_for_anki_connect(
        anki_client=anki_client,
        timeout_seconds=startup_timeout_seconds,
        monotonic=monotonic,
        sleep=sleep,
    )


def resolve_anki_desktop_launch_command(
    configured_launch_command: str | None,
    *,
    system_name: str | None = None,
) -> list[str] | None:
    if configured_launch_command is not None:
        command = shlex.split(configured_launch_command)
        if not command:
            raise RuntimeError("ANKI_DESKTOP_LAUNCH_COMMAND must not be empty")
        return command

    detected_system = system_name or platform.system()
    if detected_system == "Darwin":
        return ["open", "-a", "Anki"]
    if detected_system == "Linux":
        return ["anki"]
    if detected_system == "Windows":
        return ["cmd", "/c", "start", "", "anki"]
    return None


def launch_anki_desktop(command: Sequence[str]) -> None:
    try:
        subprocess.Popen(  # noqa: S603
            list(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not launch Anki with {format_shell_command(command)}: {exc}"
        ) from exc


def wait_for_anki_connect(
    *,
    anki_client: AnkiConnectClient,
    timeout_seconds: float,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        if _anki_connect_is_available(anki_client):
            return
        sleep(ANKI_CONNECT_POLL_INTERVAL_SECONDS)

    raise RuntimeError(
        f"Anki launched but AnkiConnect did not become reachable within {timeout_seconds:g}s"
    )


def _anki_connect_is_available(anki_client: AnkiConnectClient) -> bool:
    try:
        anki_client.get_version()
    except (AnkiConnectTransportError, AnkiConnectTimeoutError):
        return False
    return True


def format_shell_command(command: Sequence[str]) -> str:
    return shlex.join(command)


def main() -> None:
    args = parse_args()
    settings = get_settings()

    if not settings.anki_sync_token:
        raise RuntimeError("ANKI_SYNC_TOKEN is required to run sync-anki")

    limit = args.limit if args.limit is not None else settings.anki_sync_batch_limit
    backend_client = BackendSyncApiClient(
        base_url=settings.backend_api_base_url,
        token=settings.anki_sync_token,
        timeout_seconds=settings.anki_sync_http_timeout_seconds,
    )
    anki_client = AnkiConnectClient(
        endpoint=settings.anki_connect_url,
        timeout_seconds=settings.anki_sync_http_timeout_seconds,
    )
    ensure_anki_connect_available(
        anki_client=anki_client,
        configured_launch_command=settings.anki_desktop_launch_command,
        startup_timeout_seconds=settings.anki_desktop_startup_timeout_seconds,
    )
    pronunciation_generator = EdgeTtsPronunciationGenerator(
        voice=settings.anki_pronunciation_voice,
        audio_format=settings.anki_pronunciation_format,
    )

    try:
        summary = sync_pending_cards(
            backend_client=backend_client,
            anki_client=anki_client,
            pronunciation_generator=pronunciation_generator,
            limit=limit,
        )
    except (BackendSyncApiError, AnkiConnectError, RuntimeError) as exc:
        raise SystemExit(f"sync-anki failed: {exc}") from exc

    print(
        "sync-anki complete: "
        f"total={summary.total}, synced={summary.synced}, failed={summary.failed}"
    )


if __name__ == "__main__":
    main()
