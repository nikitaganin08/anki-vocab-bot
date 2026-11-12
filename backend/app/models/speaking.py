from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpeakingSession(Base):
    """One analysed voice message or video note. The media itself is never stored."""

    __tablename__ = "speaking_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # voice, video_note
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{card_id, word, used}]; card_id is a plain number, the card may be deleted later.
    words_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    filler_count: Mapped[int] = mapped_column(Integer, nullable=False)
    natural_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_time: Mapped[str] = mapped_column(Text, nullable=False)
    focus_check: Mapped[str | None] = mapped_column(String(16), nullable=True)
    llm_model: Mapped[str] = mapped_column(String(255), nullable=False)
    # The owner's message in the chat (a reference, not the file): the weekly summary forwards it.
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SpeakingIssue(Base):
    """One fix the model found in a recording, kept for counting recurring mistakes."""

    __tablename__ = "speaking_issues"
    __table_args__ = (Index("ix_speaking_issues_session_category", "session_id", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("speaking_sessions.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    wrong: Mapped[str | None] = mapped_column(Text, nullable=True)
    right: Mapped[str | None] = mapped_column(Text, nullable=True)
    why: Mapped[str] = mapped_column(Text, nullable=False)
