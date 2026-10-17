from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_telegram_webapp_user
from app.api.schemas import AppSettingsPayload
from app.db.session import get_session
from app.services.app_settings import get_app_settings

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=AppSettingsPayload)
def read_settings(session: SessionDep) -> AppSettingsPayload:
    return AppSettingsPayload.model_validate(get_app_settings(session))


@router.put("", response_model=AppSettingsPayload)
def update_settings(body: AppSettingsPayload, session: SessionDep) -> AppSettingsPayload:
    settings = get_app_settings(session)
    for field, value in body.model_dump().items():
        setattr(settings, field, value)
    session.commit()
    return AppSettingsPayload.model_validate(settings)
