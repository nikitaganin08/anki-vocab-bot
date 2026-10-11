from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261007_0004"
down_revision = "20260916_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(sa.Column("anki_sync_error", sa.Text(), nullable=True))
        batch_op.drop_column("word_family_backfilled")

    # Keep the latest failure message for cards that are still failing.
    op.execute(
        """
        UPDATE cards SET anki_sync_error = (
            SELECT error_message FROM anki_sync_attempts
            WHERE anki_sync_attempts.card_id = cards.id AND status = 'failed'
            ORDER BY anki_sync_attempts.id DESC LIMIT 1
        )
        WHERE anki_sync_status = 'failed'
        """
    )
    op.drop_index("ix_anki_sync_attempts_card_id", table_name="anki_sync_attempts")
    op.drop_table("anki_sync_attempts")


def downgrade() -> None:
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
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(
            sa.Column("word_family_backfilled", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.drop_column("anki_sync_error")
