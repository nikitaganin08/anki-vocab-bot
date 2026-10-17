# SRS Review Mini App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mini App screens for daily review (dashboard, intro, typed question, back side, round end, welcome back, settings, cards toggle) plus two small backend tweaks for the approved designs.

**Architecture:** One React app, views switched by `?view=` and a bottom tab bar; data via TanStack Query against the review/settings API from `docs/superpowers/plans/2026-10-17-srs-backend.md`. Review session state lives in one `useReviewSession` hook; screens are presentational components.

**Tech Stack:** React 18, TypeScript, Vite, TanStack Query, Vitest + Testing Library; backend Python/FastAPI for Task 1.

**Spec:** `docs/superpowers/specs/2026-10-17-srs-review-design.md` — section "Mini App (design approved 2026-10-17)" is the source of truth for every screen's content and copy.

## Global Constraints

- Branch `feat/srs-backend` (same PR #4). Do not push, do not create branches.
- Gates: backend `uv run pytest -q && uv run ruff check` (+ `ruff format` only on changed files); frontend `npx tsc --noEmit && npm run test -- --run && npm run build`.
- No new npm dependencies. Icons: inline SVG or text, no icon font. Audio: `window.speechSynthesis` with `lang="en-US"`; guard when unavailable.
- Theme: CSS variables mapped from `Telegram.WebApp.themeParams` (`bg_color`, `text_color`, `hint_color`, `button_color`, `button_text_color`, `secondary_bg_color`) with light fallbacks; flat surfaces, no gradients/shadows; one accent button per screen. Replace the current gradient theme in `styles.css`.
- Copy: Russian, sentence case, exactly as in the spec section. No streak guilt, no red for missed days.
- Inputs: `autoComplete="off" autoCorrect="off" autoCapitalize="none" spellCheck={false}`, autofocus, Enter submits.
- Keep files focused: one component per screen under `src/review/` and `src/home/`.

## Review Focus

1. `grade` returns 409 (double tap, stale session) → client refetches the session and continues, never shows a dead screen (Task 4 test `refetches session on 409`).
2. `expected_due_at` must be echoed back as the exact `srs_due_at` string from the session (no `Date` round-trip) (Task 4 test `sends srs_due_at verbatim`).
3. Session returns zero items while `due_today > 0` was shown (limits hit between screens) → round-end/"Готово на сегодня" screen, not an empty question (Task 4 test `empty session shows done screen`).
4. Telegram opened without `themeParams` or `speechSynthesis` (desktop/web) → readable fallback colors, audio button hidden (Task 2 test `falls back without theme params`, Task 4 test `hides audio without speechSynthesis`).
5. Cyrillic typed into the answer field must be sent as-is (server converts layout) — no client-side filtering (Task 4 test `sends cyrillic answer unchanged`).

---

### Task 1: Backend tweaks for W2 and M1

**Files:** `backend/app/services/review_stats.py`, `backend/app/services/srs.py`, `backend/app/api/review.py`, `backend/app/api/schemas.py`, `backend/app/services/reminders.py`; tests in `tests/test_review_stats.py`, `tests/test_srs_service.py`, `tests/test_review_api.py`, `tests/test_reminders.py`.

**Interfaces:**
- Produces: `ReviewSummary.days_away: int | None` (whole study days since the last review log; None if never), `ReviewSummary.due_all: int` (all due learning + review cards, ignoring limits); `build_session(..., include_backlog: bool = False)` — when True the daily review cap is not applied; `GET /api/review/session?size=10&include_backlog=false`; `build_reminder_text(summary, anchor, template_index, weekly)` — the `warmup` parameter and its lookup are removed (M1).

- [ ] **Step 1:** Failing tests: `test_days_away_counts_study_days`, `test_due_all_ignores_limit` (60 due, limit 50 → `due_all == 60`), `test_session_include_backlog_ignores_cap`, `test_session_endpoint_include_backlog`, `test_reminder_text_has_no_warmup` (text contains count and minutes, no "Разминка").
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** backend gates → PASS.
- [ ] **Step 5:** Commit `feat: support welcome-back session and short reminder`.

### Task 2: App shell — theme, views, bottom tabs

**Files:** Modify `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/src/telegram.ts`, `frontend/src/App.test.tsx`; Create `frontend/src/navigation.ts`, `frontend/src/components/TabBar.tsx`.

**Interfaces:**
- Produces:
  - `type View = "home" | "review" | "cards" | "settings"`; `readView(search: string): View` (default `"home"`); `useView(): [View, (v: View) => void]` (updates `?view=` via `history.replaceState`, keeps other params).
  - `applyTelegramTheme(): void` in `telegram.ts` — sets `--tg-bg`, `--tg-text`, `--tg-hint`, `--tg-accent`, `--tg-accent-text`, `--tg-surface` on `document.documentElement` from `themeParams`, leaving CSS fallbacks when absent; `showBackButton(onClick: () => void): () => void` (returns cleanup; no-op outside Telegram).
  - `<TabBar view onChange />` — 4 tabs "Главная", "Повтор", "Слова", "Настройки"; hidden when `view === "review"`.
  - `App` renders `HomeView` (Task 3), `ReviewView` (Task 4), `CardsPage` (existing), `SettingsView` (Task 5) by view; until those exist, placeholders are fine within this task.
- [ ] **Step 1:** Failing tests: `renders tab bar with four tabs`, `switches view and updates query`, `opens review view from ?view=review without tab bar`, `falls back without theme params` (no `themeParams` → `--tg-bg` unset, app renders).
- [ ] **Step 2:** run → FAIL. **Step 3:** implement; rewrite `styles.css` tokens to the flat theme (keep existing class names used by `CardsPage` working). **Step 4:** frontend gates → PASS.
- [ ] **Step 5:** Commit `feat: add Mini App shell with tabs and Telegram theme`.

### Task 3: API client + Главная (dashboard v2 and W2)

**Files:** Modify `frontend/src/api/types.ts`, `frontend/src/api/client.ts`; Create `frontend/src/home/HomeView.tsx`, `frontend/src/home/Heatmap.tsx`, `frontend/src/home/HomeView.test.tsx`.

**Interfaces:**
- Produces in `client.ts`: `getReviewSummary(): Promise<ReviewSummary>`, `getReviewSession(opts: {size: number; includeBacklog?: boolean}): Promise<ReviewSessionItem[]>`, `checkAnswer(cardId, body: CheckRequest): Promise<CheckResponse>`, `gradeCard(cardId, body: GradeRequest): Promise<GradeResponse>` (throws `ApiError` with `status` field; add `status: number` to `ApiError`), `getSettings()`, `saveSettings(body)`, `setCardLearning(cardId, isLearning: boolean): Promise<Card>`. Types mirror backend schemas exactly (`expected_due_at: string | null`).
- `HomeView({ onStart }: { onStart: (mode: {size?: number; includeBacklog?: boolean; capCards?: number}) => void })`: normal state per spec ("Цель на сегодня", "Начать", "Быстро: 5 карточек", stats, heatmap, streak line only when ≥3, forecast, "Отложено"). W2 state when `days_away >= 3 && due_all > 0`: "С возвращением", "Как сегодня?", "5 минут" (`capCards = max(5, round(5 / (est_minutes / max(due_today + new_today, 1))))`), "Обычная сессия", `Всё сразу (${due_all})` (`includeBacklog: true`).
- [ ] **Step 1:** Failing tests: `shows goal and minutes`, `hides streak below three days`, `heatmap renders 98 cells without red`, `shows welcome back after three days away`, `all-at-once starts with includeBacklog`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** gates → PASS.
- [ ] **Step 5:** Commit `feat: add dashboard and welcome-back screen`.

### Task 4: Review flow — intro, question, back, round end

**Files:** Create `frontend/src/review/useReviewSession.ts`, `frontend/src/review/ReviewView.tsx`, `frontend/src/review/IntroCard.tsx`, `frontend/src/review/QuestionCard.tsx`, `frontend/src/review/AnswerCard.tsx`, `frontend/src/review/RoundEnd.tsx`, `frontend/src/review/speak.ts`, `frontend/src/review/ReviewView.test.tsx`.

**Interfaces:**
- Consumes: Task 3 client functions; Task 2 `showBackButton`, `useView`.
- Produces:
  - `speak(text: string): void`, `canSpeak(): boolean` (`speechSynthesis` present).
  - `useReviewSession(mode)` state machine: `loading → intro | question → answer → (next) … → roundEnd | done`; rounds of 10 fetched via `getReviewSession({size: 10, includeBacklog})`; after "Запомнил" on an intro item, insert a typed item for the same card two positions later; `capCards` stops the session after that many graded cards; on `ApiError.status === 409` from grade → refetch round; response time measured from question shown to submit.
  - `ReviewView({ mode, onExit })`: screens exactly per spec (I1, question, back, R1, "Готово на сегодня"). Back side shows interval labels formatted `"<1 м" | "N м" | "N ч" | "N д"`; auto-rated button highlighted; "Мой ответ верный" → grade 3 with `overridden: true`.
- [ ] **Step 1:** Failing tests (mock client): `intro then typed question later in round`, `check shows diff and highlights auto rating`, `grade advances to next card`, `sends srs_due_at verbatim`, `refetches session on 409`, `empty session shows done screen`, `round end shows progress to goal`, `override grades good`, `hint reveals first letter and marks hint_used`, `sends cyrillic answer unchanged`, `hides audio without speechSynthesis`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** gates → PASS.
- [ ] **Step 5:** Commit `feat: add review flow screens`.

### Task 5: Настройки (S1) and Слова toggle

**Files:** Create `frontend/src/settings/SettingsView.tsx`, `frontend/src/settings/SettingsView.test.tsx`; Modify `frontend/src/pages/CardsPage.tsx`, `frontend/src/pages/CardsPage.test.tsx`.

**Interfaces:**
- `SettingsView`: one list of fields from the spec with native inputs (`<input type="number">`, `<select>` for retention 80–95 % in steps of 1 and timezone from `Intl.supportedValuesOf("timeZone")` when available, else a short list incl. the current value); "Сохранить" calls `saveSettings`; shows server validation error text.
- `CardsPage`: replace the "Learning yes/no" text with a toggle "Учим" calling `setCardLearning` and updating the list; restyle only via shared tokens.
- [ ] **Step 1:** Failing tests: `settings loads and saves`, `settings shows validation error`, `toggle learning patches card`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** gates → PASS.
- [ ] **Step 5:** Commit `feat: add settings screen and learning toggle`.

### Task 6: Docs

**Files:** `AGENTS.md` (Telegram Web App section: views, review flow; frontend stack note on Telegram theme), `docs/superpowers/specs/2026-10-17-srs-review-design.md` only if code deviated.
- [ ] **Step 1:** Update docs. **Step 2:** full gates backend + frontend. **Step 3:** Commit `docs: describe review Mini App`.
