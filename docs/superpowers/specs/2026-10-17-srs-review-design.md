# SRS review in the Telegram Mini App — design

Date: 2026-10-17. Status: agreed in chat (sections 1–4); Mini App design approved 2026-10-17.
Research inputs: `docs/research/market-research-2026-10.md`, `docs/research/motivation-ux-2026-10.md`.

## Goal

Turn the bot from "Anki card generator" into a self-contained vocabulary trainer: words captured in
Telegram are reviewed inside the Telegram Mini App with FSRS scheduling, typed answers and usage
chunks. The bot sends one daily reminder. Anki sync stays as an optional parallel path (offline use).

Success: the owner moves daily practice from Anki to the Mini App (5 new / 50 reviews a day) and
keeps it for 12+ weeks; metrics from `review_logs` show it.

## Non-goals (this cycle)

- Multi-user, quotas, public hosting, payments (next cycle; single `TELEGRAM_ALLOWED_USER_ID` stays).
- Offline review, native mobile app, decks, custom card templates, gamification (XP, leagues, badges).
- Importing Anki revlog history; FSRS parameter optimisation (logs are kept to enable it later).

## Decisions

| Topic | Decision |
|---|---|
| Scheduler | Server-side `fsrs` (py-fsrs ≥ 6.3.2, MIT). `desired_retention` from settings (default 0.9), Anki-like learning steps 1m then 1 day (a new card: Again 1m, Good 1 day, Easy 2 days), relearning 10m, `enable_fuzzing=False` so interval labels are exact. Review-state outcomes follow Anki's ordering: Good ≥ Hard + 1 day, Easy ≥ Good + 1 day. Easy vs Good: when a new/learning card's Good is ≥ 1 day away, Easy = 2 × Good; for review/relearning cards FSRS Easy is capped at 2 × Good (all capped at the maximum interval; same adjusted due for preview and grade). |
| Day boundary | Midnight in the configured timezone (default `Europe/Moscow`). The timezone follows the device: on each Mini App load the shell saves `Intl.DateTimeFormat().resolvedOptions().timeZone` when it differs from the stored one and refreshes the summary; a zone picked by hand in Settings lasts until the next load with a different device zone (hint under the field). Like Anki, review cards and learning cards on an interday step are due for the whole study day of their due date; intraday learning steps keep their exact time (+20 min look-ahead). |
| Limits | 5 new / 50 reviews per day (settings). Due backlog above the review limit is carried over and shown as "отложено". |
| What is learned | One flag `is_learning` (renamed from `eligible_for_anki`) drives both SRS queue and Anki sync. |
| Rare words | `frequency >= learn_threshold` (default 3) → learning automatically. Below → saved, not learning; bot asks "Учить?" with inline buttons. Batch import: rare → not learning, toggle in Mini App. |
| Card content | `chunks` (0–5 frequent usage chunks `{text, target, translation}`) become the main content; examples reduced to 1 for new cards. |
| Front side | Chunk with `target` replaced by `___` + chunk translation; chunks rotate per review (`review count % len(chunks)`). No chunks → Russian translation, type the English unit. |
| Typing | Always required. New cards: intro (full card, "Got it") first, typed question later in the same session. |
| Back side | Diff of typed vs expected, then the full card: word + audio + IPA, translations, explanation, chunks, 1 example, word family (one form per line). Auto-selected grade, user can change; "My answer was right" override. |
| Reminders | Background asyncio loop in the FastAPI lifespan, one message a day at the chosen hour, suppressed/backed-off per research. |
| Anki | Sync unchanged in mechanics; `Example` field = chunks + example; pronunciation MP3 comes from the backend (Yandex SpeechKit or Google TTS, best-effort). Owner's `English::Inbox` deck is imported with approximate FSRS state. |

## Data model (Alembic migration `0005`)

`cards` — add:
- `chunks_json` JSON not null default `[]` — list of `{text, target, translation}`.
- `srs_card_json` JSON null — `fsrs.Card.to_json()`; null = never scheduled.
- `srs_due_at` DateTime(tz) null, indexed — copy of `Card.due` for queue queries.
- `srs_state` String null — `learning|review|relearning` (null = new).
- `srs_reps` Integer default 0, `srs_lapses` Integer default 0 (dashboard/history; FSRS card has no counters).
- rename `eligible_for_anki` → `is_learning` (batch_alter_table).

