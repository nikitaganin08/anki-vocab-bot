from __future__ import annotations

import argparse
import subprocess
import time

from app.clients.anki_connect import (
    AnkiConnectClient,
    AnkiConnectError,
    AnkiConnectTimeoutError,
    AnkiConnectTransportError,
)
from app.clients.backend_sync_api import BackendSyncApiClient, BackendSyncApiError
from app.core.config import get_settings
from app.services.anki_sync import sync_pending_cards

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
    startup_timeout_seconds: float,
) -> None:
    if _anki_connect_is_available(anki_client):
        return

    # ponytail: macOS only (`open -a Anki`); add other launchers if sync runs elsewhere.
    print("AnkiConnect unavailable, launching Anki")
    try:
        subprocess.Popen(
            ["open", "-a", "Anki"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(f"Could not launch Anki: {exc}") from exc

    deadline = time.monotonic() + startup_timeout_seconds
    while time.monotonic() < deadline:
        if _anki_connect_is_available(anki_client):
            return
        time.sleep(ANKI_CONNECT_POLL_INTERVAL_SECONDS)

    raise RuntimeError(
        f"Anki launched but AnkiConnect did not become reachable within "
        f"{startup_timeout_seconds:g}s"
    )


def _anki_connect_is_available(anki_client: AnkiConnectClient) -> bool:
    try:
        anki_client.get_version()
    except (AnkiConnectTransportError, AnkiConnectTimeoutError):
        return False
    return True


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
        startup_timeout_seconds=settings.anki_desktop_startup_timeout_seconds,
    )

    try:
        summary = sync_pending_cards(
            backend_client=backend_client,
            anki_client=anki_client,
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
