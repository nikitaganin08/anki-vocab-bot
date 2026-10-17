# SRS Review Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backend for FSRS review inside the Telegram Mini App: chunks in cards, typed-answer checking, review/settings API, rare-word confirmation, daily reminders, chunk backfill and Anki import.

**Architecture:** Server-side py-fsrs scheduling; SRS state lives on `cards` (single user), every answer is appended to `review_logs`; one-row `app_settings` holds user preferences. Pure services (`answer_check`, `srs`, `review_stats`, `reminders`) are called by thin FastAPI routers and aiogram handlers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, aiogram 3, `fsrs>=6.3.2,<7`, `tzdata`, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-10-17-srs-review-design.md`

## Global Constraints

- Branch `feat/srs-backend` (based on `chore/repo-cleanup` + docs). Never edit existing Alembic migrations; new one is `20261017_0005`.
- Run from `backend/`: `uv run pytest -q`, `uv run ruff check`, `uv run ruff format <changed files>` (never format the whole repo). Frontend gates when `frontend/` is touched: `npx tsc --noEmit && npm run test -- --run && npm run build`.
- All datetimes stored and passed to py-fsrs in UTC; values read from SQLite are naive and must go through `as_utc()` before use.
- Day starts at 04:00 in `app_settings.timezone` (default `Europe/Moscow`).
- Defaults: `new_per_day=5`, `reviews_per_day=50`, `desired_retention=0.9`, `learn_threshold=3`, `reminder_hour=10`, `reminder_anchor=None`.
- Scheduler: `fsrs.Scheduler(desired_retention=settings.desired_retention, enable_fuzzing=False)`, default learning steps (1m, 10m), relearning (10m).
- Chunks: 0–5 items `{text, target, translation}`; `target` is a case-insensitive substring of `text`; masked with `___` (first occurrence).
- Auto rating: wrong → 1 (Again); correct/typo with hint → 2 (Hard); correct/typo → 3 (Good). Easy (4) only by user choice.
- Mini App endpoints use `require_telegram_webapp_user`; Anki/import endpoints use `require_anki_token`.
- Bot copy is Russian, sentence case; reminder never mentions streaks; no evening reminder.
- Code style: match surrounding code; no new abstractions beyond the interfaces below.

## Review Focus

1. Naive datetimes from SQLite fed to py-fsrs (UTC-only) → grade after reloading the card from DB must work (Task 4 test `test_grade_after_reload_from_db`).
2. Chunk target in different case / inflected / repeated ("Give up and give up") → mask only first case-insensitive match, expected answer keeps chunk's casing (Task 3 test `test_build_prompt_masks_first_case_insensitive`).
3. Double-tap on a grade button → second request must not log a second review (Task 6 test `test_grade_rejects_stale_due`, 409).
4. Answers at 01:00 local count for the previous day; limits computed per 04:00 window (Task 4 test `test_day_window_before_4am_belongs_to_previous_day`).
5. Imported Anki notes must not be pushed to Anki again by `sync_anki` (Task 10 test `test_import_marks_card_synced_with_note_id`).

---

### Task 1: Data model, migration, `is_learning` rename, shared test fixtures

**Files:**
- Modify: `backend/pyproject.toml` (add `fsrs>=6.3.2,<7`, `tzdata>=2024.1`), `backend/uv.lock` (via `uv add`)
- Modify: `backend/app/models/card.py`, `backend/app/models/__init__.py`, `backend/alembic/env.py`
- Create: `backend/app/models/review_log.py`, `backend/app/models/app_settings.py`, `backend/app/services/app_settings.py`
- Create: `backend/alembic/versions/20261017_0005_srs_review.py`
- Create: `backend/tests/conftest.py` (move `session`, `client`, `authed_client`, `telegram_headers`, `mobile_headers`, `_make_card` → `make_card` from `tests/test_api.py`)
- Modify (rename `eligible_for_anki` → `is_learning` everywhere): `app/api/anki.py`, `app/api/cards.py` (query param `is_learning`), `app/api/schemas.py`, `app/services/card_service.py`, tests listed by `grep -rn eligible_for_anki backend/tests`, and frontend `src/api/types.ts`, `src/api/client.ts`, `src/pages/CardsPage.tsx` (label "Learning"), `src/**/*.test.tsx`.
- Test: `backend/tests/test_srs_models.py`

**Interfaces:**
- Produces:
  - `Card` new columns: `chunks_json: list[dict[str,str]]` (default `[]`), `srs_card_json: str | None` (Text, `fsrs.Card.to_json()`), `srs_due_at: datetime | None` (indexed), `srs_state: str | None`, `srs_reps: int = 0`, `srs_lapses: int = 0`, `is_learning: bool`.
  - `ReviewLogEntry` (`app.models.review_log`, table `review_logs`): `id, card_id (FK cards.id ondelete CASCADE, indexed), reviewed_at, rating, auto_rating, overridden, prompt_kind, prompt_index, typed_answer, verdict, hint_used, response_ms, retrievability (float|None), card_before_json (str|None), state_before (str|None)`.
  - `AppSettings` (`app.models.app_settings`, table `app_settings`, id=1): `timezone, reminder_hour, reminder_anchor, new_per_day, reviews_per_day, desired_retention, learn_threshold, last_reminder_on (date|None), ignored_reminders (int)`.
  - `get_app_settings(session: Session) -> AppSettings` — returns row id=1, creating it with Global Constraints defaults if missing.
  - `app/models/__init__.py` imports the three model modules; `alembic/env.py` does `import app.models  # noqa: F401`.

