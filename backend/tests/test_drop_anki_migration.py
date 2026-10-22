from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"
ANKI_COLUMNS = {"anki_sync_status", "anki_note_id", "anki_sync_error"}
ANKI_INDEX = "ix_cards_anki_sync_status"

INSERT = (
    "INSERT INTO cards (source_text, source_language, entry_type, canonical_text,"
    " canonical_text_normalized, translation_variants_json, word_family_json, explanation,"
    " examples_json, frequency, is_learning, llm_model, anki_sync_status, anki_note_id,"
    " anki_sync_error) VALUES ('{word}', 'en', 'phrasal_verb', '{word}', '{word}',"
    " '[\"взлетать\"]', '[]', 'To leave the ground.', '[\"It took off.\"]', 5, {learning},"
    " 'test-model', '{status}', {note_id}, {error})"
)


def test_drop_anki_columns_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    engine = sa.create_engine(db_url)

    def columns() -> set[str]:
        return {c["name"] for c in sa.inspect(engine).get_columns("cards")}

    def indexes() -> set[str]:
        return {i["name"] for i in sa.inspect(engine).get_indexes("cards")}

    def uniques() -> list[dict]:
        return sa.inspect(engine).get_unique_constraints("cards")

    def other_data() -> list[tuple]:
        keep = ", ".join(sorted(columns() - ANKI_COLUMNS))
        with engine.connect() as conn:
            return [
                tuple(r) for r in conn.execute(sa.text(f"SELECT {keep} FROM cards ORDER BY id"))
            ]

    try:
        command.upgrade(config, "20261017_0005")
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    INSERT.format(
                        word="take off", learning=1, status="synced", note_id=77, error="'boom'"
                    )
                )
            )
            conn.execute(
                sa.text(
                    INSERT.format(
                        word="give up", learning=0, status="failed", note_id="NULL", error="NULL"
                    )
                )
            )
        assert ANKI_COLUMNS <= columns()
        assert ANKI_INDEX in indexes()
        before, other_indexes, unique = other_data(), indexes() - {ANKI_INDEX}, uniques()

        command.upgrade(config, "20261018_0006")
        assert not ANKI_COLUMNS & columns()
        assert indexes() == other_indexes
        assert other_data() == before
        assert uniques() == unique

        command.downgrade(config, "20261017_0005")
        assert ANKI_COLUMNS <= columns()
        assert indexes() == other_indexes | {ANKI_INDEX}
        assert other_data() == before
        assert uniques() == unique
        with engine.connect() as conn:
            restored = conn.execute(
                sa.text("SELECT anki_sync_status, anki_note_id, anki_sync_error FROM cards")
            ).all()
        assert restored == [("pending", None, None)] * 2

        command.upgrade(config, "20261018_0006")
        assert not ANKI_COLUMNS & columns()
        assert indexes() == other_indexes
        assert other_data() == before
        assert uniques() == unique
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_common_synonym_migration_adds_a_nullable_column(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_url = f"sqlite:///{(tmp_path / 'syn.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    engine = sa.create_engine(db_url)
    try:
        command.upgrade(config, "head")
        cols = {c["name"]: c for c in sa.inspect(engine).get_columns("cards")}
        assert cols["common_synonym"]["nullable"] is True

        command.downgrade(config, "20261018_0006")
        assert "common_synonym" not in {c["name"] for c in sa.inspect(engine).get_columns("cards")}
    finally:
        engine.dispose()
        get_settings.cache_clear()
