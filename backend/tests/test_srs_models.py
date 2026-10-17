from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings

from .conftest import make_card

ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"


def test_get_app_settings_creates_defaults(session: Session) -> None:
    settings = get_app_settings(session)

    assert settings.new_per_day == 5
    assert settings.reviews_per_day == 50
    assert settings.learn_threshold == 3
    assert settings.timezone == "Europe/Moscow"
    assert get_app_settings(session).id == settings.id


def test_review_log_cascade_on_card_delete(session: Session) -> None:
    card = make_card()
    session.add(card)
    session.commit()
    session.add(
        ReviewLogEntry(
            card_id=card.id,
            reviewed_at=datetime.now(UTC),
            rating=3,
            auto_rating=3,
            overridden=False,
            prompt_kind="chunk",
            prompt_index=0,
            typed_answer="take off",
            verdict="correct",
            hint_used=False,
            response_ms=1500,
        )
    )
    session.commit()

    session.delete(card)
    session.commit()

    assert session.scalar(sa.select(sa.func.count()).select_from(ReviewLogEntry)) == 0


def test_migration_upgrade_renames_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    engine = sa.create_engine(db_url)
    try:
        command.upgrade(config, "20261007_0004")
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO cards (source_text, source_language, entry_type, canonical_text,"
                    " canonical_text_normalized, translation_variants_json, word_family_json,"
                    " explanation, examples_json, frequency, eligible_for_anki, llm_model)"
                    " VALUES ('take off', 'en', 'phrasal_verb', 'take off', 'take off',"
                    " '[\"взлетать\"]', '[]', 'To leave the ground.', '[\"It took off.\"]',"
                    " 5, 1, 'test-model')"
                )
            )

        command.upgrade(config, "head")

        inspector = sa.inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("cards")}
        assert {"is_learning", "chunks_json", "srs_due_at"} <= columns
        assert "eligible_for_anki" not in columns
        assert {"review_logs", "app_settings"} <= set(inspector.get_table_names())
        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT is_learning, chunks_json FROM cards")).one()
        assert row == (1, "[]")
    finally:
        engine.dispose()
        get_settings.cache_clear()