- [ ] **Step 1: Write failing tests** in `tests/test_srs_models.py`:
  - `test_get_app_settings_creates_defaults`: fresh DB → `get_app_settings(s)` returns `new_per_day == 5`, `reviews_per_day == 50`, `learn_threshold == 3`, `timezone == "Europe/Moscow"`; second call returns same id.
  - `test_review_log_cascade_on_card_delete`: delete card → its `ReviewLogEntry` rows gone.
  - `test_migration_upgrade_renames_flag` (uses a temp SQLite file + `alembic upgrade head` via `alembic.command`): after upgrade, `cards` has `is_learning`, `chunks_json`, `srs_due_at`; tables `review_logs`, `app_settings` exist; a row inserted before the migration with `eligible_for_anki=1` reads back `is_learning=1`.
- [ ] **Step 2:** `uv run pytest tests/test_srs_models.py -q` → FAIL (import errors).
- [ ] **Step 3:** `uv add "fsrs>=6.3.2,<7" "tzdata>=2024.1"`; implement models, accessor, migration (`batch_alter_table("cards")`: `alter_column("eligible_for_anki", new_column_name="is_learning")`, add columns with `server_default` for non-null ones; `create_table` for the two tables; downgrade reverses). Move fixtures to `conftest.py`; do the rename across backend + frontend.
- [ ] **Step 4:** `uv run pytest -q && uv run ruff check` → all pass; frontend gates pass.
- [ ] **Step 5:** Commit `feat: add SRS data model and rename eligible_for_anki to is_learning`.

### Task 2: Chunks in the LLM contract, card creation and Anki example

**Files:**
- Modify: `backend/app/schemas/llm.py`, `backend/app/services/llm_prompt.py`, `backend/app/services/card_service.py`, `backend/app/bot/formatter.py`, `backend/app/services/anki_sync.py`, `backend/app/clients/backend_sync_api.py` (`PendingCard.chunks`), `backend/app/api/schemas.py` (`CardResponse.chunks`, `AnkiPendingCardResponse.chunks`)
- Test: `tests/test_llm_schemas.py`, `tests/test_llm_prompt.py`, `tests/test_card_service.py`, `tests/test_bot_formatter.py`, `tests/test_anki_sync_service.py`

**Interfaces:**
- Consumes: `get_app_settings` (Task 1).
- Produces:
  - `class CardChunk(BaseModel)`: `text: str` (English, 2–6 words), `target: str`, `translation: str` (Cyrillic); validator: `target.casefold() in text.casefold()`.
  - `AcceptedLlmResponse.chunks: list[CardChunk] = Field(default_factory=list, max_length=5)`; `examples: list[str] = Field(min_length=1, max_length=3)`.
  - Semantic check replaces "≥2 examples reference canonical": for multi-token canonical, at least one of (examples[0], any chunk.text) references canonical (reuse `_example_references_canonical`).
  - `apply_source_text(...)` unchanged signature; sets `chunks_json=[c.model_dump() for c in llm_result.chunks]`, `is_learning = llm_result.frequency >= get_app_settings(session).learn_threshold`.
  - `format_anki_example(chunks: list[CardChunk], examples: list[str], word_family: list[WordFamilyItem]) -> str`: chunk lines `"{text} — {translation}"`, blank line, `examples[0]`, then the existing word-family block.

