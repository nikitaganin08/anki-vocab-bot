# anki-vocab-bot backend

This package contains the FastAPI app, Telegram bot runtime, persistence layer,
and sync helpers for the anki-vocab-bot monorepo.

Useful local commands:
- `uv run uvicorn app.main:app --reload` for API development.
- `uv run python -m app.scripts.sync_anki --limit 50` for one sync pass.

Review (SRS):
- FSRS scheduling (`fsrs` package) runs server-side; state lives on `cards.srs_*`, every answer
  is appended to `review_logs`, user preferences are the single `app_settings` row.
- Mini App endpoints (Telegram Web App auth): `/api/review/*`, `/api/settings`,
  `PATCH /api/cards/{id}` (`is_learning` toggle).

Pronunciation:
- Yandex SpeechKit or Google Cloud Text-to-Speech, proxied by the backend:
  `GET /api/cards/{id}/audio` (Web App auth) and `GET /api/anki/cards/{id}/audio` (bearer token)
  return an MP3 of `canonical_text`, synthesized per request; nothing is stored on the server.
- Provider selection: `YANDEX_TTS_API_KEY` set -> Yandex (optional `YANDEX_TTS_VOICE`, default
  `john`, the only English SpeechKit voice); else `GOOGLE_TTS_API_KEY` set -> Google (optional
  `GOOGLE_TTS_VOICE`, default `en-US-Chirp3-HD-Aoede`). If both are set, Yandex wins. With
  neither, the endpoints return 503, `GET /api/settings` reports `tts_enabled: false` and the
  Mini App uses device `speechSynthesis`.
- Yandex price: about 1342 RUB per 1M characters including VAT; the whole 1.1k-word deck is
  about 20 RUB. Yandex setup: create a Yandex Cloud account and a billing account, create a
  service account with the role `ai.speechkit-tts.user`, create an API key for it, put
  `YANDEX_TTS_API_KEY` in `/opt/anki-vocab-bot/.env` on the VPS, then `docker compose up -d app`.
- Not verified live yet: `lang=en-US` with voice `john` is documented only on the SpeechKit
  voices page. Check one `GET /api/cards/{id}/audio` after setting the key.
- Google: Chirp 3 HD is free up to 1M characters per month; set a quota for the
  Text-to-Speech API in the GCP console. Needs a billing account.
- The day starts at midnight in `app_settings.timezone` (default `Europe/Moscow`); the Mini App
  saves the device timezone on load when it differs (manual override in Settings).
- A daily reminder loop runs in the FastAPI lifespan when `TELEGRAM_BOT_TOKEN` is set; set
  `DISABLE_REMINDERS=1` to turn it off (tests do).
- Bot command `/review` opens the review view; rare words (`frequency < learn_threshold`) are
  saved as not learning and the bot asks "Rare word (N/10). Learn it?" with inline "Learn" / "Skip"
  buttons. All bot copy is English.

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

Optional local desktop launch variables:
- `ANKI_DESKTOP_STARTUP_TIMEOUT_SECONDS` (default: `20`)

Idempotency policy:
- each card is tagged in Anki as `avb-card-<card_id>`
- sync checks `findNotes` by tag before creating a note
- if found, sync acknowledges the existing note id instead of creating duplicate
- pronunciation audio is downloaded from `GET /api/anki/cards/<card_id>/audio` and uploaded to
  Anki media as `avb-pronunciation-<card_id>.mp3`; best-effort: on any audio failure (e.g. 503
  before a TTS key is set) the note is added with an empty `PronunciationAudio`
  field, one warning with the cause is logged and the rest of the run skips audio

## Docker

From repository root:
- `docker build -t anki-vocab-bot:local .`
- `docker compose up --build` (needs the external `edge` network: `docker network create edge`)
