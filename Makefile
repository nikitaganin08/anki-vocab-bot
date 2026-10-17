.PHONY: backend-dev frontend-dev backend-test frontend-test test build-frontend sync-anki import-anki backfill-chunks android-apk docker-build docker-up docker-down

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

import-anki:
	cd backend && uv run python -m app.scripts.import_anki

backfill-chunks:
	cd backend && uv run python -m app.scripts.backfill_chunks

android-apk:
	cd android && ANDROID_HOME="$${ANDROID_HOME:-/opt/homebrew/share/android-sdk}" JAVA_HOME="$$(/usr/libexec/java_home -v 19 2>/dev/null || /usr/libexec/java_home -v 17 2>/dev/null || /usr/libexec/java_home -v 21 2>/dev/null || /usr/libexec/java_home)" ./gradlew :app:assembleDebug

docker-build:
	docker build -t anki-vocab-bot:local .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