- [ ] **Step 1: Failing tests:**
  - `test_accepts_chunks_with_inflected_target` (`{"text":"gave up on him","target":"gave up","translation":"разуверился в нём"}` accepted).
  - `test_rejects_chunk_target_not_in_text` (ValueError).
  - `test_accepts_single_example_and_empty_chunks`.
  - `test_prompt_requests_chunks_and_rejects_function_words`: `SYSTEM_PROMPT` contains `"chunks"`, `"target"`, and the word `"function words"`.
  - `test_rare_word_is_not_learning` (frequency 2 → `is_learning is False`), `test_frequent_word_is_learning` (frequency 3 → True).
  - `test_format_card_payload_shows_chunks` (formatter output contains `"give up smoking — бросить курить"`).
  - `test_anki_example_lists_chunks_then_example`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Prompt changes: add `chunks` to the accepted contract with the rules from the spec (frequent natural usages, `target` = exact substring realising canonical_text, may be inflected, `[]` if none common), ask for exactly 1 example, and add "Reject function words on their own (articles, pronouns, auxiliaries, prepositions, conjunctions)". Formatter: section "🧩 Как используется" with one line per chunk, placed before examples; show only `examples[0]`.
- [ ] **Step 4:** `uv run pytest -q && uv run ruff check` → pass.
- [ ] **Step 5:** Commit `feat: add usage chunks to cards and learn threshold`.

### Task 3: Answer checking and prompt building (pure)

**Files:**
- Create: `backend/app/services/answer_check.py`
- Test: `backend/tests/test_answer_check.py`

**Interfaces:**
- Produces:
  - `normalize_answer(text: str) -> str` — NFKC, casefold, `’`/`‘` → `'`, collapse whitespace, strip trailing `.,!?;:`.
  - `ru_layout_to_en(text: str) -> str` — ЙЦУКЕН → QWERTY char map (both cases), other chars unchanged.
  - `@dataclass(slots=True) class AnswerCheck: verdict: Literal["correct","typo","wrong"]; expected: str`.
  - `check_answer(typed: str, expected: str, *, optional_prefixes: tuple[str, ...] = ()) -> AnswerCheck` — apply layout conversion if typed has Cyrillic; strip any of `optional_prefixes` (e.g. `"to "`, `"a "`, `"an "`, `"the "`) from both; equal → correct; Damerau-Levenshtein distance 1 and `len(expected) >= 5` → typo; else wrong. Empty typed → wrong.
  - `auto_rating(verdict: str, hint_used: bool) -> int`.
  - `@dataclass(slots=True) class Prompt: kind: Literal["chunk","translation"]; index: int; masked: str; hint_translation: str; expected: str`.
  - `build_prompt(chunks: list[dict[str,str]], translations: list[str], canonical_text: str, review_count: int) -> Prompt` — chunks present → `index = review_count % len(chunks)`, mask first case-insensitive occurrence of `target` with `___`, `expected` = target as it appears in `text`; else kind `translation`, `masked = ", ".join(translations)`, `expected = canonical_text`, index 0.

