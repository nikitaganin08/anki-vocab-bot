from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSettings(Base):
    """Single-row (id=1) user preferences; read via `get_app_settings`."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    reminder_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    reminder_anchor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    reviews_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    desired_retention: Mapped[float] = mapped_column(Float, nullable=False, default=0.9)
    learn_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_reminder_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ignored_reminders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
