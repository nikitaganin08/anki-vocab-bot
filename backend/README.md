# anki-vocab-bot backend

This package contains the FastAPI app, Telegram bot runtime, persistence layer,
and review (FSRS) services for the anki-vocab-bot monorepo.

Useful local commands:
- `uv run uvicorn app.main:app --reload` for API development.
- `uv run pytest` and `uv run ruff check` for the quality gates.

Review (SRS):
- FSRS scheduling (`fsrs` package) runs server-side; state lives on `cards.srs_*`, every answer
  is appended to `review_logs`, user preferences are the single `app_settings` row.
- Mini App endpoints (Telegram Web App auth): `/api/review/*`, `/api/settings`,
  `PATCH /api/cards/{id}` (`is_learning` toggle).

Pronunciation:
- Yandex SpeechKit or Google Cloud Text-to-Speech, proxied by the backend:
  `GET /api/cards/{id}/audio` (Web App auth) returns an MP3 of `canonical_text`, synthesized per
  request; nothing is stored on the server.
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
  saved as not learning and the bot asks "Учить?" with inline buttons.

Webhook mode:
- Telegram delivers updates to `POST /telegram/webhook`.
- Required webhook env vars: `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`.
- Telegram admin panel is served as a Web App under `/telegram/webapp`.
- Required runtime env var for the Web App launcher: `TELEGRAM_WEBAPP_URL`.
- Bot command `/find <description>` asks the LLM for 3 to 5 likely English lexical units
  from a clue and returns them without creating a card.

## Docker

From repository root:
- `docker build -t anki-vocab-bot:local .`
- `docker compose up --build` (needs the external `edge` network: `docker network create edge`)