- [ ] **Step 1: Failing tests:** `test_exact_match_case_insensitive`, `test_one_typo_long_word_is_typo` (`"reluctnat"` vs `"reluctant"`), `test_one_typo_short_word_is_wrong` (`"giv"` vs `"give"`... len 4 → wrong), `test_russian_layout_converted` (`"пшму гз"` → correct for `"give up"`), `test_curly_apostrophe` (`"don’t"`), `test_optional_to_prefix` (`"to give up"` correct for `"give up"` with prefixes), `test_empty_is_wrong`, `test_auto_rating_matrix` (wrong→1, correct+hint→2, typo→3, correct→3), `test_build_prompt_rotates_chunks` (review_count 0,1,2 with 2 chunks → index 0,1,0), `test_build_prompt_masks_first_case_insensitive` (`text="Give up and give up"`, target `"give up"` → masked `"___ and give up"`, expected `"Give up"`), `test_build_prompt_falls_back_to_translation`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement (stdlib only; DL distance as a small DP).
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: add typed answer checking and prompt builder`.

### Task 4: Scheduling, session queue, grade and undo

**Files:**
- Create: `backend/app/services/srs.py`
- Test: `backend/tests/test_srs_service.py`

**Interfaces:**
- Consumes: Task 1 models/settings, Task 3 `build_prompt`, `Prompt`.
- Produces:
  - `as_utc(dt: datetime) -> datetime` (naive → UTC tzinfo).
  - `day_window(now: datetime, tz_name: str) -> tuple[datetime, datetime]` — UTC start/end of the 04:00-to-04:00 local day containing `now`.
  - `build_scheduler(settings: AppSettings) -> fsrs.Scheduler`.
  - `load_fsrs_card(card: Card) -> fsrs.Card` (new `fsrs.Card(card_id=card.id)` when `srs_card_json is None`; else `from_json` with `due`/`last_review` coerced via `as_utc`).
  - `preview_intervals(scheduler, card: Card, now: datetime) -> dict[int, int]` — seconds until due for ratings 1–4, computed on copies.
  - `@dataclass(slots=True) class SessionItem: card: Card; prompt: Prompt; intro: bool`.
  - `build_session(session: Session, settings: AppSettings, now: datetime, size: int = 10) -> list[SessionItem]` — order: (1) learning/relearning with `srs_due_at <= now + 20 min`; (2) review cards with `srs_due_at <= now`, sorted by retrievability desc, capped by `reviews_per_day − reviews done today`; (3) new learning cards (`is_learning` and `srs_card_json is None`), capped by `new_per_day − new introduced today`, each emitted as `intro=True`; only `is_learning=True` cards. "Done today" counts `review_logs` in `day_window`; "new introduced today" = distinct cards whose first log is today.
  - `@dataclass(slots=True) class GradeInput: rating: int; auto_rating: int; overridden: bool; typed_answer: str; prompt_kind: str; prompt_index: int; verdict: str; hint_used: bool; response_ms: int; expected_due_at: datetime | None`.
  - `class StaleReviewError(Exception)`.
  - `grade_card(session: Session, settings: AppSettings, card: Card, grade: GradeInput, now: datetime) -> Card` — if `grade.expected_due_at` differs from `card.srs_due_at` (both via `as_utc`, None == None) raise `StaleReviewError`; compute retrievability, `scheduler.review_card`, write `ReviewLogEntry` with `card_before_json`/`state_before`, update `srs_*` (`srs_reps += 1`, `srs_lapses += 1` when rating 1 from review state), commit.
  - `undo_last(session: Session) -> Card | None` — restore latest log's `card_before_json`/`state_before` (None → reset to new), recompute `srs_due_at`, decrement counters, delete the log.

- [ ] **Step 1: Failing tests** (use `now` fixed, e.g. `datetime(2026, 10, 20, 9, 0, tzinfo=UTC)`):
  - `test_day_window_before_4am_belongs_to_previous_day` (Moscow 01:00 on 21st → window start = 20th 01:00 UTC).
  - `test_new_card_good_goes_to_learning` (state learning, due ≈ now+10m).
  - `test_grade_after_reload_from_db` (grade, `session.expire_all()`, reload, grade again → no exception, two logs).
  - `test_session_order_learning_then_reviews_then_new` and `test_session_respects_daily_limits` (5 new already introduced today → no new items; 50 reviews logged → no review items, learning still returned).
  - `test_session_skips_not_learning_cards`.
  - `test_reviews_sorted_by_retrievability_desc`.
  - `test_grade_rejects_stale_due` (raises `StaleReviewError` when `expected_due_at` mismatches).
  - `test_undo_restores_previous_state` (grade then undo → `srs_card_json` equals before, log count 0).
  - `test_preview_intervals_monotonic` (1 ≤ 2 ≤ 3 ≤ 4 seconds).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Use `zoneinfo.ZoneInfo`. Mark `# ponytail: SRS state on cards (single user); move to user_cards for multi-user`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: add FSRS scheduling, session queue, grade and undo`.

### Task 5: Dashboard summary

**Files:**
- Create: `backend/app/services/review_stats.py`
- Test: `backend/tests/test_review_stats.py`

