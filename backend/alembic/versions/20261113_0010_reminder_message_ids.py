from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261113_0010"
down_revision = "20261112_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(sa.Column("reminder_message_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("speaking_reminder_message_id", sa.Integer(), nullable=True))
    # speaking_prompt now holds the topic as JSON; today's rendered text would not parse.
    op.execute("UPDATE app_settings SET speaking_prompt = NULL, speaking_prompt_on = NULL")


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("speaking_reminder_message_id")
        batch_op.drop_column("reminder_message_id")
