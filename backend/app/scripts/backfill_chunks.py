from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.card import Card


def backfill_chunks(session: Session, client: OpenRouterClient, *, limit: int) -> tuple[int, int]:
    # ponytail: one-off; cards the LLM leaves with [] chunks are picked again on the next run.
    cards = session.scalars(
        select(Card).where(Card.chunks_json == []).order_by(Card.created_at, Card.id).limit(limit)
    ).all()
    updated = failed = 0
    for card in cards:
        try:
            result = client.generate_chunks(
                card.canonical_text, card.translation_variants_json, card.examples_json
            )
        except OpenRouterError as exc:
            session.rollback()
            print(f"card={card.id} failed: {exc.user_message}")
            failed += 1
            continue
        card.chunks_json = [chunk.model_dump() for chunk in result.chunks]
        card.examples_json = [result.example]
        session.commit()
        print(f"card={card.id} updated: {len(card.chunks_json)} chunks")
        updated += 1
    return updated, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill usage chunks for saved cards.")
    parser.add_argument("--limit", type=int, default=50, help="Max cards to handle in one run.")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required to run backfill_chunks")

    client = OpenRouterClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
    with SessionLocal() as session:
        updated, failed = backfill_chunks(session, client, limit=args.limit)
    print(f"backfill_chunks complete: updated={updated}, failed={failed}")


if __name__ == "__main__":
    main()
