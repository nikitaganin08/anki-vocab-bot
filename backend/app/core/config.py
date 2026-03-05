from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = REPO_ROOT / "backend" / "data" / "app.db"


def default_database_url() -> str:
    return f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


class Settings(BaseSettings):
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_id: int | None = Field(default=None, alias="TELEGRAM_ALLOWED_USER_ID")
    telegram_webhook_url: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_SECRET")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    anki_sync_token: str | None = Field(default=None, alias="ANKI_SYNC_TOKEN")
    backend_api_base_url: str = Field(
        default="http://127.0.0.1:8000",
        alias="BACKEND_API_BASE_URL",
    )
    anki_connect_url: str = Field(
        default="http://127.0.0.1:8765",
        alias="ANKI_CONNECT_URL",
    )
    anki_sync_batch_limit: int = Field(default=50, alias="ANKI_SYNC_BATCH_LIMIT")
    anki_sync_http_timeout_seconds: float = Field(
        default=15.0,
        alias="ANKI_SYNC_HTTP_TIMEOUT_SECONDS",
    )
    database_url: str = Field(default_factory=default_database_url, alias="DATABASE_URL")
    llm_model: str = Field(default="google/gemini-2.5-flash-lite", alias="LLM_MODEL")

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(REPO_ROOT / "backend" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def normalized_database_url(self) -> str:
        if not self.database_url.startswith("sqlite:///"):
            return self.database_url

        raw_path = Path(self.database_url.removeprefix("sqlite:///"))
        if not raw_path.is_absolute():
            raw_path = REPO_ROOT / raw_path

        return f"sqlite:///{raw_path.resolve().as_posix()}"

    @property
    def database_path(self) -> Path | None:
        if not self.normalized_database_url.startswith("sqlite:///"):
            return None

        return Path(self.normalized_database_url.removeprefix("sqlite:///"))

    def validate_runtime_config(self) -> None:
        required_fields = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_ALLOWED_USER_ID": self.telegram_allowed_user_id,
            "OPENROUTER_API_KEY": self.openrouter_api_key,
            "ANKI_SYNC_TOKEN": self.anki_sync_token,
        }
        missing = [name for name, value in required_fields.items() if value in (None, "")]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required runtime environment variables: {joined}")

    def validate_webhook_config(self) -> None:
        required_fields = {
            "TELEGRAM_WEBHOOK_URL": self.telegram_webhook_url,
            "TELEGRAM_WEBHOOK_SECRET": self.telegram_webhook_secret,
        }
        missing = [name for name, value in required_fields.items() if value in (None, "")]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required webhook environment variables: {joined}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
