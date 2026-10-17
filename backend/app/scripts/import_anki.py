from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app.clients.anki_connect import AnkiConnectClient, AnkiConnectError
from app.clients.backend_sync_api import BackendSyncApiClient, BackendSyncApiError
from app.core.config import get_settings
from app.scripts.sync_anki import ensure_anki_connect_available
from app.services.anki_sync import ANKI_DECK_NAME, CARD_TAG_PREFIX

# The backend calls the LLM for notes it does not know yet, which is slower than a sync call.
IMPORT_HTTP_TIMEOUT_SECONDS = 120.0
ANKI_SUSPENDED_QUEUE = -1
TAG_PREFIX = f"{CARD_TAG_PREFIX}-"


def _backend_card_id(tags: list[str]) -> int | None:
    for tag in tags:
        if tag.startswith(TAG_PREFIX) and tag.removeprefix(TAG_PREFIX).isdigit():
            return int(tag.removeprefix(TAG_PREFIX))
    return None


def collect_import_items(anki_client: AnkiConnectClient) -> list[dict[str, Any]]:
    notes = anki_client.notes_info(anki_client.find_notes(f'deck:"{ANKI_DECK_NAME}"'))
    card_ids = [note["cards"][0] for note in notes]
    cards = {info["cardId"]: info for info in anki_client.cards_info(card_ids)}
    reviews = anki_client.reviews_of_cards(card_ids)

    items = []
    for note, card_id in zip(notes, card_ids, strict=True):
        card = cards[card_id]
        review_ids = [review["id"] for review in reviews.get(str(card_id), [])]
        last_review_at = (
            datetime.fromtimestamp(max(review_ids) / 1000, UTC).isoformat() if review_ids else None
        )
        items.append(
            {
                "word": note["fields"]["Word"]["value"],
                "translation": note["fields"]["Translation"]["value"],
                "anki_note_id": note["noteId"],
                "backend_card_id": _backend_card_id(note["tags"]),
                "suspended": card["queue"] == ANKI_SUSPENDED_QUEUE,
                "card_type": card["type"],
                "interval_days": card["interval"],
                "ease": card["factor"] / 1000,
                "last_review_at": last_review_at,
                "reps": card["reps"],
                "lapses": card["lapses"],
            }
        )
    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the Anki deck with approximate FSRS state."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Read Anki only; do not call the backend."
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.anki_sync_token:
        raise SystemExit("ANKI_SYNC_TOKEN is required to run import_anki")

    anki_client = AnkiConnectClient(
        endpoint=settings.anki_connect_url,
        timeout_seconds=settings.anki_sync_http_timeout_seconds,
    )
    ensure_anki_connect_available(
        anki_client=anki_client,
        startup_timeout_seconds=settings.anki_desktop_startup_timeout_seconds,
    )
    try:
        items = collect_import_items(anki_client)
    except AnkiConnectError as exc:
        raise SystemExit(f"import_anki failed: {exc}") from exc

    if args.dry_run:
        tagged = sum(item["backend_card_id"] is not None for item in items)
        suspended = sum(item["suspended"] for item in items)
        print(
            f"import_anki dry run: notes={len(items)}, tagged={tagged}, "
            f"untagged={len(items) - tagged}, suspended={suspended}"
        )
        return

    backend_client = BackendSyncApiClient(
        base_url=settings.backend_api_base_url,
        token=settings.anki_sync_token,
        timeout_seconds=IMPORT_HTTP_TIMEOUT_SECONDS,
    )
    counts: Counter[str] = Counter()
    for item in items:
        try:
            status = backend_client.import_note(item)["status"]
        except BackendSyncApiError as exc:
            status = "error"
            print(f"note={item['anki_note_id']} failed: {exc}")
        counts[status] += 1
    summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    print(f"import_anki complete: total={len(items)}, {summary}")


if __name__ == "__main__":
    main()
