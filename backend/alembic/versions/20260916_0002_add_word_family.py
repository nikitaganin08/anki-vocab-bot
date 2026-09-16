from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260916_0002"
down_revision = "20260228_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(sa.Column("word_family_json", sa.JSON(), nullable=True))

    cards = sa.table("cards", sa.column("word_family_json", sa.JSON()))
    op.execute(cards.update().values(word_family_json=[]))

    with op.batch_alter_table("cards") as batch_op:
        batch_op.alter_column("word_family_json", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_column("word_family_json")