**Interfaces:**
- Consumes: Task 4 `day_window`, `as_utc`.
- Produces: `@dataclass(slots=True) class ReviewSummary` with `due_today: int, new_today: int, est_minutes: int, backlog: int, retention_30d: float | None, learned_total: int, learned_delta_7d: int, streak_days: int, best_streak_days: int, heatmap: list[int]` (98 daily answer counts, oldest first), `forecast_tomorrow: int, forecast_week_avg: int`; `build_summary(session: Session, settings: AppSettings, now: datetime) -> ReviewSummary`.
  - `due_today` = min(due review count, remaining review limit) + due learning; `backlog` = due reviews beyond the limit; `new_today` = remaining new limit capped by available new cards.
  - `est_minutes` = ceil((due_today + new_today×2) × median `response_ms` of last 200 logs (default 15 000 ms) / 60 000).
  - `retention_30d` = share of rating > 1 among logs in last 30 days where elapsed since previous review of that card ≥ 7 days; None if no such logs.
  - `learned_total` = cards with `srs_state == "review"`; delta = those whose first transition to review happened in last 7 days.
  - Streak: a day counts if ≥ 5 typed answers; up to 2 missed days per calendar week are forgiven; `best_streak_days` over all history.

- [ ] **Step 1: Failing tests:** `test_empty_db_summary` (all zeros, retention None, heatmap len 98), `test_backlog_beyond_limit` (60 due, limit 50 → due_today 50, backlog 10), `test_retention_counts_only_mature`, `test_streak_forgives_two_days_per_week`, `test_day_with_four_answers_breaks_streak_without_freeze`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement with plain queries + Python aggregation (single user; fine at this scale).
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: add review dashboard summary`.

### Task 6: Review, settings and card-toggle API

**Files:**
- Create: `backend/app/api/review.py`, `backend/app/api/settings.py`
- Modify: `backend/app/api/schemas.py`, `backend/app/api/cards.py` (PATCH), `backend/app/main.py`
- Test: `backend/tests/test_review_api.py`

**Interfaces:**
- Consumes: Tasks 3–5.
- Produces (all under `require_telegram_webapp_user`):
  - `GET /api/review/summary` → `ReviewSummary` fields as JSON.
  - `GET /api/review/session?size=10` (1–20) → `{"items": [{"card": CardResponse, "intro": bool, "prompt": {"kind","index","masked","hint_translation","expected_length","hint_letter"}, "srs_due_at": str|null}]}` — `expected` itself is NOT sent; `expected_length` = len, `hint_letter` = first char.
  - `POST /api/review/{card_id}/check` `{typed, prompt_kind, prompt_index, hint_used}` → `{verdict, expected, auto_rating, intervals: {"1":s,"2":s,"3":s,"4":s}}` (no DB write).
  - `POST /api/review/{card_id}/grade` `{rating, auto_rating, overridden, typed, prompt_kind, prompt_index, verdict, hint_used, response_ms, expected_due_at}` → `{srs_due_at, srs_state}`; 409 on `StaleReviewError`; 404 unknown card.
  - `POST /api/review/undo` → `{card_id}` or 404 when nothing to undo.
  - `GET /api/settings`, `PUT /api/settings` (validated ranges: hour 0–23, new 0–100, reviews 0–1000, retention 0.7–0.97, threshold 0–10, timezone must load in `ZoneInfo`).
  - `PATCH /api/cards/{card_id}` `{is_learning: bool}` → `CardResponse`.

- [ ] **Step 1: Failing tests:** `test_review_requires_telegram_auth` (401 without header), `test_session_hides_expected_answer`, `test_check_then_grade_flow` (check returns intervals, grade moves due), `test_grade_rejects_stale_due` (second identical grade → 409, one log), `test_undo_endpoint`, `test_settings_roundtrip_and_validation` (bad timezone → 422), `test_patch_is_learning`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement; `now = datetime.now(UTC)` inside handlers.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: add review, settings and learning toggle API`.

### Task 7: Bot — rare-word confirmation and /review

**Files:**
- Modify: `backend/app/bot/handler.py`, `backend/app/bot/formatter.py`, `backend/app/bot/runtime.py`
- Test: `backend/tests/test_bot_handler.py`, `backend/tests/test_bot_formatter.py`

