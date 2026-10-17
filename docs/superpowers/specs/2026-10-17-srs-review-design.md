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
| Scheduler | Server-side `fsrs` (py-fsrs ≥ 6.3.2, MIT). `desired_retention` from settings (default 0.9), default learning steps 1m/10m, relearning 10m, `enable_fuzzing=False` so interval labels are exact. Review-state outcomes follow Anki's ordering: Good ≥ Hard + 1 day, Easy ≥ Good + 1 day (same adjusted due for preview and grade). |
| Day boundary | 04:00 in the configured timezone (default `Europe/Moscow`). |
| Limits | 5 new / 50 reviews per day (settings). Due backlog above the review limit is carried over and shown as "отложено". |
| What is learned | One flag `is_learning` (renamed from `eligible_for_anki`) drives both SRS queue and Anki sync. |
| Rare words | `frequency >= learn_threshold` (default 3) → learning automatically. Below → saved, not learning; bot asks "Учить?" with inline buttons. Batch import: rare → not learning, toggle in Mini App. |
| Card content | `chunks` (0–5 frequent usage chunks `{text, target, translation}`) become the main content; examples reduced to 1 for new cards. |
| Front side | Chunk with `target` replaced by `___` + chunk translation; chunks rotate per review (`review count % len(chunks)`). No chunks → Russian translation, type the English unit. |
| Typing | Always required. New cards: intro (full card, "Запомнил") first, typed question later in the same session. |
| Back side | Full card: diff of typed vs expected, word + audio + IPA, translations, chunks, 1 example, word family, explanation (full, wrapped). Auto-selected grade, user can change; "Мой ответ верный" override. |
| Reminders | Background asyncio loop in the FastAPI lifespan, one message a day at the chosen hour, suppressed/backed-off per research. |
| Anki | Sync unchanged in mechanics; `Example` field = chunks + example. Owner's `English::Inbox` deck is imported with approximate FSRS state. |

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

Backfill pass for existing cards (one-off script, deleted after run): asks only for `chunks` + best single example for a given card, keeps canonical text, translations, IPA unchanged.

## Bot flows

- New card accepted, `frequency >= learn_threshold` → as today + `is_learning=True`.
- Below threshold → card saved `is_learning=False`; reply = card + "Редкое слово (N/10). Учить?" with inline buttons `learn:<id>` / `skip:<id>`. Callback sets the flag, edits the message to drop buttons and states the choice. Duplicate of a not-learning card → same buttons again.
- `/admin` stays; add `/review` → web_app button that opens the review screen directly.

## Review API (Mini App auth, same `require_telegram_webapp_user`)

- `GET /api/review/summary` → today goal (due capped by limits, new remaining, est. minutes from median `response_ms`), retention 30d (share of non-Again answers on cards with `elapsed ≥ 7d`), learned total (`srs_state=review`) + delta 7d, streak + best streak (day counts if ≥5 typed answers; 2 freeze days per week), heatmap last 14 weeks, forecast (tomorrow, 7-day average), `backlog` (due beyond limit), `due_all` (all due learning + review cards, ignoring the limit), `days_away` (study days since the last answer; null if never).
- `GET /api/review/session?size=10&include_backlog=false` → next round (`include_backlog=true` ignores the daily review limit): due learning/relearning first; then due reviews ordered by retrievability desc (warm-up); new cards interleaved (intro + typed later), respecting daily limits. Each item: card payload, `intro`, `srs_due_at`, `prompt` `{kind, index, masked, hint_translation, first_letter_hint}` (`first_letter_hint`: first letter, `_` per further letter, spaces kept; the expected answer itself is not sent).
- `POST /api/review/{id}/check` `{typed, prompt_kind, prompt_index, hint_used}` → `{verdict, expected, auto_rating, intervals: {1..4: seconds}}` (the client renders the diff). Stateless; no DB write.
- `POST /api/review/{id}/grade` `{rating, auto_rating, overridden, typed, prompt_kind, prompt_index, verdict, hint_used, response_ms, expected_due_at}` → schedules with py-fsrs, writes `review_logs`, returns next due. `expected_due_at` echoes the session's `srs_due_at` (±1 s), otherwise 409 — guards against double-taps.
- `POST /api/review/undo` → restores `card_before_json` of the latest log row and deletes it.
- `GET/PUT /api/settings`; `PATCH /api/cards/{id}` `{is_learning}`.

