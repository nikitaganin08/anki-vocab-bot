from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261113_0011"
down_revision = "20261113_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("speaking_sessions") as batch_op:
        batch_op.add_column(sa.Column("telegram_message_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(sa.Column("speaking_weekly_on", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("speaking_weekly_on")
    with op.batch_alter_table("speaking_sessions") as batch_op:
        batch_op.drop_column("telegram_message_id")