**Interfaces:**
- Produces:
  - `build_learn_keyboard(card_id: int) -> InlineKeyboardMarkup` — buttons "Учить" (`learn:<id>`), "Не учить" (`skip:<id>`).
  - `format_rare_word_prompt(card: Card) -> str` → `"Редкое слово ({frequency}/10). Учить?"`.
  - `TelegramTextHandler` sends the card message; if `result.card` exists and `not result.card.is_learning`, sends `format_rare_word_prompt` with the keyboard as a second message.
  - `TelegramLearnCallbackHandler(allowed_user_id, set_learning: Callable[[int, bool], Card | None])` with `async handle_callback(callback)`: parses `learn:`/`skip:`, ignores other users, calls `set_learning`, edits the prompt message to `"Учим: {canonical_text}"` / `"Не учим: {canonical_text}"` (no keyboard), `callback.answer()`.
  - `/review` command → message "Повторение" with a web_app button to `f"{webapp_url}?view=review"`.

- [ ] **Step 1: Failing tests:** `test_rare_word_sends_learn_prompt`, `test_frequent_word_no_prompt`, `test_learn_callback_sets_flag_and_edits_message`, `test_callback_from_other_user_ignored`, `test_review_command_opens_review_view`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement; register `router.callback_query(F.data.regexp(r"^(learn|skip):\d+$"))` and `Command("review")` in `runtime.py`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: ask before learning rare words and add /review`.

### Task 8: Daily reminders

**Files:**
- Create: `backend/app/services/reminders.py`
- Modify: `backend/app/main.py` (FastAPI `lifespan` starts/cancels the loop only when bot config is present), `backend/app/bot/runtime.py` (expose bot)
- Test: `backend/tests/test_reminders.py`

**Interfaces:**
- Consumes: Task 4 `day_window`, Task 5 `build_summary`.
- Produces:
  - `should_send(settings: AppSettings, now_local: datetime, reviewed_today: bool, due_total: int, today_local: date) -> bool` — pure: hour reached, `last_reminder_on != today_local`, not reviewed today, due_total > 0, backoff: `ignored_reminders >= 7` → False; `>= 3` → only on days where `(today_local.toordinal() % 2 == 0)`.
  - `REMINDER_TEMPLATES: tuple[str, ...]` — 12 Russian templates with `{cards}` and `{minutes}`; none mention streaks or guilt.
  - `build_reminder_text(summary: ReviewSummary, anchor: str | None, warmup: tuple[str, str] | None, template_index: int, weekly: str | None) -> str` — warmup = (masked chunk, translation); anchor prepended as `"{anchor} — "`; Monday weekly block appended.
  - `async def send_reminder_if_due(session_factory, bot, now: datetime) -> bool` — updates `last_reminder_on`; increments `ignored_reminders` when yesterday's reminder was sent and no review followed; resets to 0 when a review happened since the last reminder. Inline keyboard: web_app button "Повторить" → `?view=review`.
  - `async def run_reminder_loop(session_factory, bot, interval_seconds: int = 300) -> None` — `# ponytail: single uvicorn worker; use an atomic DB claim if workers > 1`.

- [ ] **Step 1: Failing tests:** `test_not_before_hour`, `test_not_twice_same_day`, `test_not_when_reviewed_today`, `test_not_when_nothing_due`, `test_backoff_every_other_day_after_three_ignored`, `test_paused_after_seven_ignored`, `test_text_has_counts_and_no_streak_word` (no "серия"/"streak"), `test_monday_includes_weekly_block`, `test_send_if_due_updates_last_reminder_on` (fake bot records one call; second call same day → no send).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** run → PASS; also `uv run pytest -q` whole suite (lifespan must not start the loop in tests: start only when `settings.telegram_bot_token` is set and env `DISABLE_REMINDERS` is not "1"; conftest sets `DISABLE_REMINDERS=1`).
- [ ] **Step 5:** Commit `feat: add daily review reminder with backoff`.

### Task 9: Chunk backfill for existing cards

**Files:**
- Create: `backend/app/services/chunks_prompt.py`, `backend/app/scripts/backfill_chunks.py`
- Modify: `backend/app/clients/openrouter.py`, `backend/app/schemas/llm.py`
- Test: `backend/tests/test_backfill_chunks.py`

**Interfaces:**
- Produces:
  - `class ChunksResponse(BaseModel)`: `chunks: list[CardChunk]` (max 5), `example: str` (English, non-empty); `parse_chunks_response(payload) -> ChunksResponse`.
  - `OpenRouterClient.generate_chunks(canonical_text: str, translation_variants: list[str], examples: list[str]) -> ChunksResponse`.
  - `backfill_chunks(session: Session, client: OpenRouterClient, *, limit: int) -> tuple[int, int]` (updated, failed) — cards with `chunks_json == []`, oldest first; sets `chunks_json` and `examples_json = [example]`; canonical text, translations, IPA untouched; commit per card; `OpenRouterError` → rollback, count failed, continue.
  - CLI: `python -m app.scripts.backfill_chunks --limit 50`.

