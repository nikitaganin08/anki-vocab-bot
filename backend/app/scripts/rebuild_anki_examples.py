from __future__ import annotations

import argparse

from app.clients.anki_connect import AnkiConnectClient, AnkiConnectError
from app.clients.backend_sync_api import BackendSyncApiClient, BackendSyncApiError
from app.core.config import get_settings
from app.scripts.sync_anki import ensure_anki_connect_available
from app.services.anki_word_family import rebuild_anki_examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update existing Anki notes with word-family data in the Example field."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of eligible backend cards to inspect in one run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of backend cards to fetch per request (default: 50).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Find matching Anki notes without changing them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be greater than zero")
    if args.batch_size < 1 or args.batch_size > 200:
        raise SystemExit("--batch-size must be between 1 and 200")

    settings = get_settings()
    if not settings.anki_sync_token:
        raise SystemExit("ANKI_SYNC_TOKEN is required to rebuild Anki examples")

    backend_client = BackendSyncApiClient(
        base_url=settings.backend_api_base_url,
        token=settings.anki_sync_token,
        timeout_seconds=settings.anki_sync_http_timeout_seconds,
    )
    anki_client = AnkiConnectClient(
        endpoint=settings.anki_connect_url,
        timeout_seconds=settings.anki_sync_http_timeout_seconds,
    )

    try:
        ensure_anki_connect_available(
            anki_client=anki_client,
            startup_timeout_seconds=settings.anki_desktop_startup_timeout_seconds,
        )
        summary = rebuild_anki_examples(
            backend_client=backend_client,
            anki_client=anki_client,
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    except (BackendSyncApiError, AnkiConnectError, RuntimeError) as exc:
        raise SystemExit(f"rebuild-anki-examples failed: {exc}") from exc

    mode = "dry-run" if args.dry_run else "complete"
    print(
        f"rebuild-anki-examples {mode}: "
        f"total={summary.total}, updated={summary.updated}, "
        f"skipped={summary.skipped}, failed={summary.failed}"
    )
    for failure in summary.failures:
        print(f"FAILED: {failure}")


if __name__ == "__main__":
    main()
