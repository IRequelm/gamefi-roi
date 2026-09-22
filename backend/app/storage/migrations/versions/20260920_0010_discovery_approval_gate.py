"""Add human approval state for autonomous discovery candidates."""

from alembic import op
import sqlalchemy as sa


revision = "20260920_0010"
down_revision = "20260910_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discovery_records", sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="NOT_REQUIRED"))
    op.add_column("discovery_records", sa.Column("approval_token_hash", sa.String(length=128), nullable=True))
    op.add_column("discovery_records", sa.Column("approval_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("discovery_records", sa.Column("approval_decided_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_discovery_records_approval_status", "discovery_records", ["approval_status"])
    # A unique index works on both PostgreSQL and SQLite; SQLite cannot add an
    # ALTER TABLE unique constraint to an already-created table.
    op.create_index("uq_discovery_records_approval_token_hash", "discovery_records", ["approval_token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_discovery_records_approval_token_hash", table_name="discovery_records")
    op.drop_index("ix_discovery_records_approval_status", table_name="discovery_records")
    op.drop_column("discovery_records", "approval_decided_at")
    op.drop_column("discovery_records", "approval_requested_at")
    op.drop_column("discovery_records", "approval_token_hash")
    op.drop_column("discovery_records", "approval_status")
