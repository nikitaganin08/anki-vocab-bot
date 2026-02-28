from pathlib import Path

from app.core.config import Settings


def test_default_database_url_points_to_repo_data_directory() -> None:
    settings = Settings()

    assert settings.normalized_database_url.startswith("sqlite:///")
    assert settings.database_path == Path(__file__).resolve().parents[1] / "data" / "app.db"
