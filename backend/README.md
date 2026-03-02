# anki-vocab-bot backend

This package contains the FastAPI app, Telegram bot runtime, persistence layer,
and sync helpers for the anki-vocab-bot monorepo.

Useful local commands:
- `uv run uvicorn app.main:app --reload` for API development.
- `uv run python -m app.scripts.run_telegram_bot` for Telegram long polling.
