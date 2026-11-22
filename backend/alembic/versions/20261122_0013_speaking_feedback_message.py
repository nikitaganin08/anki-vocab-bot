from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261122_0013"
down_revision = "20261113_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("speaking_sessions") as batch:
        batch.add_column(sa.Column("feedback_message_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("speaking_sessions") as batch:
        batch.drop_column("feedback_message_id")
