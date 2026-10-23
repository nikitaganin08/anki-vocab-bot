from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261023_0008"
down_revision = "20261022_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("last_reminder_at")
