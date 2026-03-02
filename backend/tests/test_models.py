from app.db.base import Base
from app.models.anki_sync_attempt import AnkiSyncAttempt
from app.models.card import Card


def test_phase_one_metadata_registers_core_tables() -> None:
    assert Card.__tablename__ == "cards"
    assert AnkiSyncAttempt.__tablename__ == "anki_sync_attempts"
    assert "cards" in Base.metadata.tables
    assert "anki_sync_attempts" in Base.metadata.tables