`review_logs` (new):
`id, card_id FK (cascade), reviewed_at, rating (1-4), auto_rating, overridden bool, prompt_kind (chunk|translation), prompt_index, typed_answer, verdict (correct|typo|wrong|skipped), hint_used bool, response_ms, retrievability float null, card_before_json (for undo), state_before`.
Intro screens are not logged as reviews (FSRS sees the first typed answer).

`app_settings` (new, single row id=1):
`timezone, reminder_hour, reminder_anchor (text, e.g. "после кофе"), new_per_day, reviews_per_day, desired_retention, learn_threshold, last_reminder_on (date), ignored_reminders (int)`.

## LLM contract changes

Accepted result adds `chunks`: 0–5 items `{text, target, translation}`:
- `text` English, 2–6 words, frequent natural usage of `canonical_text` (collocation, typical object/complement, fixed frame); `target` is the exact substring of `text` that realises `canonical_text` (may be inflected); `translation` Russian.
- Return `[]` when no frequent chunks exist (rare/technical words). Function words are rejected as input. Invalid chunks are dropped one by one; they never reject the whole card.
- `examples` becomes 1–3 items (prompt asks for exactly 1; old 3-example cards stay valid). The "≥2 examples reference canonical" check becomes "every chunk `target` is in its `text`, and the example or ≥1 chunk references canonical".
- Prompt adds: reject function words (articles, pronouns, auxiliaries, prepositions on their own).

Backfill pass for existing cards (one-off script, run 2026-10-17 and deleted, see git history): asks only for `chunks` + best single example for a given card, keeps canonical text, translations, IPA unchanged.

## Bot flows

- New card accepted, `frequency >= learn_threshold` → as today + `is_learning=True`.
- Below threshold → card saved `is_learning=False`; reply = card + "Редкое слово (N/10). Учить?" with inline buttons `learn:<id>` / `skip:<id>`. Callback sets the flag, edits the message to drop buttons and states the choice. Duplicate of a not-learning card → same buttons again.
- `/admin` stays; add `/review` → web_app button that opens the review screen directly.

## Review API (Mini App auth, same `require_telegram_webapp_user`)

- `GET /api/review/summary` → today goal (due capped by limits, new remaining, est. minutes from median `response_ms`), retention 30d (share of non-Again answers on cards with `elapsed ≥ 7d`), learned total (`srs_state=review`) + delta 7d, streak + best streak (day counts if ≥5 typed answers; 2 freeze days per week), heatmap last 14 weeks, forecast (tomorrow, 7-day average), `backlog` (due beyond limit), `due_all` (all due learning + review cards, ignoring the limit), `days_away` (study days since the last answer; null if never).
- `GET /api/review/session?size=10&include_backlog=false` → next round (`include_backlog=true` ignores the daily review limit): due learning/relearning first; then due reviews ordered by retrievability desc (warm-up); new cards interleaved (intro + typed later), respecting daily limits. Each item: card payload, `intro`, `srs_due_at`, `prompt` `{kind, index, masked, hint_translation}` (the expected answer itself is not sent).
- `POST /api/review/{id}/check` `{typed, prompt_kind, prompt_index, hint_used}` → `{verdict, expected, auto_rating, intervals: {1..4: seconds}}` (the client renders the diff). Stateless; no DB write.
- `POST /api/review/{id}/grade` `{rating, auto_rating, overridden, typed, prompt_kind, prompt_index, verdict, hint_used, response_ms, expected_due_at}` → schedules with py-fsrs, writes `review_logs`, returns next due. `expected_due_at` echoes the session's `srs_due_at` (±1 s), otherwise 409 — guards against double-taps.
- `POST /api/review/undo` → restores `card_before_json` of the latest log row and deletes it.
- `GET/PUT /api/settings`; `PATCH /api/cards/{id}` `{is_learning}`.

### Answer checking (`app/services/answer_check.py`)

Normalise: NFKC, casefold, trim, collapse spaces, `’`→`'`, strip trailing punctuation. If the typed text has Cyrillic letters, convert from the ЙЦУКЕН layout to QWERTY first. Verdict: equal → `correct`; Damerau-Levenshtein 1 and expected length ≥ 5 → `typo` (counts as correct); else `wrong`. For translation prompts the expected answer is `canonical_text` (articles "to "/"a "/"the " optional). Auto rating: wrong → Again, correct/typo with hint → Hard, correct/typo → Good. Easy only by user choice.

## Reminders (`app/services/reminders.py`)

