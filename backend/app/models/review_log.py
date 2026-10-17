from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewLogEntry(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    auto_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    overridden: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prompt_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_index: Mapped[int] = mapped_column(Integer, nullable=False)
    typed_answer: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    retrievability: Mapped[float | None] = mapped_column(Float, nullable=True)
    card_before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_before: Mapped[str | None] = mapped_column(String(32), nullable=True)
