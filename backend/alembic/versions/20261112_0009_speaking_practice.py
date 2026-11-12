from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261112_0009"
down_revision = "20261023_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speaking_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("words_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("filler_count", sa.Integer(), nullable=False),
        sa.Column("natural_version", sa.Text(), nullable=True),
        sa.Column("next_time", sa.Text(), nullable=False),
        sa.Column("focus_check", sa.String(16), nullable=True),
        sa.Column("llm_model", sa.String(255), nullable=False),
    )
    op.create_index("ix_speaking_sessions_recorded_at", "speaking_sessions", ["recorded_at"])
    op.create_table(
        "speaking_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("speaking_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("wrong", sa.Text(), nullable=True),
        sa.Column("right", sa.Text(), nullable=True),
        sa.Column("why", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_speaking_issues_session_category", "speaking_issues", ["session_id", "category"]
    )
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column("speaking_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(sa.Column("speaking_prompt", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("speaking_prompt_words_json", sa.Text(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("speaking_prompt_on", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("speaking_reminder_on", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("speaking_next_reminder_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("speaking_ignored", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        for column in (
            "speaking_ignored",
            "speaking_next_reminder_at",
            "speaking_reminder_on",
            "speaking_prompt_on",
            "speaking_prompt_words_json",
            "speaking_prompt",
            "speaking_enabled",
        ):
            batch_op.drop_column(column)
    op.drop_index("ix_speaking_issues_session_category", table_name="speaking_issues")
    op.drop_table("speaking_issues")
    op.drop_index("ix_speaking_sessions_recorded_at", table_name="speaking_sessions")
    op.drop_table("speaking_sessions")
