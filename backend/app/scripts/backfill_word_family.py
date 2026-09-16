from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.card import Card


@dataclass(slots=True)
class BackfillSummary:
    selected: int = 0
    updated: int = 0
    failed: int = 0


def backfill_cards(
    session: Session,
    openrouter_client: OpenRouterClient,
    *,
    limit: int,
) -> BackfillSummary:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    cards = session.scalars(
        select(Card)
        .where(Card.word_family_backfilled.is_(False))
        .order_by(Card.id)
        .limit(limit)
    ).all()
    summary = BackfillSummary(selected=len(cards))

    for card in cards:
        try:
            if not card.word_family_json:
                word_family = openrouter_client.generate_word_family(
                    card.canonical_text,
                    explanation=card.explanation,
                    translation_variants=card.translation_variants_json,
                )
                card.word_family_json = [item.model_dump() for item in word_family]
            card.word_family_backfilled = True
            session.commit()
        except OpenRouterError as exc:
            session.rollback()
            print(f"card={card.id} failed: {exc.user_message}")
            summary.failed += 1
            continue

        print(f"card={card.id} updated: {len(card.word_family_json)} forms")
        summary.updated += 1

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill word-family forms for saved cards.")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max number of unprocessed cards to handle in one run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required to run backfill-word-family")
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero")

    client = OpenRouterClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
    with SessionLocal() as session:
        summary = backfill_cards(session, client, limit=args.limit)

    print(
        "backfill-word-family complete: "
        f"selected={summary.selected}, updated={summary.updated}, failed={summary.failed}"
    )


if __name__ == "__main__":
    main()
