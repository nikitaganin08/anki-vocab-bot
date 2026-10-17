from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261017_0005"
down_revision = "20261007_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.alter_column("eligible_for_anki", new_column_name="is_learning")
        batch_op.add_column(
            sa.Column("chunks_json", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("srs_card_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("srs_due_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("srs_state", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("srs_reps", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("srs_lapses", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index("ix_cards_srs_due_at", ["srs_due_at"])

    op.create_table(
        "review_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "card_id",
            sa.Integer(),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("auto_rating", sa.Integer(), nullable=False),
        sa.Column("overridden", sa.Boolean(), nullable=False),
        sa.Column("prompt_kind", sa.String(length=32), nullable=False),
        sa.Column("prompt_index", sa.Integer(), nullable=False),
        sa.Column("typed_answer", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("hint_used", sa.Boolean(), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=False),
        sa.Column("retrievability", sa.Float(), nullable=True),
        sa.Column("card_before_json", sa.Text(), nullable=True),
        sa.Column("state_before", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_review_logs_card_id", "review_logs", ["card_id"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("reminder_hour", sa.Integer(), nullable=False),
        sa.Column("reminder_anchor", sa.String(length=255), nullable=True),
        sa.Column("new_per_day", sa.Integer(), nullable=False),
        sa.Column("reviews_per_day", sa.Integer(), nullable=False),
        sa.Column("desired_retention", sa.Float(), nullable=False),
        sa.Column("learn_threshold", sa.Integer(), nullable=False),
        sa.Column("last_reminder_on", sa.Date(), nullable=True),
        sa.Column("ignored_reminders", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_review_logs_card_id", table_name="review_logs")
    op.drop_table("review_logs")
    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_index("ix_cards_srs_due_at")
        batch_op.drop_column("srs_lapses")
        batch_op.drop_column("srs_reps")
        batch_op.drop_column("srs_state")
        batch_op.drop_column("srs_due_at")
        batch_op.drop_column("srs_card_json")
        batch_op.drop_column("chunks_json")
        batch_op.alter_column("is_learning", new_column_name="eligible_for_anki")
