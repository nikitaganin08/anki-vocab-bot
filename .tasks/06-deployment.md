# Phase 6 - Anki Sync and Deployment

## Objective
Deliver local Anki synchronization flow and production-like packaging for backend + frontend.

## Tasks
Status is tracked in `bd`; the list below is reference-only.

- 6.1 Implement local sync helper script (`make sync-anki` target).
- 6.2 Build AnkiConnect client wrapper with retry/error mapping.
- 6.3 Pull pending cards from backend sync API with bearer token.
- 6.4 Map card fields to Anki `VocabularyCard` note fields:
- 6.4.1 `Word` <- `canonical_text`
- 6.4.2 `Transcription` <- `transcription`
- 6.4.3 `Translation` <- comma-joined translations
- 6.4.4 `Explanation` <- `explanation`
- 6.4.5 `Example` <- first two examples joined by newline
- 6.5 Report outcomes back via `anki/ack` and `anki/fail` endpoints.
- 6.6 Create multi-stage Dockerfile (frontend build stage, backend deps stage, runtime stage).
- 6.7 Add docker-compose for local run with persistent `backend/data` volume.
- 6.8 Finalize root Makefile and developer runbook.
- 6.9 Add smoke checks for bot flow, API flow, frontend serving, and sync cycle.
- 6.10 Define sync-cycle idempotency and retry policy for repeated `ack`/`fail`, transient AnkiConnect errors, and backend acknowledgement gaps.

## Deliverables
- End-to-end pending -> synced/failed Anki transition pipeline.
- Containerized runtime with static admin frontend served by backend.

## Exit Criteria
- `make build-frontend` and container build succeed.
- Sync helper updates statuses correctly on success and failure.
