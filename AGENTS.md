# anki-vocab-bot

## Project Overview

This repository contains a personal vocabulary assistant built as a monorepo with:
- a Python backend
- a React Telegram Web App frontend

The app receives words and stable expressions from Telegram, generates learning cards with an LLM, stores them in a local database, schedules them for FSRS review in the Telegram Mini App, and sends one daily review reminder.

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
- Telegram Web App (Mini App) with a review dashboard, the daily review flow, settings, and the word list (add words, search, filter, delete, toggle learning)
- FSRS review of learning cards with typed answers and usage chunks
- Daily review reminder from the bot
- The production migrations to the SRS model (chunks backfill, Anki deck import, General American IPA backfill) were run on 2026-10-17 and their scripts removed; the Anki integration itself (sync helper, `/api/anki/*`, `anki_*` card columns, sync token) was removed on 2026-10-18; see git history

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

### Frontend

- `React 18`
- `TypeScript`
- `Vite`
- `TanStack Query`
- No router: views are switched by the `?view=` query parameter
- Theme follows Telegram: `Telegram.WebApp.themeParams` are mapped to CSS variables (`--tg-bg`, `--tg-text`, `--tg-hint`, `--tg-accent`, `--tg-accent-text`, `--tg-surface`) with light fallbacks; flat surfaces, no gradients, one accent button per screen
- Audio: see "Pronunciation". The speaker plays only on tap (no autoplay, no prefetch); it shows when `GET /api/settings` reports `tts_enabled` or `window.speechSynthesis` exists, and is hidden otherwise
- UI copy is English, sentence case (`<html lang="en">`); Russian appears only as card data (translations, chunk translations)
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
15. Learning cards enter the FSRS review queue in the Mini App.

## Review (SRS)

- Server-side scheduling with `fsrs.Scheduler(desired_retention=app_settings.desired_retention, learning_steps=(1m, 1d), relearning_steps=(10m,), enable_fuzzing=False)`: a new card is Again 1m, Good 1 day, Easy 2 days.
- Easy vs Good (`_outcomes`, shared by preview and grade): for a new/learning card whose Good is ≥ 1 day away, Easy = 2 × Good; for review/relearning cards FSRS Easy is capped at 2 × Good; review outcomes keep Good ≥ Hard + 1 day, Easy ≥ Good + 1 day.
- Due dates of a day or more count from the start of their study day (local midnight); intraday learning steps keep their exact time.
- SRS state lives on `cards` (`srs_card_json` = `fsrs.Card.to_json()`, `srs_due_at`, `srs_state`, `srs_reps`, `srs_lapses`); every graded answer is appended to `review_logs` (with the card state before, for undo). Intro screens of new cards are not logged.
- All datetimes are UTC; values read from SQLite are naive and go through `as_utc()`.
- The day starts at midnight in `app_settings.timezone` (default `Europe/Moscow`, then follows the device, see Settings below); daily limits (`new_per_day` 5, `reviews_per_day` 50) are counted per that window. Due reviews beyond the limit are reported as `backlog`.
- Session order: due learning/relearning cards, then due reviews by retrievability (highest first), then new learning cards (intro first, typed later).
- Prompt: a usage chunk with its `target` masked as `___` plus the chunk translation, rotating chunks per review; cards without chunks prompt with the Russian translations and expect `canonical_text`.
- Answer checking (`app/services/answer_check.py`): NFKC, casefold, curly apostrophes, trailing punctuation, ЙЦУКЕН→QWERTY layout fix; one Damerau-Levenshtein edit when the expected answer has 5+ chars is a `typo` (counts as correct).
- Question screen: chunk prompts show the chunk translation plus the word's own translations; "What's this word?" reveals the card's English explanation and sets `hint_used`.
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
- `transcription` is General American (US) IPA wrapped in slashes, e.g. `/ˈhɔːnt/` (no square brackets, no syllable dots, stress marks included, US vowels and r-coloured vowels instead of the British ɒ, əʊ, ɪə, eə, ʊə); multi-word units are transcribed word by word inside one pair of slashes; `null` only when the model cannot produce one. The format is a prompt rule, not validated
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
- `is_learning` (drives the review queue)
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

- `timezone` (default `Europe/Moscow`; the Mini App replaces it with the device timezone)
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

