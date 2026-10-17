from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import is_tts_enabled, require_telegram_webapp_user
from app.api.schemas import AppSettingsPayload, AppSettingsResponse
from app.db.session import get_session
from app.models.app_settings import AppSettings
from app.services.app_settings import get_app_settings

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]
TtsEnabledDep = Annotated[bool, Depends(is_tts_enabled)]


def _response(settings: AppSettings, tts_enabled: bool) -> AppSettingsResponse:
    payload = AppSettingsPayload.model_validate(settings).model_dump()
    return AppSettingsResponse(**payload, tts_enabled=tts_enabled)


@router.get("", response_model=AppSettingsResponse)
def read_settings(session: SessionDep, tts_enabled: TtsEnabledDep) -> AppSettingsResponse:
    return _response(get_app_settings(session), tts_enabled)


# tts_enabled in the body is ignored: AppSettingsPayload has no such field.
@router.put("", response_model=AppSettingsResponse)
def update_settings(
    body: AppSettingsPayload, session: SessionDep, tts_enabled: TtsEnabledDep
) -> AppSettingsResponse:
    settings = get_app_settings(session)
    for field, value in body.model_dump().items():
        setattr(settings, field, value)
    session.commit()
    return _response(settings, tts_enabled)
