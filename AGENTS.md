# anki-vocab-bot

## Project Overview

This repository contains a personal vocabulary assistant built as a monorepo with:
- a Python backend
- a React Telegram Web App frontend

The app receives words and stable expressions from Telegram, generates learning cards with an LLM, stores them in a local database, schedules them for FSRS review in the Telegram Mini App, sends one daily review reminder, and queues learning cards for optional sync into Anki.

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
- Telegram Web App (Mini App) with a review dashboard, the daily review flow, settings, and the card list (import, filter, delete, toggle learning)
- FSRS review of learning cards with typed answers and usage chunks
- Daily review reminder from the bot
- Local sync helper for Anki via AnkiConnect, plus one-off Anki deck import and chunk backfill scripts

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
- `fsrs` (py-fsrs) for spaced-repetition scheduling
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
- `TanStack Query`
- No router: views are switched by the `?view=` query parameter
- Theme follows Telegram: `Telegram.WebApp.themeParams` are mapped to CSS variables (`--tg-bg`, `--tg-text`, `--tg-hint`, `--tg-accent`, `--tg-accent-text`, `--tg-surface`) with light fallbacks; flat surfaces, no gradients, one accent button per screen
- Audio: browser `speechSynthesis` (`en-US`), hidden when unavailable
- `npm` for dependency management
- `npx` only for one-off scaffolding and CLI bootstrap commands

### Deployment

- Backend and frontend live in one repository
- Frontend is built into static assets and served by the backend under `/telegram/webapp/*`
- Production deploy is triggered by GitHub Actions on push to `master`
- The deploy workflow lives in `.github/workflows/deploy.yml`
- GitHub Actions builds and pushes the Docker image, then deploys it on the VPS over SSH
- Edge nginx (domain, TLS, other sites) lives outside this repository in `/opt/nginx` on the VPS;
  this repo owns only its `/anki/` routes in `deploy/nginx/anki.conf`, which the deploy workflow
  copies to `/opt/nginx/snippets/anki.conf` and applies with `nginx -t` + reload (restoring the
  previous file if the test fails)
- In production, admin access is expected through Telegram Web App auth tied to the allowed Telegram user
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
14. Cards with `frequency >= learn_threshold` (`app_settings`, default 3) are stored with `is_learning = true`; rarer cards are stored with `is_learning = false` and the bot asks "Учить?" with inline `learn:<id>` / `skip:<id>` buttons (also on a duplicate of a not-learning card).
15. Learning cards enter the FSRS review queue in the Mini App; a local sync helper also pulls pending learning cards from the backend and sends them to AnkiConnect.

## Review (SRS)

- Server-side scheduling with `fsrs.Scheduler(desired_retention=app_settings.desired_retention, enable_fuzzing=False)`, default learning steps (1m, 10m) and relearning step (10m).
- SRS state lives on `cards` (`srs_card_json` = `fsrs.Card.to_json()`, `srs_due_at`, `srs_state`, `srs_reps`, `srs_lapses`); every graded answer is appended to `review_logs` (with the card state before, for undo). Intro screens of new cards are not logged.
- All datetimes are UTC; values read from SQLite are naive and go through `as_utc()`.
- The day starts at 04:00 in `app_settings.timezone` (default `Europe/Moscow`); daily limits (`new_per_day` 5, `reviews_per_day` 50) are counted per that window. Due reviews beyond the limit are reported as `backlog`.
- Session order: due learning/relearning cards, then due reviews by retrievability (highest first), then new learning cards (intro first, typed later).
- Prompt: a usage chunk with its `target` masked as `___` plus the chunk translation, rotating chunks per review; cards without chunks prompt with the Russian translations and expect `canonical_text`.
- Answer checking (`app/services/answer_check.py`): NFKC, casefold, curly apostrophes, trailing punctuation, ЙЦУКЕН→QWERTY layout fix; one Damerau-Levenshtein edit when the expected answer has 5+ chars is a `typo` (counts as correct).
- Auto rating: wrong → Again (1); correct/typo with hint → Hard (2); correct/typo → Good (3). Easy (4) only by user choice.
- A grade carries the `srs_due_at` the client saw; a mismatch (e.g. double tap) returns 409 and logs nothing.

## Reminders

- `app/services/reminders.py` runs a loop every 5 minutes in the FastAPI lifespan (only when `TELEGRAM_BOT_TOKEN` is set and `DISABLE_REMINDERS` is not `1`; single uvicorn worker assumed).
- One message a day at `reminder_hour` local time when nothing was reviewed today and cards are due; never mentions streaks, no evening reminder.
- Backoff: after 3 ignored reminders only every other day, after 7 paused until the next review; any review resets the counter.
- Short rotating Russian templates with card count and minutes, optional `reminder_anchor` prefix, no warm-up chunk; Mondays add last week's summary. Inline button "Повторить" opens the Mini App at `?view=review`.