Loop every 5 minutes in FastAPI lifespan (`asyncio.create_task`; single uvicorn worker — ceiling noted in code). Send when: local time ≥ `reminder_hour`, `last_reminder_on != today`, no review logs today, due+new > 0, backoff allows (`ignored_reminders` ≥3 → every other day, ≥7 → paused until next session; any session resets to 0). Message (M1): 12 rotating short templates with counts and minutes, optional anchor prefix, no warm-up chunk; Monday adds last week's summary (active days, learned delta, retention). Inline web_app button opens `?view=review`. No streak mentions, no evening ping.

## Mini App (design approved 2026-10-17)

Daily counts are distinct cards on every screen: `done_today` = cards with at least one answer today that are not due again (an Again that comes back within the learning look-ahead is not done until it passes); `due_today` and `new_today` are what remains.

Look: flat, neutral, follows the Telegram theme (`Telegram.WebApp.themeParams` → CSS variables with light fallbacks); one accent button per screen; no gradients. The existing cards page is restyled to the same tokens. English UI copy, sentence case (`<html lang="en">`; changed 2026-10-17 from Russian); Russian appears only as card data (translations, chunk translations).

Full card (intro and back side, one component): word + speaker + IPA → translations → explanation (full English definition) → "Usage" chunks → one example → word family, each form on its own line ("distinguishable (adjective) — различимый"), never joined with "·".

Audio (revised 2026-10-17): Yandex SpeechKit (voice `john`) or Google Cloud Text-to-Speech (`en-US-Chirp3-HD-Aoede` by default), proxied by the backend and never stored on the server. Provider: `YANDEX_TTS_API_KEY` set -> Yandex, else `GOOGLE_TTS_API_KEY` set -> Google, both set -> Yandex (the owner cannot set up Google billing from Russia). Yandex costs about 1342 RUB per 1M characters including VAT (the whole 1.1k-word deck is about 20 RUB); `lang=en-US` with `john` is documented only on the voices page and not verified live yet. `GET /api/cards/{id}/audio` synthesizes `canonical_text` per request and returns `audio/mpeg` with `Cache-Control: private, max-age=31536000, immutable`; inert until a TTS key is set (503). The speaker shows when `GET /api/settings` reports `tts_enabled` or `speechSynthesis` exists. On tap only (no autoplay, no prefetch) the Mini App fetches the MP3 once per card per page load, keeps the object URL in memory and plays it; on any failure or without the key it falls back to `speechSynthesis` (lang en-US, an English voice when listed), else silent. Label "Play pronunciation". Google Chirp 3 HD is free up to 1M characters per month; with Google the owner sets a quota in the GCP console. Anki audio: `sync_anki` downloads the same MP3 from `GET /api/anki/cards/{id}/audio` (bearer token); best-effort, the note is added with an empty `PronunciationAudio` field when audio fails. (Earlier device-only decision: edge-tts got 403 from Microsoft.)

Views switched by `?view=` (no router): `home`, `review`, `cards`, `settings`; the reminder and `/review` open `?view=review`.

