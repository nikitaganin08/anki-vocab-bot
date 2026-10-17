# anki-vocab-bot backend

This package contains the FastAPI app, Telegram bot runtime, persistence layer,
and sync helpers for the anki-vocab-bot monorepo.

Useful local commands:
- `uv run uvicorn app.main:app --reload` for API development.
- `uv run python -m app.scripts.sync_anki --limit 50` for one sync pass.
- `uv run python -m app.scripts.backfill_chunks --limit 50` (or `make backfill-chunks`) asks
  the LLM for usage chunks + one example for saved cards without chunks. One-off; on prod:
  `docker compose exec app python -m app.scripts.backfill_chunks --limit 500`.
- `uv run python -m app.scripts.import_anki [--dry-run]` (or `make import-anki`) imports the
  `English::Inbox` deck with approximate FSRS state (see "Anki import" below). One-off.

Review (SRS):
- FSRS scheduling (`fsrs` package) runs server-side; state lives on `cards.srs_*`, every answer
  is appended to `review_logs`, user preferences are the single `app_settings` row.
- Mini App endpoints (Telegram Web App auth): `/api/review/*`, `/api/settings`,
  `PATCH /api/cards/{id}` (`is_learning` toggle).
- The day starts at 04:00 in `app_settings.timezone` (default `Europe/Moscow`).
- A daily reminder loop runs in the FastAPI lifespan when `TELEGRAM_BOT_TOKEN` is set; set
  `DISABLE_REMINDERS=1` to turn it off (tests do).
- Bot command `/review` opens the review view; rare words (`frequency < learn_threshold`) are
  saved as not learning and the bot asks "Учить?" with inline buttons.

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

Optional local desktop launch variables:
- `ANKI_DESKTOP_STARTUP_TIMEOUT_SECONDS` (default: `20`)

Idempotency policy:
- each card is tagged in Anki as `avb-card-<card_id>`
- sync checks `findNotes` by tag before creating a note
- if found, sync acknowledges the existing note id instead of creating duplicate
- pronunciation audio is generated locally during sync and uploaded to Anki media as
  `avb-pronunciation-<card_id>.mp3`

## Anki import

`app.scripts.import_anki` reads the `English::Inbox` deck through AnkiConnect (same env vars
as sync) and posts each note to `POST /api/anki/import` (bearer `ANKI_SYNC_TOKEN`). The backend
links the note to a card by its `avb-card-<id>` tag or canonical text, or creates the card via
the LLM pipeline, then sets an approximate FSRS state (review cards: stability = interval,
difficulty from ease, due = last review + interval) and marks it `synced`, so `sync_anki` does
not push it back. Suspended notes are imported as not learning. Run `--dry-run` first: it only
counts tagged/untagged/suspended notes.

## Docker

From repository root:
- `docker build -t anki-vocab-bot:local .`
- `docker compose up --build` (needs the external `edge` network: `docker network create edge`)