- `GET /api/cards` (filters include `is_learning`; each card carries `srs_state` and `srs_due_at`, both null until its first review)
- `POST /api/cards/batch`
- `PATCH /api/cards/{card_id}` (`{is_learning}`)
- `DELETE /api/cards/{card_id}`
- `GET /api/review/summary` (today goal, backlog, `due_all`, `days_away`, retention 30d, learned, streak, heatmap, forecast)
- `GET /api/review/session?size=10&include_backlog=false` (next round; the expected answer is not sent; `include_backlog=true` ignores the daily review cap)
- `POST /api/review/{card_id}/check` (verdict, expected answer, auto rating, intervals; no DB write)
- `POST /api/review/{card_id}/grade` (409 on a stale `expected_due_at`)
- `POST /api/review/undo`
- `GET /api/cards/{card_id}/audio` (MP3 of `canonical_text`, see "Pronunciation")
- `GET /api/settings` (also read-only `tts_enabled`: `YANDEX_TTS_API_KEY` or `GOOGLE_TTS_API_KEY` is set)
- `PUT /api/settings` (`tts_enabled` is not required and is ignored)

### Telegram Webhook API

- `POST /telegram/webhook`

## Telegram Web App

Views are switched by `?view=` (`history.replaceState`, other params and the hash kept); unknown or missing values open `home`. The bot's `/review` command and reminders open `?view=review`. Screen content and the English UI copy follow the "Mini App" section of `docs/superpowers/specs/2026-10-17-srs-review-design.md`.