## LLM Contract

The backend expects a structured JSON response from OpenRouter.
The backend stores the original request as `source_text` and the configured client model as
`llm_model`; the LLM does not echo either field.

Accepted result:
- `accepted = true`
- `source_language`
- `entry_type`
- `canonical_text`
- `transcription`
- `translation_variants`
- `explanation`
- `examples`
- `chunks`
- `word_family`
- `frequency`
- `frequency_note`

Rejected result:
- `accepted = false`
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
- `examples` must contain 1 to 3 items (the prompt asks for exactly 1; older cards keep 3)
- `chunks` must contain 0 to 5 frequent usage chunks `{text, target, translation}`:
  - `text` is English, 2 to 6 words
  - `target` is the substring of `text` that realises `canonical_text` (case-insensitive, may be inflected)
  - `translation` is Russian
  - `[]` when the unit has no frequent chunks
- for multi-token canonical text, the first example or at least one chunk must reference it
- `word_family` has at most 3 items
- `frequency` must be in range `0..10`
- the prompt tells the LLM to reject function words on their own (articles, pronouns, auxiliaries, prepositions, conjunctions)

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
- `is_learning` (drives both the review queue and Anki sync; renamed from `eligible_for_anki`)
- `anki_sync_status` (`pending`, `synced`, `failed`)
- `anki_note_id`
- `anki_sync_error` (last sync failure, cleared on ack)
- `word_family_json`
- `chunks_json` (list of `{text, target, translation}`, default `[]`)
- `srs_card_json` (`fsrs.Card.to_json()`; null = never scheduled)
- `srs_due_at` (indexed copy of the FSRS due time)
- `srs_state` (`learning`, `review`, `relearning`; null = new)
- `srs_reps`
- `srs_lapses`
- `llm_model`
- `created_at`
- `updated_at`

### `review_logs`

- `id`
- `card_id` (FK `cards.id`, cascade delete)
- `reviewed_at`
- `rating` (1-4)
- `auto_rating`
- `overridden`
- `prompt_kind` (`chunk`, `translation`)
- `prompt_index`
- `typed_answer`
- `verdict` (`correct`, `typo`, `wrong`, `skipped`)
- `hint_used`
- `response_ms`
- `retrievability`
- `card_before_json` (for undo)
- `state_before`

### `app_settings` (single row, `id = 1`)

- `timezone` (default `Europe/Moscow`)
- `reminder_hour` (default `10`)
- `reminder_anchor` (optional text, e.g. "после кофе")
- `new_per_day` (default `5`)
- `reviews_per_day` (default `50`)
- `desired_retention` (default `0.9`)
- `learn_threshold` (default `3`)
- `last_reminder_on`
- `ignored_reminders`

## Backend API

### Public JSON API

- `GET /api/health`

### Web App API (Telegram Web App auth)

- `GET /api/cards` (filters include `is_learning`)
- `POST /api/cards/batch`
- `PATCH /api/cards/{card_id}` (`{is_learning}`)
- `DELETE /api/cards/{card_id}`
- `GET /api/review/summary` (today goal, backlog, `due_all`, `days_away`, retention 30d, learned, streak, heatmap, forecast)
- `GET /api/review/session?size=10&include_backlog=false` (next round; the expected answer is not sent, only `first_letter_hint`; `include_backlog=true` ignores the daily review cap)
- `POST /api/review/{card_id}/check` (verdict, expected answer, auto rating, intervals; no DB write)
- `POST /api/review/{card_id}/grade` (409 on a stale `expected_due_at`)
- `POST /api/review/undo`
- `GET /api/settings`
- `PUT /api/settings`

### Telegram Webhook API

- `POST /telegram/webhook`

### Anki Sync API

- `GET /api/anki/pending?limit=50`
- `POST /api/anki/ack`
- `POST /api/anki/fail`
- `POST /api/anki/import` (one Anki note → linked/created card with approximate FSRS state)

The Anki sync API uses bearer token authentication.

## Telegram Web App

Views are switched by `?view=` (`history.replaceState`, other params and the hash kept); unknown or missing values open `home`. The bot's `/review` command and reminders open `?view=review`. Screen content and Russian copy follow the "Mini App" section of `docs/superpowers/specs/2026-10-17-srs-review-design.md`.

