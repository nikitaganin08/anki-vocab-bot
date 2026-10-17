from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.card import Card

DRY_RUN_PREVIEW = 30


def backfill_transcription(
    session: Session,
    client: OpenRouterClient,
    *,
    limit: int | None = None,
    batch_size: int = 20,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Returns (updated, unchanged, failed); only cards.transcription is written."""
    cards = session.scalars(select(Card).order_by(Card.id).limit(limit)).all()
    updated = unchanged = failed = shown = 0
    for start in range(0, len(cards), batch_size):
        batch = cards[start : start + batch_size]
        try:
            result = client.generate_transcriptions([(c.id, c.canonical_text) for c in batch])
        except OpenRouterError as exc:
            session.rollback()
            print(f"batch {start // batch_size + 1} failed: {exc.user_message}")
            failed += len(batch)
            continue
        batch_updated = batch_unchanged = batch_failed = 0
        for card in batch:
            new = result.get(card.id)
            if new is None:
                batch_failed += 1
            elif new == card.transcription:
                batch_unchanged += 1
            else:
                if dry_run and shown < DRY_RUN_PREVIEW:
                    print(f"{card.canonical_text}: {card.transcription} -> {new}")
                    shown += 1
                if not dry_run:
                    card.transcription = new
                batch_updated += 1
        if not dry_run:
            session.commit()
        print(
            f"batch {start // batch_size + 1}: updated={batch_updated}, "
            f"unchanged={batch_unchanged}, failed={batch_failed}"
        )
        updated += batch_updated
        unchanged += batch_unchanged
        failed += batch_failed
    return updated, unchanged, failed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite card transcriptions as General American IPA."
    )
    parser.add_argument("--limit", type=int, default=None, help="Max cards to handle.")
    parser.add_argument("--batch-size", type=int, default=20, help="Cards per LLM request.")
    parser.add_argument("--dry-run", action="store_true", help="Print old -> new, write nothing.")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required to run backfill_transcription")

    client = OpenRouterClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
    with SessionLocal() as session:
        updated, unchanged, failed = backfill_transcription(
            session, client, limit=args.limit, batch_size=args.batch_size, dry_run=args.dry_run
        )
    mode = "dry run" if args.dry_run else "complete"
    print(
        f"backfill_transcription {mode}: updated={updated}, unchanged={unchanged}, failed={failed}"
    )


if __name__ == "__main__":
    main()
