"""Index latest snapshot lookups by strategy and calculation time.

Revision ID: 20260907_0008
Revises: 20260823_0007
Create Date: 2026-09-07
"""

from alembic import op


revision = "20260907_0008"
down_revision = "20260823_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_strategy_snapshots_strategy_calculated_created",
        "strategy_snapshots",
        ["strategy_id", "calculated_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_snapshots_strategy_calculated_created",
        table_name="strategy_snapshots",
    )
