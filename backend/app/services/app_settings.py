from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings


def get_app_settings(session: Session) -> AppSettings:
    settings = session.get(AppSettings, 1)
    if settings is None:
        settings = AppSettings(id=1)
        session.add(settings)
        session.commit()
    return settings
