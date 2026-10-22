from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261022_0007"
down_revision = "20261018_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(sa.Column("common_synonym", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_column("common_synonym")