- **Navigation — N1:** bottom tab bar with 4 tabs: Home, Review, Words, Settings (Tabler-style outline icons). Hidden during an active review; Telegram BackButton leaves the review to Home.
- **Home — dashboard v2:** "Today's goal: Y cards · ~M min" (Y = `done_today + due_today + new_today`, M from `est_minutes` of what remains), a muted "X done · R left" line when `done_today > 0` (R = `due_today + new_today`), accent button "Start", secondary "Quick: 5 cards"; 2×2 stats: "Retention (30 days)" `retention_30d` with "goal 90%", "Learned" `learned_total` with "+delta this week"; activity heatmap captioned "Activity", 14 weeks × 7 days (rows Monday→Sunday) from `heatmap` (empty days neutral grey, never red); small line "streak N days · best M" shown only when `streak_days >= 3`; forecast "Tomorrow ~X · week ~Y/day". If `backlog > 0`: muted "Postponed: N".
- **Welcome back — W2:** shown instead of the goal card when `days_away >= 3` and there is something due: title "Welcome back", "How about today?", buttons "5 minutes" (accent; session capped at `ceil(5 / est per card)` cards, min 5; reaching the cap ends the round), "Regular session", "All at once (N)" (`due_all`, ignores the daily review limit via `include_backlog=true`).
- **Intro — I1:** chip "New word", the full card, accent button "Got it"; the typed question for that card is inserted two items later in the same round.
- **Question:** "Round R · k of T" (T = typed questions in the round: 10, fewer when the server returns fewer, 5 for "Quick") + "~N min", round progress bar; masked chunk (or translations), hint translation under it; input autofocus, placeholder "Type the missing part" (chunk) / "Type in English" (translation), Enter submits, `autocorrect/autocapitalize/spellcheck` off; link "What's this word?" under the input reveals the card's English explanation below it, focus stays in the input (sets `hint_used`); accent button "Check". Chunk prompts also show the word's own translations under the chunk translation (design T1), because a chunk's translation can be too figurative.
- **Back side:** "You: <typed> → correct: <expected>" (wrong: typed struck through in danger colour, expected in success colour; or "✓ correct" / "typo"), then the full card; "My answer was right" link, shown only after a wrong answer (forces Good, `overridden=true`); 4 grade buttons "Again / Hard / Good / Easy" with interval labels from `check` ("<1m", "10m", "12h", "2d"), the auto-rated one highlighted; caption "Rating picked automatically — you can change it".
- **Round end — R1:** "✓ Round complete", "Today X of Y" with a progress bar to the daily goal (X = `done_today`, Y = `done_today + due_today + new_today` from the summary fetched after the round: the same distinct-card counts as Home, so an Again that is due again does not count as done), "~N min left", accent "Another round", secondary "Done for today". When nothing is left: "Done for today", "Tomorrow ~X cards", single "Close" (back to Home).
- **Settings — S1:** one plain list: New cards per day, Reviews per day, Target retention (80–95 %), Reminder (hour), Reminder anchor (text, optional), Learn threshold (0–10), Time zone (filled from the device automatically, editable as an override; hint "Detected from your device on every launch"); "Save", then "Saved".
- **Words:** existing list (search, filters, batch import, delete) + per-card "Learning" toggle (`PATCH is_learning`). Errors read "Couldn't load data" with "Try again"; outside Telegram the app asks to open it from Telegram.
- **Бот, редкое слово — B1:** card message, then a separate message "Редкое слово (N/10). Учить?" with "Учить" / "Не учить" (as implemented).
- **Бот, напоминание — M1:** short: "{anchor — }17 карточек, ~6 минут." + button "Повторить"; Monday appends the weekly block; no warm-up chunk.

Input UX: rounds of 10; Again re-queues via the next round (learning look-ahead), never grows the current denominator; on 409 from `grade` the client refetches the session.

## Anki import (done 2026-10-17; script and `POST /api/anki/import` removed, see git history)

Via AnkiConnect: `findNotes deck:"English::Inbox"`, `notesInfo`, `cardsInfo`, `getReviewsOfCards` (latest review time). For each note:
- tag `avb-card-<id>` → existing backend card (marked synced with the note id, so `sync_anki` never re-adds it); else a card with the same normalized canonical text; otherwise create via the normal card pipeline from the `Word` field (LLM fills explanation, chunks, IPA; Anki translation kept as first translation variant if the LLM's differs).
- FSRS state from Anki card: new → none; learning / relearning → `Learning` / `Relearning` step 0, due now; review → `Review` with `stability = max(interval days, 1)`, `difficulty = clamp(5 + (2.5 − ease) × 4, 1, 10)`, `last_review` = latest Anki review (fallback: now − interval), `due = last_review + interval`; suspended → `is_learning=False`.
- Reps/lapses copied from Anki; the card is marked `synced` with the Anki note id, so `sync_anki` does not push it again.
Goes through a token-protected endpoint `POST /api/anki/import` (same bearer token as sync).

## Testing

Backend unit tests: answer checker (layout, typo, inflected targets), queue building (limits, day boundary at midnight, learning re-queue, warm-up order), grade/undo round trip with py-fsrs, summary metrics, reminder decision function (pure function of settings + now + counts), contract validation for chunks, rare-word callback. Frontend component tests: dashboard renders summary, review flow (type → check → grade), intro → typed, settings form, device timezone sync. Gates: `uv run pytest`, `ruff check`, `tsc`, `vitest`, `npm run build`.

## Rollout

1. PR #3 (cleanup) merged first; this work branches on top.
2. Backend PR: migration, contract, review API, reminders, bot flows, import/backfill scripts (run on 2026-10-17, then removed).
3. The Mini App (frontend) ships in the same PR #4 as the backend.
4. On prod: run backfill, then local Anki import. Done 2026-10-17; both scripts and the import endpoint were deleted afterwards (see git history).
