# anki-vocab-bot backend

This package contains the FastAPI app, Telegram bot runtime, persistence layer,
and sync helpers for the anki-vocab-bot monorepo.

Useful local commands:
- `uv run uvicorn app.main:app --reload` for API development.
- `uv run python -m app.scripts.run_telegram_bot` for Telegram long polling.
- `uv run python -m app.scripts.sync_anki --limit 50` for one sync pass.

## Sync helper

`app.scripts.sync_anki` pulls pending cards from backend API and pushes them to
AnkiConnect.

Required environment variables for sync:
- `ANKI_SYNC_TOKEN`
- `BACKEND_API_BASE_URL` (default: `http://127.0.0.1:8000`)
- `ANKI_CONNECT_URL` (default: `http://127.0.0.1:8765`)
- `ANKI_SYNC_BATCH_LIMIT` (default: `50`)
- `ANKI_SYNC_HTTP_TIMEOUT_SECONDS` (default: `15`)

Idempotency policy:
- each card is tagged in Anki as `avb-card-<card_id>`
- sync checks `findNotes` by tag before creating a note
- if found, sync acknowledges the existing note id instead of creating duplicate

## Docker

From repository root:
- `docker build -t anki-vocab-bot:local .`
- `docker compose up --build`

Smoke check when container is running:
- `curl --fail --silent http://127.0.0.1:8000/api/health`
