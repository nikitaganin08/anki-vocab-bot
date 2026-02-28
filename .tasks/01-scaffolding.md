# Phase 1 - Scaffolding and Foundation

## Objective
Create a runnable monorepo skeleton with backend foundation, DB schema, migrations, and local dev commands.

## Tasks
Status is tracked in `bd`; the list below is reference-only.

- 1.1 Create root structure: `backend/`, `frontend/`, `backend/data/`.
- 1.2 Add backend project files (`backend/pyproject.toml`, package layout, tool config for ruff/pytest).
- 1.3 Implement settings module (`app/core/config.py`) with required env vars and defaults.
- 1.4 Configure database layer (`app/db/session.py`, base model, engine/session factory).
- 1.5 Implement SQLAlchemy models for `cards` and `anki_sync_attempts`.
- 1.6 Initialize Alembic and create initial migration for both tables and key indexes.
- 1.7 Add root `Makefile` targets: `backend-dev`, `frontend-dev`, `test`, `build-frontend`, `sync-anki`.
- 1.8 Add `.env.example` with all required variables from spec.
- 1.9 Set up frontend component test harness (`vitest`/`jsdom` or equivalent) and wire it into developer test commands.

## Deliverables
- Backend skeleton importable and runnable.
- DB migration applies cleanly on empty SQLite database.
- Makefile commands exist and execute expected commands.

## Exit Criteria
- `uv sync` works in `backend/`.
- `uv run alembic upgrade head` creates schema without errors.
