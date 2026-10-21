from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.api.telegram_webapp_auth import parse_and_validate_init_data
from app.clients.openrouter import OpenRouterClient
from app.core.config import get_settings
from app.services.pronunciation import GoogleTtsClient, TtsClient, YandexTtsClient


def get_openrouter_client() -> OpenRouterClient:
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


def is_tts_enabled() -> bool:
    settings = get_settings()
    return bool(settings.yandex_tts_api_key or settings.google_tts_api_key)


def get_tts_client() -> TtsClient:
    # Yandex wins when both keys are set (Google needs billing that is unavailable in Russia).
    settings = get_settings()
    if settings.yandex_tts_api_key:
        return YandexTtsClient(api_key=settings.yandex_tts_api_key, voice=settings.yandex_tts_voice)
    if settings.google_tts_api_key:
        return GoogleTtsClient(api_key=settings.google_tts_api_key, voice=settings.google_tts_voice)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Pronunciation is not configured",
    )


def require_telegram_webapp_user(
    telegram_init_data: Annotated[
        str | None,
        Header(alias="X-Telegram-Init-Data"),
    ] = None,
) -> int:
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


def require_clip_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """Bearer token for the browser extension; the Mini App auth cannot be used there."""
    token = get_settings().clip_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Clipping is not configured"
        )
    supplied = (authorization or "").removeprefix("Bearer ")
    if not hmac.compare_digest(supplied.encode(), token.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
