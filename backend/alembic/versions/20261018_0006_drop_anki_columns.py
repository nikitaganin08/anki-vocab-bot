from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261018_0006"
down_revision = "20261017_0005"
branch_labels = None
depends_on = None

INDEX = "ix_cards_anki_sync_status"


def upgrade() -> None:
    has_index = any(i["name"] == INDEX for i in sa.inspect(op.get_bind()).get_indexes("cards"))
    with op.batch_alter_table("cards") as batch_op:
        if has_index:
            batch_op.drop_index(INDEX)
        batch_op.drop_column("anki_sync_error")
        batch_op.drop_column("anki_note_id")
        batch_op.drop_column("anki_sync_status")


def downgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(
            sa.Column(
                "anki_sync_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(sa.Column("anki_note_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("anki_sync_error", sa.Text(), nullable=True))
        batch_op.create_index(INDEX, ["anki_sync_status"])
