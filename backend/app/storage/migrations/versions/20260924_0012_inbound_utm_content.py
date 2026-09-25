"""Capture UTM content for individual distribution attribution.

Revision ID: 20260924_0012
Revises: 20260921_0011
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260924_0012"
down_revision = "20260921_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inbound_landing_events", sa.Column("utm_content", sa.String(length=128), nullable=True))
    op.create_index(
        op.f("ix_inbound_landing_events_utm_content"),
        "inbound_landing_events",
        ["utm_content"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inbound_landing_events_utm_content"), table_name="inbound_landing_events")
    op.drop_column("inbound_landing_events", "utm_content")
