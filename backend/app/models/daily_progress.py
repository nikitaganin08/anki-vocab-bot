from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyProgress(Base):
    """A study day whose review goal was closed (nothing due or new left after an answer).

    Kept per day because past goals cannot be rebuilt from the logs: what was due back then is
    not stored. Only closed days get a row.
    """

    __tablename__ = "daily_progress"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    review_goal_met: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
