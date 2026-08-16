"""Add historical strategy snapshot tables.

Revision ID: 20260816_0003
Revises: 20260815_0002
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260816_0003"
down_revision = "20260815_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("adapter_contract_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intended_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intended_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reporting_currency", sa.String(length=32), nullable=False),
        sa.Column("capital_metrics", sa.JSON(), nullable=False),
        sa.Column("earnings_cost_metrics", sa.JSON(), nullable=False),
        sa.Column("roi_outputs", sa.JSON(), nullable=False),
        sa.Column("adapter_derived_values", sa.JSON(), nullable=False),
        sa.Column("uncertainty_ranges", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("classification_summary", sa.JSON(), nullable=False),
        sa.Column("input_observation_ids", sa.JSON(), nullable=False),
        sa.Column("input_observation_references", sa.JSON(), nullable=False),
        sa.Column("freshness_summary", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id", name=op.f("pk_strategy_snapshots")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_strategy_snapshots_idempotency_key")),
    )
    op.create_index(op.f("ix_strategy_snapshots_calculated_at"), "strategy_snapshots", ["calculated_at"], unique=False)
    op.create_index(op.f("ix_strategy_snapshots_model_version"), "strategy_snapshots", ["model_version"], unique=False)
    op.create_index(op.f("ix_strategy_snapshots_strategy_id"), "strategy_snapshots", ["strategy_id"], unique=False)
    op.create_index(
        op.f("ix_strategy_snapshots_strategy_version"),
        "strategy_snapshots",
        ["strategy_version"],
        unique=False,
    )

    op.create_table(
        "strategy_calculation_failures",
        sa.Column("failure_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("adapter_contract_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("intended_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intended_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_type", sa.String(length=255), nullable=False),
        sa.Column("error_message", sa.String(length=2048), nullable=False),
        sa.Column("input_observation_ids", sa.JSON(), nullable=False),
        sa.Column("input_observation_references", sa.JSON(), nullable=False),
        sa.Column("freshness_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("failure_id", name=op.f("pk_strategy_calculation_failures")),
        sa.UniqueConstraint(
            "idempotency_key",
            name=op.f("uq_strategy_calculation_failures_idempotency_key"),
        ),
    )
    op.create_index(
        op.f("ix_strategy_calculation_failures_failed_at"),
        "strategy_calculation_failures",
        ["failed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_calculation_failures_strategy_id"),
        "strategy_calculation_failures",
        ["strategy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_strategy_calculation_failures_strategy_id"), table_name="strategy_calculation_failures")
    op.drop_index(op.f("ix_strategy_calculation_failures_failed_at"), table_name="strategy_calculation_failures")
    op.drop_table("strategy_calculation_failures")
    op.drop_index(op.f("ix_strategy_snapshots_strategy_version"), table_name="strategy_snapshots")
    op.drop_index(op.f("ix_strategy_snapshots_strategy_id"), table_name="strategy_snapshots")
    op.drop_index(op.f("ix_strategy_snapshots_model_version"), table_name="strategy_snapshots")
    op.drop_index(op.f("ix_strategy_snapshots_calculated_at"), table_name="strategy_snapshots")
    op.drop_table("strategy_snapshots")
