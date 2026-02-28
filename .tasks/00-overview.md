# anki-vocab-bot Implementation Plan

## Goal
Build the full MVP described in `AGENTS.md`: Telegram vocabulary bot + FastAPI backend + read-only React admin UI + Anki sync helper.

## Execution Rules
- Build in phases to keep dependencies clear.
- Every phase ends with tests for the scope delivered.
- Keep backend as the single source of truth for cards and sync state.
- Track execution in Beads (`bd`) as epics + child tasks.
- Treat `.tasks/` as a static planning reference, not a live status tracker.

## Tracking
- `Beads` (`bd`) is the canonical source of truth for task status, dependencies, and prioritization.
- `.tasks/` captures the agreed phase scope only and should not be updated to reflect runtime progress.

## Phases
1. Scaffolding and Foundation
2. LLM Integration and Card Service
3. Telegram Bot
4. FastAPI API
5. React Frontend
6. Anki Sync and Deployment

## Cross-Phase Constraints
- Input languages: `ru` and `en`
- Input length: `1..8` tokens
- Two-step dedup: `source_text` before LLM, `canonical_text_normalized` after LLM
- Anki eligibility: `frequency > 2`
- Rate limit: max 5 requests per minute
- Anki statuses: `pending`, `synced`, `failed`

## Definition of Done
- All phase tasks completed.
- Backend unit tests and frontend component tests passing.
- Frontend build is served under `/admin/*` from backend.
- Anki sync helper performs pending -> ack/fail transitions.
