# Phase 4 - FastAPI API

## Objective
Implement backend JSON APIs for admin UI and Anki sync, including auth and stats.

## Tasks
Status is tracked in `bd`; the list below is reference-only.

- 4.1 Build FastAPI app entry point and router wiring.
- 4.2 Add DB session dependency and request-scoped session lifecycle.
- 4.3 Implement `GET /api/health`.
- 4.4 Implement `GET /api/cards` with pagination and filters.
- 4.5 Implement `GET /api/cards/{card_id}`.
- 4.6 Implement `GET /api/stats` (totals, queue counters, optional entry-type split).
- 4.7 Implement bearer-token auth dependency for `/api/anki/*`.
- 4.8 Implement `GET /api/anki/pending?limit=50`.
- 4.9 Implement `POST /api/anki/ack` (set status `synced`, store `anki_note_id`).
- 4.10 Implement `POST /api/anki/fail` (set status `failed`, log in `anki_sync_attempts`).
- 4.11 Serve built frontend assets under `/admin/*`.
- 4.12 Add API tests for happy path, auth checks, and key validation errors.
- 4.13 Add SPA fallback for `/admin/*` deep links by serving the frontend `index.html` on client-side routes.

## Deliverables
- Stable read API for admin frontend.
- Stable sync API for local Anki helper.

## Exit Criteria
- All API endpoints return contract-compatible JSON.
- Unauthorized access to `/api/anki/*` is rejected.
