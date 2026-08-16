"""Add versioned snapshot risk/confidence scores.

Revision ID: 20260816_0004
Revises: 20260816_0003
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260816_0004"
down_revision = "20260816_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_snapshot_scores",
        sa.Column("score_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("methodology_version", sa.String(length=64), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("confidence_label", sa.String(length=32), nullable=False),
        sa.Column("confidence_contributions", sa.JSON(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_label", sa.String(length=32), nullable=False),
        sa.Column("risk_contributions", sa.JSON(), nullable=False),
        sa.Column("unavailable_factors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["strategy_snapshots.snapshot_id"],
            name=op.f("fk_strategy_snapshot_scores_snapshot_id_strategy_snapshots"),
        ),
        sa.PrimaryKeyConstraint("score_id", name=op.f("pk_strategy_snapshot_scores")),
        sa.UniqueConstraint(
            "snapshot_id",
            "methodology_version",
            name="uq_strategy_snapshot_scores_snapshot_id",
        ),
    )
    op.create_index(
        op.f("ix_strategy_snapshot_scores_methodology_version"),
        "strategy_snapshot_scores",
        ["methodology_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_snapshot_scores_scored_at"),
        "strategy_snapshot_scores",
        ["scored_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_snapshot_scores_snapshot_id"),
        "strategy_snapshot_scores",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_snapshot_scores_strategy_id"),
        "strategy_snapshot_scores",
        ["strategy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_strategy_snapshot_scores_strategy_id"), table_name="strategy_snapshot_scores")
    op.drop_index(op.f("ix_strategy_snapshot_scores_snapshot_id"), table_name="strategy_snapshot_scores")
    op.drop_index(op.f("ix_strategy_snapshot_scores_scored_at"), table_name="strategy_snapshot_scores")
    op.drop_index(op.f("ix_strategy_snapshot_scores_methodology_version"), table_name="strategy_snapshot_scores")
    op.drop_table("strategy_snapshot_scores")
