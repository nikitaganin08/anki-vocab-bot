from __future__ import annotations

import os
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.api.deps as deps_mod
from app.api.deps import require_anki_token
from app.db.base import Base
from app.db.session import enable_sqlite_foreign_keys, get_session
from app.main import app
from app.models.card import AnkiSyncStatus, Card

from .telegram_webapp_test_helpers import build_telegram_init_data

# Keep the FastAPI lifespan from starting the reminder loop in tests.
os.environ["DISABLE_REMINDERS"] = "1"

TELEGRAM_BOT_TOKEN = "telegram-bot-token"
TELEGRAM_ALLOWED_USER_ID = 42


@dataclass
class TelegramSettingsStub:
    telegram_bot_token: str = TELEGRAM_BOT_TOKEN
    telegram_allowed_user_id: int = TELEGRAM_ALLOWED_USER_ID
    anki_sync_token: str | None = "sync-token"


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _session_override(session: Session):  # type: ignore[no-untyped-def]
    """Return a FastAPI dependency that always yields the given session."""

    def _override() -> Generator[Session, None, None]:
        yield session

    return _override


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_session] = _session_override(session)
    original_get_settings = deps_mod.get_settings
    deps_mod.get_settings = lambda: TelegramSettingsStub()
    try:
        yield TestClient(app)
    finally:
        deps_mod.get_settings = original_get_settings
        app.dependency_overrides.clear()


@pytest.fixture
def authed_client(session: Session) -> Generator[TestClient, None, None]:
    """Client with both session and anki auth overridden."""
    app.dependency_overrides[get_session] = _session_override(session)
    app.dependency_overrides[require_anki_token] = lambda: None
    original_get_settings = deps_mod.get_settings
    deps_mod.get_settings = lambda: TelegramSettingsStub()
    try:
        yield TestClient(app)
    finally:
        deps_mod.get_settings = original_get_settings
        app.dependency_overrides.clear()


def telegram_headers() -> dict[str, str]:
    return {
        "X-Telegram-Init-Data": build_telegram_init_data(
            bot_token=TELEGRAM_BOT_TOKEN,
            user_id=TELEGRAM_ALLOWED_USER_ID,
        )
    }


def mobile_headers() -> dict[str, str]:
    return {"Authorization": "Bearer sync-token"}


def make_card(**overrides: object) -> Card:
    defaults: dict[str, object] = dict(
        source_text="take off",
        source_language="en",
        entry_type="phrasal_verb",
        canonical_text="take off",
        canonical_text_normalized="take off",
        transcription="/teɪk ɒf/",
        translation_variants_json=["взлетать", "снимать", "резко начинаться"],
        explanation="To leave the ground, or to remove something.",
        examples_json=[
            "The plane took off at noon.",
            "Take off your shoes, please.",
            "Her career really took off last year.",
        ],
        frequency=5,
        frequency_note="Very common.",
        is_learning=True,
        anki_sync_status=AnkiSyncStatus.PENDING,
        llm_model="test-model",
    )
    defaults.update(overrides)
    return Card(**defaults)  # type: ignore[arg-type]
