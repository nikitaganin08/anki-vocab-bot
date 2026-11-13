from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import sqlalchemy as sa

from alembic import op

revision = "20261113_0012"
down_revision = "20261113_0011"
branch_labels = None
depends_on = None

# Past goals are unknown (what was due is not stored). Backfill: a day with 5+ answers counts as
# closed, the same bar as the streak and the old heatmap's full cell.
FULL_DAY_ANSWERS = 5


def upgrade() -> None:
    table = op.create_table(
        "daily_progress",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("review_goal_met", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    bind = op.get_bind()
    zone = bind.execute(sa.text("SELECT timezone FROM app_settings WHERE id = 1")).scalar()
    tz = ZoneInfo(zone or "Europe/Moscow")
    answers: Counter = Counter()
    for (reviewed_at,) in bind.execute(sa.text("SELECT reviewed_at FROM review_logs")):
        moment = (
            reviewed_at
            if isinstance(reviewed_at, datetime)
            else datetime.fromisoformat(reviewed_at)
        )
        answers[moment.replace(tzinfo=moment.tzinfo or UTC).astimezone(tz).date()] += 1
    rows = [
        {"day": day, "review_goal_met": True} for day, n in answers.items() if n >= FULL_DAY_ANSWERS
    ]
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_table("daily_progress")
