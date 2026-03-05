.PHONY: backend-dev frontend-dev backend-test frontend-test test build-frontend sync-anki docker-build docker-up docker-down smoke-api

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev

backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && npm run test -- --run

test: backend-test frontend-test

build-frontend:
	cd frontend && npm run build

sync-anki:
	cd backend && uv run python -m app.scripts.sync_anki

docker-build:
	docker build -t anki-vocab-bot:local .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

smoke-api:
	curl --fail --silent http://127.0.0.1/api/health
