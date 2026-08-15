"""Add raw market observations table.

Revision ID: 20260815_0002
Revises: 20260815_0001
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260815_0002"
down_revision = "20260815_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observations",
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("metric", sa.String(length=128), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("quote_currency", sa.String(length=32), nullable=True),
        sa.Column("source_provider", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_locator", sa.String(length=1024), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fresh_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("observation_id", name=op.f("pk_observations")),
    )
    op.create_index(op.f("ix_observations_entity_id"), "observations", ["entity_id"], unique=False)
    op.create_index(op.f("ix_observations_metric"), "observations", ["metric"], unique=False)
    op.create_index(op.f("ix_observations_retrieved_at"), "observations", ["retrieved_at"], unique=False)
    op.create_index(op.f("ix_observations_status"), "observations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_observations_status"), table_name="observations")
    op.drop_index(op.f("ix_observations_retrieved_at"), table_name="observations")
    op.drop_index(op.f("ix_observations_metric"), table_name="observations")
    op.drop_index(op.f("ix_observations_entity_id"), table_name="observations")
    op.drop_table("observations")
