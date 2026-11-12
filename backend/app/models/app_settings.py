from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
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
    last_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ignored_reminders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # The latest reminder of each kind; a new one deletes it so only one stays in the chat.
    reminder_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speaking_reminder_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Speaking practice: today's prompt and its reminder state (see speaking.py).
    speaking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Today's SpeakingTopic as JSON.
    speaking_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaking_prompt_words_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    speaking_prompt_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    speaking_reminder_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    speaking_next_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    speaking_ignored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