- Bottom tab bar (`src/components/TabBar.tsx`): Главная (`home`), Повтор (`review`), Слова (`cards`), Настройки (`settings`). Hidden during a review; the Telegram BackButton leaves the review to Главная.
- Главная (`src/home/`): today's goal with "Начать" and "Быстро: 5 карточек" (ends after 5 graded cards), retention and learned tiles, 14-week heatmap, streak line (only from 3 days), forecast, backlog. After 3+ study days away with cards due it shows "С возвращением" instead: "5 минут" (card cap from today's pace), "Обычная сессия", "Всё сразу (N)" (`include_backlog=true`).
- Повтор (`src/review/`): `useReviewSession` drives the flow in rounds of 10 (5 for «Быстро») from `GET /api/review/session`. New cards show an intro ("Запомнил"), and the typed question for that card comes two items later in the same round. Question → `check` → back side with the diff, card details and four grade buttons "Снова / Трудно / Хорошо / Легко" (auto rating highlighted; after a wrong answer "Мой ответ верный" forces Good) → `grade`. `grade` echoes `srs_due_at` verbatim as `expected_due_at`; a 409 refetches the round. After each round: "Раунд готов" with progress to the daily goal; an empty session shows "Готово на сегодня".
- Настройки (`src/settings/`): daily limits, desired retention, reminder hour and anchor, learn threshold, timezone; saved with `PUT /api/settings`.
- Слова (`src/pages/CardsPage.tsx`): cards list with search and filters (including `is_learning`), batch import, deletion, and a per-card "Учим" toggle (`PATCH /api/cards/{card_id}`).

The UI reads only from backend JSON endpoints.

Production exposure (`deploy/nginx/anki.conf`):
- `/anki/telegram/*` → Mini App static files and the webhook (secret token)
- `/anki/api/*` → every backend API route; each authenticates itself (Telegram Web App init data
  or the bearer token), except the health check
- other backend paths (e.g. FastAPI docs) are not exposed

## Anki Integration

- Deck: `English::Inbox`
- Note type: `VocabularyCard`
- Fields:
  - `Word`
  - `Transcription`
  - `PronunciationAudio`
  - `Translation`
  - `Explanation`
  - `Example`

Mapping:
- `Word` -> `canonical_text_normalized` (lowercased, whitespace-collapsed `canonical_text`)
- `Transcription` -> `transcription`
- `PronunciationAudio` -> `[sound:avb-pronunciation-<card_id>.mp3]` generated locally during `sync_anki`
- `Translation` -> comma-joined translations
- `Explanation` -> `explanation`
- `Example` -> chunk lines (`text — translation`), blank line, first English example, then the word family block

Deck import (`app/scripts/import_anki.py`, one-off): notes of `English::Inbox` are posted to `POST /api/anki/import`; tagged notes link to their card, others are matched by canonical text or created via the LLM pipeline. Review cards get stability = interval, difficulty from ease, due = last review + interval; suspended notes are not learning; imported cards are marked `synced` so `sync_anki` does not push them again.

## Configuration

Required environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_ID`
- `TELEGRAM_WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_WEBAPP_URL`
- `OPENROUTER_API_KEY`
- `ANKI_SYNC_TOKEN`
- `ANKI_PRONUNCIATION_VOICE` (default: `en-US-EmmaNeural`)
- `DATABASE_URL` (default: `sqlite:///backend/data/app.db`)
- `LLM_MODEL` (default: `google/gemini-2.5-flash-lite`)

Optional:
- `DISABLE_REMINDERS=1` turns off the reminder loop (set in tests)

Review preferences (timezone, reminder hour, limits, retention, learn threshold) live in `app_settings`, edited via `PUT /api/settings`.

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
- `make import-anki` (one-off Anki deck import)
- `make backfill-chunks` (one-off chunk backfill for existing cards)

## Testing Scope

Required in the first implementation:
- backend unit tests
- frontend component tests

Focus areas:
- acceptance/rejection of lexical units
- deduplication by source text and canonical form
- card persistence
- Anki queue status transitions
- answer checking (layout, typos, inflected chunk targets)
- FSRS scheduling, session queue limits and the 04:00 day boundary, grade/undo
- review summary metrics and reminder decisions
- rare-word confirmation and Anki import state mapping
- Telegram Web App rendering of API data and the review flow (intro → typed, check → grade, 409 refetch)

## Defaults and Constraints

- Single-user only in the first version
- Telegram runs in webhook mode
- Rate limit: no more than 5 requests per minute from the allowed user
- Review defaults: 5 new / 50 reviews per day, desired retention 0.9, learn threshold 3, reminder at 10:00, day starts at 04:00 local
- Default LLM model: `google/gemini-2.5-flash-lite`
- Cards are rejected when the model is not confident the input is a stable lexical unit
- Backend is the source of truth for all stored cards and sync state

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **Run quality gates** (if code changed) - Tests, linters, builds
2. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
3. **Clean up** - Clear stashes, prune remote branches
4. **Verify** - All changes committed AND pushed
5. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
