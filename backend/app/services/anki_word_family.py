from __future__ import annotations

from dataclasses import dataclass, field

from app.clients.anki_connect import AnkiConnectClient, AnkiConnectError
from app.clients.backend_sync_api import BackendSyncApiClient, PendingCard
from app.services.anki_sync import build_card_tag, format_anki_example


@dataclass(slots=True)
class AnkiWordFamilySummary:
    total: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)


def rebuild_anki_examples(
    *,
    backend_client: BackendSyncApiClient,
    anki_client: AnkiConnectClient,
    limit: int | None = None,
    batch_size: int = 50,
    dry_run: bool = False,
) -> AnkiWordFamilySummary:
    summary = AnkiWordFamilySummary()
    offset = 0

    while limit is None or summary.total < limit:
        request_limit = batch_size
        if limit is not None:
            request_limit = min(request_limit, limit - summary.total)

        cards = backend_client.get_eligible(limit=request_limit, offset=offset)
        if not cards:
            break

        for card in cards:
            _process_card(card, anki_client, summary, dry_run=dry_run)

        summary.total += len(cards)
        offset += len(cards)

        if len(cards) < request_limit:
            break

    return summary


def _process_card(
    card: PendingCard,
    anki_client: AnkiConnectClient,
    summary: AnkiWordFamilySummary,
    *,
    dry_run: bool,
) -> None:
    try:
        note_ids = anki_client.find_notes_by_tag(build_card_tag(card.id))
        if not note_ids:
            summary.skipped += 1
            return

        if dry_run:
            summary.updated += 1
            return

        anki_client.update_note_fields(
            note_ids[0],
            {"Example": format_anki_example(card.examples, card.word_family)},
        )
        summary.updated += 1
    except AnkiConnectError as exc:
        summary.failed += 1
        summary.failures.append(f"card {card.id}: {exc.user_message}")