### Answer checking (`app/services/answer_check.py`)

Normalise: NFKC, casefold, trim, collapse spaces, `’`→`'`, strip trailing punctuation. If the typed text has Cyrillic letters, convert from the ЙЦУКЕН layout to QWERTY first. Verdict: equal → `correct`; Damerau-Levenshtein 1 and expected length ≥ 5 → `typo` (counts as correct); else `wrong`. For translation prompts the expected answer is `canonical_text` (articles "to "/"a "/"the " optional). Auto rating: wrong → Again, correct/typo with hint → Hard, correct/typo → Good. Easy only by user choice.

## Reminders (`app/services/reminders.py`)

Loop every 5 minutes in FastAPI lifespan (`asyncio.create_task`; single uvicorn worker — ceiling noted in code). Send when: local time ≥ `reminder_hour`, `last_reminder_on != today`, no review logs today, due+new > 0, backoff allows (`ignored_reminders` ≥3 → every other day, ≥7 → paused until next session; any session resets to 0). Message (M1): 12 rotating short templates with counts and minutes, optional anchor prefix, no warm-up chunk; Monday adds last week's summary (active days, learned delta, retention). Inline web_app button opens `?view=review`. No streak mentions, no evening ping.

## Mini App (design approved 2026-10-17)

Look: flat, neutral, follows the Telegram theme (`Telegram.WebApp.themeParams` → CSS variables with light fallbacks); one accent button per screen; no gradients. The existing cards page is restyled to the same tokens. Russian UI copy, sentence case.

Views switched by `?view=` (no router): `home`, `review`, `cards`, `settings`; the reminder and `/review` open `?view=review`.

- **Navigation — N1:** bottom tab bar with 4 tabs: Главная, Повтор, Слова, Настройки (Tabler-style outline icons). Hidden during an active review; Telegram BackButton leaves the review to Главная.
- **Главная — dashboard v2:** "Цель на сегодня: N карточек · ~M мин" (`due_today + new_today`, `est_minutes`), accent button "Начать", secondary "Быстро: 5 карточек"; 2×2 stats: "Удержание за 30 дн." `retention_30d` with "цель 90%", "Выучено" `learned_total` with "+delta за неделю"; activity heatmap captioned "Активность", 14 weeks × 7 days (rows Monday→Sunday) from `heatmap` (empty days neutral grey, never red); small line "серия N дн. · лучшая M" shown only when `streak_days >= 3`; forecast "Завтра ~X · неделя ~Y/день". If `backlog > 0`: muted "Отложено: N".
- **С возвращением — W2:** shown instead of the goal card when `days_away >= 3` and there is something due: title "С возвращением", "Как сегодня?", buttons "5 минут" (accent; session capped at `ceil(5 / est per card)` cards, min 5; reaching the cap ends the round), "Обычная сессия", "Всё сразу (N)" (`due_all`, ignores the daily review limit via `include_backlog=true`).
- **Знакомство — I1:** chip "Новое", full card (word + audio + IPA, translations, chunks, example), accent button "Запомнил"; the typed question for that card is inserted two items later in the same round.
- **Вопрос:** "Раунд R · k из T" (T = typed questions in the round: 10, fewer when the server returns fewer, 5 for "Быстро") + "~N мин", round progress bar; masked chunk (or translations), hint translation under it; input autofocus, Enter submits, `autocorrect/autocapitalize/spellcheck` off; "Подсказка: первая буква" (sets `hint_used`); accent button "Проверить".
- **Оборот:** "Ты: <typed> → верно: <expected>" (wrong: typed struck through in danger colour, expected in success colour; or "✓ верно" / "опечатка"), word + audio + IPA + translations, "Как используется" chunks, 1 example, word family, explanation (full, wrapped); "Мой ответ верный" link, shown only after a wrong answer (forces Good, `overridden=true`); 4 grade buttons "Снова / Трудно / Хорошо / Легко" (Again/Hard/Good/Easy) with interval labels from `check`, the auto-rated one highlighted; caption "Оценка выбрана автоматически, можно поменять". Audio = browser `speechSynthesis` (en-US), no server audio.
- **Конец раунда — R1:** "✓ Раунд готов", "Сегодня X из Y" with a progress bar to the daily goal, "Осталось ~N мин", accent "Ещё раунд", secondary "На сегодня хватит". When nothing is left: "Готово на сегодня", "Завтра ~X карточек", single "Закрыть" (back to Главная).
- **Настройки — S1:** one plain list: Новых в день, Повторений в день, Целевое удержание (80–95 %), Напоминание (час), Привязка (text, optional), Порог «учить» (0–10), Часовой пояс; "Сохранить".
- **Слова:** existing list (search, filters, batch import, delete) + per-card "Учим" toggle (`PATCH is_learning`).
- **Бот, редкое слово — B1:** card message, then a separate message "Редкое слово (N/10). Учить?" with "Учить" / "Не учить" (as implemented).
- **Бот, напоминание — M1:** short: "{anchor — }17 карточек, ~6 минут." + button "Повторить"; Monday appends the weekly block; no warm-up chunk.

