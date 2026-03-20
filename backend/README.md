# anki-vocab-bot backend

This package contains the FastAPI app, Telegram bot runtime, persistence layer,
and sync helpers for the anki-vocab-bot monorepo.

Useful local commands:
- `uv run uvicorn app.main:app --reload` for API development.
- `uv run python -m app.scripts.sync_anki --limit 50` for one sync pass.

Webhook mode:
- Telegram delivers updates to `POST /telegram/webhook`.
- Required webhook env vars: `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`.
- Telegram admin panel is served as a Web App under `/telegram/webapp`.
- Required runtime env var for the Web App launcher: `TELEGRAM_WEBAPP_URL`.
- Bot command `/find <description>` asks the LLM for 3 to 5 likely English lexical units
  from a clue and returns them without creating a card.

## Sync helper

`app.scripts.sync_anki` pulls pending cards from backend API and pushes them to
AnkiConnect. If AnkiConnect is unavailable, the script tries to launch the Anki
desktop app locally first and waits for AnkiConnect to come up.

Required environment variables for sync:
- `ANKI_SYNC_TOKEN`
- `BACKEND_API_BASE_URL` (default: `http://127.0.0.1:8000`)
- `ANKI_CONNECT_URL` (default: `http://127.0.0.1:8765`)
- `ANKI_SYNC_BATCH_LIMIT` (default: `50`)
- `ANKI_SYNC_HTTP_TIMEOUT_SECONDS` (default: `15`)
- `ANKI_PRONUNCIATION_VOICE` (default: `en-US-EmmaNeural`)
- `ANKI_PRONUNCIATION_FORMAT` (default: `mp3`)

Optional local desktop launch variables:
- `ANKI_DESKTOP_STARTUP_TIMEOUT_SECONDS` (default: `20`)

Idempotency policy:
- each card is tagged in Anki as `avb-card-<card_id>`
- sync checks `findNotes` by tag before creating a note
- if found, sync acknowledges the existing note id instead of creating duplicate
- pronunciation audio is generated locally during sync and uploaded to Anki media as
  `avb-pronunciation-<card_id>.mp3`

## Docker

From repository root:
- `docker build -t anki-vocab-bot:local .`
- `docker compose up --build`

Smoke check when container is running:
- `curl --fail --silent http://127.0.0.1/api/health`
