"""Add autonomous discovery records and dynamic catalog overlay."""

from alembic import op
import sqlalchemy as sa

revision = "20260910_0009"
down_revision = "20260907_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_records",
        sa.Column("discovery_id", sa.String(length=64), primary_key=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("admission_outcome", sa.String(length=32), nullable=True),
        sa.Column("discovery_score", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_discovery_records_normalized_name", "discovery_records", ["normalized_name"])
    op.create_index("ix_discovery_records_validation_status", "discovery_records", ["validation_status"])
    op.create_index("ix_discovery_records_admission_outcome", "discovery_records", ["admission_outcome"])
    op.create_table(
        "dynamic_catalog_entries",
        sa.Column("opportunity_id", sa.String(length=255), primary_key=True),
        sa.Column("discovery_id", sa.String(length=64), nullable=False),
        sa.Column("admission_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_dynamic_catalog_entries_discovery_id", "dynamic_catalog_entries", ["discovery_id"])
    op.create_index("ix_dynamic_catalog_entries_status", "dynamic_catalog_entries", ["status"])


def downgrade() -> None:
    op.drop_table("dynamic_catalog_entries")
    op.drop_table("discovery_records")
