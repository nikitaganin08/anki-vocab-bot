from app.db.base import Base
from app.models import Card  # noqa: F401


def test_phase_one_metadata_registers_core_tables() -> None:
    assert "cards" in Base.metadata.tables
    assert "anki_sync_attempts" in Base.metadata.tables