- Bottom tab bar (`src/components/TabBar.tsx`): Home (`home`), Review (`review`), Words (`cards`), Settings (`settings`). Hidden during a review; the Telegram BackButton leaves the review to Home.
- Home (`src/home/`): today's goal with "Start" and "Quick: 5 cards" (ends after 5 graded cards), retention and learned tiles, 14-week heatmap, streak line (only from 3 days), forecast, backlog. After 3+ study days away with cards due it shows "Welcome back" instead: "5 minutes" (card cap from today's pace), "Regular session", "All at once (N)" (`include_backlog=true`).
- Review (`src/review/`): `useReviewSession` drives the flow in rounds of 10 (5 for "Quick") from `GET /api/review/session`. New cards show an intro ("New word" chip, full card, "Got it"), and the typed question for that card comes two items later in the same round. Question → `check` → back side with the diff, the full card and four grade buttons "Again / Hard / Good / Easy" (auto rating highlighted; after a wrong answer "My answer was right" forces Good) → `grade`. `grade` echoes `srs_due_at` verbatim as `expected_due_at`; a 409 refetches the round. After each round: "Round complete" with progress to the daily goal; an empty session shows "Done for today".
- Full card (`CardDetails` in `src/review/IntroCard.tsx`, intro and back side): word + speaker + IPA → translations → explanation (full English definition) → "Usage" chunks → one example → word family, one form per line ("distinguishable (adjective) — различимый").
- Settings (`src/settings/`): daily limits, desired retention, reminder hour and anchor, learn threshold, timezone; saved with `PUT /api/settings`. On each Mini App load the shell saves the device timezone (`Intl.DateTimeFormat().resolvedOptions().timeZone`) when it differs from the stored one; a zone picked by hand in Settings is replaced on the next load if the device reports another.
- Words (`src/pages/CardsPage.tsx`, sheets in `AddWordsSheet.tsx` and `CardSheet.tsx`, shared `src/components/Sheet.tsx`): a search box (debounced) with a "+" button, filter chips "All" / "Learning" / "Not learning" (`is_learning`), then a compact row per card: status dot (blue new, amber learning/relearning, green review, grey not learning), word, primary translation and a right-hand label ("new", "today", "N d", "off"; the day follows the browser's local time). 50 cards per page with "Load more" (offset paging). `q` and `filter` live in the query string. "+" opens the "Add words" sheet (batch import, 5 words per request). A row tap opens a bottom sheet with the full card (`CardDetails`), a "Learning" switch (`PATCH /api/cards/{card_id}`), "Delete" (with a confirm dialog) and "Close"; Escape or a backdrop tap closes it and focus returns to the row.

The UI reads only from backend JSON endpoints.

Production exposure (`deploy/nginx/anki.conf`):
- `/anki/telegram/*` → Mini App static files and the webhook (secret token)
- `/anki/api/*` → every backend API route; each authenticates itself (Telegram Web App init data),
  except the health check
- other backend paths (e.g. FastAPI docs) are not exposed

## Pronunciation

- Two providers behind one interface (`app/services/pronunciation.py`: `TtsClient.synthesize(text) -> bytes`, `PronunciationAudioError` on any failure): `YandexTtsClient` (Yandex SpeechKit v1) and `GoogleTtsClient` (Google Cloud Text-to-Speech). Proxied by the backend: `GET /api/cards/{card_id}/audio` (Web App auth) synthesizes `canonical_text` per request and return `audio/mpeg` with `Cache-Control: private, max-age=31536000, immutable`. Nothing is stored on the server
- Provider selection (`get_tts_client` in `app/api/deps.py`): `YANDEX_TTS_API_KEY` set -> Yandex; else `GOOGLE_TTS_API_KEY` set -> Google; both set -> Yandex wins. `tts_enabled` is true when either key is set
- Inert until a key is set: 503 `Pronunciation is not configured`; unknown card 404; provider failure 502 (cause logged)
- Yandex request: `POST https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize`, header `Authorization: Api-Key <key>`, form fields `text`, `lang=en-US`, `voice` (default `john`, the only English voice), `format=mp3`; no `folderId` with a service-account API key; the response body is raw MP3. Not verified live yet: `lang=en-US` with `john` is documented only on the SpeechKit voices page
- Yandex setup: Yandex Cloud account, billing account, service account with role `ai.speechkit-tts.user`, an API key for it; put `YANDEX_TTS_API_KEY` in `/opt/anki-vocab-bot/.env`, then `docker compose up -d app`
- Mini App: the first tap per card fetches the MP3 once per page load (object URL kept in memory, double taps share the request) and plays it with `new Audio`; on any failure, or without the key, it falls back to `speechSynthesis` (`en-US`, an English voice when listed), else stays silent
- Cost: Yandex SpeechKit is about 1342 RUB per 1M characters including VAT (the whole 1.1k-word deck is about 20 RUB). Google Chirp 3 HD has a free tier of 1M characters per month (a word is ~10 characters); set a quota on the Text-to-Speech API in the GCP console so a bug cannot run up a bill

## Backups

- `deploy/backup/backup.sh` runs daily from the VPS user's cron (`17 4 * * *`): consistent SQLite online copy, `integrity_check`, gzip into `~/backups/wordloop/app-<timestamp>.db.gz`, 14 days kept (log: `backup.log` next to them). The deploy workflow keeps the scripts in `/opt/anki-vocab-bot/backup/`; the cron entry itself is installed once by hand.
- Restore: `/opt/anki-vocab-bot/backup/restore.sh ~/backups/wordloop/app-<timestamp>.db.gz` (checks the copy, stops the app, keeps the current database as `app.db.before-restore`, starts the app).
- `make pull-backups` copies the server's backups to `~/Backups/wordloop` on the dev machine (off-server copy; `BACKUP_HOST` overrides the ssh host).
- `.env` (tokens, keys) is not backed up; keep the secrets in a password manager.

## Configuration

Required environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_ID`
- `TELEGRAM_WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_WEBAPP_URL`
- `OPENROUTER_API_KEY`
- `DATABASE_URL` (default: `sqlite:///backend/data/app.db`)
- `LLM_MODEL` (default: `google/gemini-2.5-flash-lite`)

Optional:
- `YANDEX_TTS_API_KEY` (Yandex SpeechKit; takes precedence over Google when both are set)
- `YANDEX_TTS_VOICE` (default: `john`, the only English voice)
- `GOOGLE_TTS_API_KEY` (Google Cloud Text-to-Speech; with neither key set, pronunciation endpoints return 503)
- `GOOGLE_TTS_VOICE` (default: `en-US-Chirp3-HD-Aoede`; the language code is taken from the name)
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

## Testing Scope

Required in the first implementation:
- backend unit tests
- frontend component tests

Focus areas:
- acceptance/rejection of lexical units
- deduplication by source text and canonical form
- card persistence
- answer checking (layout, typos, inflected chunk targets)
- FSRS scheduling, session queue limits and the midnight day boundary, grade/undo
- review summary metrics and reminder decisions
- rare-word confirmation
- Telegram Web App rendering of API data and the review flow (intro → typed, check → grade, 409 refetch)

## Defaults and Constraints

- Single-user only in the first version
- Telegram runs in webhook mode
- Rate limit: no more than 5 requests per minute from the allowed user
- Review defaults: 5 new / 50 reviews per day, desired retention 0.9, learn threshold 3, reminder at 10:00, day starts at local midnight, timezone follows the device
- Default LLM model: `google/gemini-2.5-flash-lite`
- Cards are rejected when the model is not confident the input is a stable lexical unit
- Backend is the source of truth for all stored cards and review state

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
