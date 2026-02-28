from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260228_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_text", sa.String(length=255), nullable=False),
        sa.Column(
            "source_language",
            sa.Enum("ru", "en", name="sourcelanguage", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "entry_type",
            sa.Enum(
                "word",
                "phrasal_verb",
                "collocation",
                "idiom",
                "expression",
                name="entrytype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("canonical_text", sa.String(length=255), nullable=False),
        sa.Column("canonical_text_normalized", sa.String(length=255), nullable=False),
        sa.Column("transcription", sa.String(length=255), nullable=True),
        sa.Column("translation_variants_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("examples_json", sa.JSON(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("frequency_note", sa.Text(), nullable=True),
        sa.Column("eligible_for_anki", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "anki_sync_status",
            sa.Enum("pending", "synced", "failed", name="ankisyncstatus", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("anki_note_id", sa.Integer(), nullable=True),
        sa.Column("llm_model", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("canonical_text_normalized", name="uq_cards_canonical_text_normalized"),
    )
    op.create_index("ix_cards_source_text", "cards", ["source_text"])
    op.create_index("ix_cards_anki_sync_status", "cards", ["anki_sync_status"])

    op.create_table(
        "anki_sync_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "card_id",
            sa.Integer(),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_anki_sync_attempts_card_id", "anki_sync_attempts", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_anki_sync_attempts_card_id", table_name="anki_sync_attempts")
    op.drop_table("anki_sync_attempts")
    op.drop_index("ix_cards_anki_sync_status", table_name="cards")
    op.drop_index("ix_cards_source_text", table_name="cards")
    sa.Enum(name="ankisyncstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="entrytype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sourcelanguage").drop(op.get_bind(), checkfirst=True)
    op.drop_table("cards")