- [ ] **Step 1: Failing tests:** `test_backfill_sets_chunks_and_single_example` (stub client), `test_backfill_keeps_translations`, `test_backfill_continues_after_llm_error`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: add one-off chunk backfill command`.

### Task 10: Anki deck import

**Files:**
- Modify: `backend/app/clients/anki_connect.py` (`find_notes(query) -> list[int]`, `notes_info(ids) -> list[dict]`, `cards_info(ids) -> list[dict]`, `reviews_of_cards(card_ids) -> dict[str, list[dict]]` = action `getReviewsOfCards`), `backend/app/clients/backend_sync_api.py` (`import_note(item: dict) -> dict`), `backend/app/api/anki.py`, `backend/app/api/schemas.py`
- Create: `backend/app/services/anki_import.py`, `backend/app/scripts/import_anki.py`
- Test: `backend/tests/test_anki_import.py`

**Interfaces:**
- Produces:
  - `AnkiImportRequest` (pydantic): `word: str, translation: str, anki_note_id: int, backend_card_id: int | None, suspended: bool, card_type: int (0 new,1 learn,2 review,3 relearn), interval_days: int, ease: float, last_review_at: datetime | None, reps: int, lapses: int`.
  - `POST /api/anki/import` (bearer) → `{"status": "linked"|"created"|"rejected"|"upstream_error", "card_id": int|null}`.
  - `fsrs_card_from_anki(item: AnkiImportRequest, card_id: int, now: datetime) -> fsrs.Card | None` — type 0 → None; 1/3 → Learning/Relearning step 0 due now; 2 → Review with `stability=max(interval_days, 1)`, `difficulty=clamp(5 + (2.5 − ease) × 4, 1, 10)`, `last_review=last_review_at or now − interval`, `due = last_review + interval_days`.
  - `import_anki_note(session, client, item, now) -> tuple[str, Card | None]` — card by `backend_card_id`, else by `canonical_text_normalized == normalize_canonical_text(word)`, else `apply_source_text(word)`; on success set SRS columns, `srs_reps/lapses`, `anki_note_id`, `anki_sync_status = SYNCED`, `is_learning = not suspended`; if created and `translation` (HTML stripped) not in variants, prepend it (keep max 3).
  - Script `python -m app.scripts.import_anki [--dry-run]`: notes in `deck:"English::Inbox"`, map `avb-card-<id>` tag → `backend_card_id`, `cardsInfo` fields `type`, `queue == -1` → suspended, `interval`, `factor/1000`, `reps`, `lapses`; `getReviewsOfCards` latest `id` (ms) → `last_review_at`; prints counts per status.

- [ ] **Step 1: Failing tests:** `test_fsrs_card_from_anki_review_state` (interval 20, ease 2.5 → stability 20, difficulty 5, due = last_review + 20d), `test_new_anki_card_has_no_srs_state`, `test_import_links_existing_by_tag`, `test_import_creates_card_via_pipeline` (stub client), `test_import_marks_card_synced_with_note_id`, `test_suspended_note_not_learning`, `test_import_endpoint_requires_token`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat: import Anki deck with approximate FSRS state`.

### Task 11: Docs and wiring

**Files:** `AGENTS.md` (data model, LLM contract `chunks`, API list, workflow steps 14–15 → `is_learning`, reminders, scripts), `backend/README.md` (backfill/import commands), `Makefile` (`import-anki`, `backfill-chunks` targets), `docs/superpowers/specs/2026-10-17-srs-review-design.md` (Anki import: due = last review + interval).

- [ ] **Step 1:** Update docs to match code; no code changes.
- [ ] **Step 2:** Full gates: backend `uv run pytest -q && uv run ruff check`; frontend `npx tsc --noEmit && npm run test -- --run && npm run build`.
- [ ] **Step 3:** Commit `docs: describe SRS review backend`.

## Deployment notes (for the PR description)

- External nginx must allow `/anki/api/review` and `/anki/api/settings` like `/anki/api/cards` (site.conf lives outside the repo).
- After deploy: `docker compose exec app python -m app.scripts.backfill_chunks --limit 500`, then locally `make import-anki` with Anki open.
