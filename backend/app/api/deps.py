from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
