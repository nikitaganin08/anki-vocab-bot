from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.anki_sync_attempt import AnkiSyncAttempt


def _enum_values(enum_type: type[Enum]) -> list[str]:
    return [member.value for member in enum_type]


class SourceLanguage(str, Enum):
    RU = "ru"
    EN = "en"


class EntryType(str, Enum):
    WORD = "word"
    PHRASAL_VERB = "phrasal_verb"
    COLLOCATION = "collocation"
    IDIOM = "idiom"
    EXPRESSION = "expression"


class AnkiSyncStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_text: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_language: Mapped[SourceLanguage] = mapped_column(
        SqlEnum(SourceLanguage, native_enum=False, values_callable=_enum_values),
        nullable=False,
    )
    entry_type: Mapped[EntryType] = mapped_column(
        SqlEnum(EntryType, native_enum=False, values_callable=_enum_values),
        nullable=False,
    )
    canonical_text: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_text_normalized: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    transcription: Mapped[str | None] = mapped_column(String(255), nullable=True)
    translation_variants_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    examples_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligible_for_anki: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anki_sync_status: Mapped[AnkiSyncStatus] = mapped_column(
        SqlEnum(AnkiSyncStatus, native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=AnkiSyncStatus.PENDING,
    )
    anki_note_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_model: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sync_attempts: Mapped[list["AnkiSyncAttempt"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