Input UX: rounds of 10; Again re-queues via the next round (learning look-ahead), never grows the current denominator; on 409 from `grade` the client refetches the session.

## Anki import (`app/scripts/import_anki.py`, local, one-off)

Via AnkiConnect: `findNotes deck:"English::Inbox"`, `notesInfo`, `cardsInfo`, `getReviewsOfCards` (latest review time). For each note:
- tag `avb-card-<id>` → existing backend card (marked synced with the note id, so `sync_anki` never re-adds it); else a card with the same normalized canonical text; otherwise create via the normal card pipeline from the `Word` field (LLM fills explanation, chunks, IPA; Anki translation kept as first translation variant if the LLM's differs).
- FSRS state from Anki card: new → none; learning / relearning → `Learning` / `Relearning` step 0, due now; review → `Review` with `stability = max(interval days, 1)`, `difficulty = clamp(5 + (2.5 − ease) × 4, 1, 10)`, `last_review` = latest Anki review (fallback: now − interval), `due = last_review + interval`; suspended → `is_learning=False`.
- Reps/lapses copied from Anki; the card is marked `synced` with the Anki note id, so `sync_anki` does not push it again.
Goes through a token-protected endpoint `POST /api/anki/import` (same bearer token as sync).

## Testing

Backend unit tests: answer checker (layout, typo, inflected targets), queue building (limits, day boundary at 04:00, learning re-queue, warm-up order), grade/undo round trip with py-fsrs, summary metrics, reminder decision function (pure function of settings + now + counts), contract validation for chunks, rare-word callback, import state mapping. Frontend component tests: dashboard renders summary, review flow (type → check → grade), intro → typed, settings form. Gates: `uv run pytest`, `ruff check`, `tsc`, `vitest`, `npm run build`.

## Rollout

1. PR #3 (cleanup) merged first; this work branches on top.
2. Backend PR: migration, contract, review API, reminders, bot flows, import/backfill scripts.
3. The Mini App (frontend) ships in the same PR #4 as the backend.
4. On prod: run backfill (`docker compose exec app python -m app.scripts.backfill_chunks`), then local `import_anki`; delete both scripts in a follow-up.
