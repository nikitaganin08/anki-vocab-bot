from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.telegram_webapp_auth import TelegramWebAppUser, parse_and_validate_init_data
from app.clients.openrouter import OpenRouterClient
from app.core.config import get_settings
from app.services.card_service import CardGenerator

_bearer = HTTPBearer()


def require_anki_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),  # noqa: B008
) -> None:
    settings = get_settings()
    if credentials.credentials != settings.anki_sync_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


def get_card_generator() -> CardGenerator:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not configured",
        )

    return OpenRouterClient(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
    )


def require_telegram_webapp_user(
    telegram_init_data: Annotated[
        str | None,
        Header(alias="X-Telegram-Init-Data"),
    ] = None,
) -> TelegramWebAppUser:
    if not telegram_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Telegram init data",
        )

    settings = get_settings()
    if not settings.telegram_bot_token or settings.telegram_allowed_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Web App auth is not configured",
        )

    return parse_and_validate_init_data(
        telegram_init_data,
        bot_token=settings.telegram_bot_token,
        allowed_user_id=settings.telegram_allowed_user_id,
    )
