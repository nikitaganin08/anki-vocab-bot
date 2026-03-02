from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_bearer = HTTPBearer()


def require_anki_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),  # noqa: B008
) -> None:
    settings = get_settings()
    if credentials.credentials != settings.anki_sync_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
