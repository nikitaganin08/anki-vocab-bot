from pathlib import Path

import pytest

from app.core.config import Settings


def test_default_database_url_points_to_repo_data_directory() -> None:
    settings = Settings()

    assert settings.normalized_database_url.startswith("sqlite:///")
    assert settings.database_path == Path(__file__).resolve().parents[1] / "data" / "app.db"


def test_validate_webhook_config_passes_with_required_values() -> None:
    settings = Settings(
        TELEGRAM_WEBHOOK_URL="https://bot.example.com/telegram/webhook",
        TELEGRAM_WEBHOOK_SECRET="secret",
    )

    settings.validate_webhook_config()


def test_validate_webhook_config_raises_if_missing_values() -> None:
    settings = Settings(TELEGRAM_WEBHOOK_URL="")

    with pytest.raises(ValueError, match="Missing required webhook environment variables"):
        settings.validate_webhook_config()
