# anki-vocab-bot

## Project Overview

This repository contains a personal vocabulary assistant built as a monorepo with:
- a Python backend
- a React admin frontend

The app receives words and stable expressions from Telegram, generates learning cards with an LLM, stores them in a local database, exposes a JSON API for inspection, and queues eligible cards for later sync into Anki.

## Product Scope

- Single-user Telegram bot
- Accepts:
  - single words
  - phrasal verbs
  - collocations
  - idioms
  - short stable expressions
- Source input languages: Russian (`ru`) and English (`en`)
- Input length limit: 1 to 8 tokens
- The resulting card always targets an English lexical unit
- The LLM decides whether the input is a valid lexical unit or just a free-form phrase/sentence
- Read-only admin UI for browsing cards
- Local sync helper for Anki via AnkiConnect

## Architecture

### Monorepo Layout

- `backend/`
- `frontend/`

### Backend

- Python `3.12`
- `FastAPI`
- `aiogram`
- `Pydantic v2`
- `SQLAlchemy 2`
- `Alembic`
- `httpx`
- `SQLite` storage
- `uv` for dependency management and runtime commands
- Backend package layout:
  - `app/bot/` for Telegram bot runtime, handlers, formatter, and rate limiting
  - `app/core/` for settings and shared runtime config
  - `app/db/` for SQLAlchemy base and session setup
  - `app/models/` for ORM entities
  - `app/schemas/` for LLM contract validation
  - `app/clients/` for external integrations such as OpenRouter
  - `app/services/` for prompts and domain workflows
  - `app/scripts/` for local helper entrypoints

### Frontend

- `React 18`
- `TypeScript`
- `Vite`
- `React Router`
- `TanStack Query`
- `npm` for dependency management
- `npx` only for one-off scaffolding and CLI bootstrap commands

### Deployment

- Backend and frontend live in one repository
- Frontend is built into static assets and served by the backend under `/admin/*`
- Docker uses a multi-stage build:
  - frontend build stage
  - backend dependency stage
  - runtime stage
- Persistent app data lives in `backend/data/app.db`

## Core Workflow

1. Telegram bot receives a text message from the allowed user.
2. Backend normalizes whitespace and validates the input length.
3. If the input has more than 8 tokens, the request is rejected before the LLM call.
4. The backend checks whether the same `source_text` already exists.
5. If a source-text duplicate is found, the backend returns the existing card and marks it as already in the dictionary.
6. If there is no source-text duplicate, the backend sends the input to OpenRouter.
7. The LLM either:
   - accepts the input as a valid lexical unit and returns a structured card
   - rejects the input as not being a stable expression
8. Rejected inputs are not stored.
9. Accepted inputs are normalized to a canonical English form.
10. The backend checks duplicates by `canonical_text_normalized`.
11. If a canonical duplicate is found, the backend returns the existing card and marks it as already in the dictionary.
12. Otherwise, the backend stores the card in SQLite.
13. The backend renders and sends the Telegram response from stored structured fields.
14. Cards with `frequency > 2` are marked as eligible for Anki sync.
15. A local sync helper pulls pending cards from the backend and sends them to AnkiConnect.

## LLM Contract

The backend expects a structured JSON response from OpenRouter.

Accepted result:
- `accepted = true`
- `source_text`
- `source_language`
- `entry_type`
- `canonical_text`
- `canonical_text_normalized`
- `transcription`
- `translation_variants`
- `explanation`
- `examples`
- `frequency`
- `frequency_note`
- `llm_model`

Rejected result:
- `accepted = false`
- `reason`
- `message_for_user`

Validation rules:
- `source_language` must be one of:
  - `ru`
  - `en`
- `entry_type` must be one of:
  - `word`
  - `phrasal_verb`
  - `collocation`
  - `idiom`
  - `expression`
- `canonical_text` must be English
- `explanation` must be English
- `examples` must be English
- `translation_variants` must contain 2 to 3 Russian translations
- `examples` must contain exactly 3 items
- `frequency` must be in range `0..10`

## Data Model

### `cards`

- `id`
- `source_text`
- `source_language`
- `entry_type`
- `canonical_text`
- `canonical_text_normalized` (unique)
- `transcription`
- `translation_variants_json`
- `explanation`
- `examples_json`
- `frequency`
- `frequency_note`
- `eligible_for_anki`
- `anki_sync_status` (`pending`, `synced`, `failed`)
- `anki_note_id`
- `llm_model`
- `created_at`
- `updated_at`

### `anki_sync_attempts`

- `id`
- `card_id`
- `status`
- `error_message`
- `created_at`

## Backend API

### Public JSON API

- `GET /api/health`
- `GET /api/cards`
- `GET /api/cards/{card_id}`
- `GET /api/stats`

### Telegram Webhook API

- `POST /telegram/webhook`

### Anki Sync API

- `GET /api/anki/pending?limit=50`
- `POST /api/anki/ack`
- `POST /api/anki/fail`

The Anki sync API uses bearer token authentication.

## Admin UI

The React frontend is read-only and includes:
- dashboard with counters
- cards list with search and filters
- card detail page

The UI reads only from backend JSON endpoints.

## Anki Integration

- Deck: `English::Inbox`
- Note type: `VocabularyCard`
- Fields:
  - `Word`
  - `Transcription`
  - `Translation`
  - `Explanation`
  - `Example`

Mapping:
- `Word` -> `canonical_text`
- `Transcription` -> `transcription`
- `Translation` -> comma-joined translations
- `Explanation` -> `explanation`
- `Example` -> first two English examples joined with a newline

## Configuration

Required environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_ID`
- `TELEGRAM_WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET`
- `OPENROUTER_API_KEY`
- `ANKI_SYNC_TOKEN`
- `DATABASE_URL` (default: `sqlite:///backend/data/app.db`)
- `LLM_MODEL` (default: `google/gemini-2.5-flash-lite`)

## Development Commands

### Backend

- Install deps: `uv sync`
- Run app: `uv run ...`
- Run tests: `uv run pytest`
- Lint: `uv run ruff check`
- Format: `uv run ruff format`

### Frontend

- Install deps: `npm install`
- Run dev server: `npm run dev`
- Build frontend: `npm run build`

### Root-level helpers

The repository should maintain a `Makefile` with at least:
- `make backend-dev`
- `make frontend-dev`
- `make test`
- `make build-frontend`
- `make sync-anki`

## Testing Scope

Required in the first implementation:
- backend unit tests
- frontend component tests

Focus areas:
- acceptance/rejection of lexical units
- deduplication by source text and canonical form
- card persistence
- Anki queue status transitions
- admin UI rendering of API data

## Defaults and Constraints

- Single-user only in the first version
- Telegram runs in webhook mode
- Rate limit: no more than 5 requests per minute from the allowed user
- Default LLM model: `google/gemini-2.5-flash-lite`
- Cards are rejected when the model is not confident the input is a stable lexical unit
- Backend is the source of truth for all stored cards and sync state

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
