"""Add inbound landing acquisition events.

Revision ID: 20260823_0006
Revises: 20260823_0005
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20260823_0006"
down_revision = "20260823_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inbound_landing_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("landing_path", sa.String(length=512), nullable=False),
        sa.Column("referrer_domain", sa.String(length=255), nullable=True),
        sa.Column("utm_source", sa.String(length=128), nullable=True),
        sa.Column("utm_medium", sa.String(length=128), nullable=True),
        sa.Column("utm_campaign", sa.String(length=128), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("coarse_session_id", sa.String(length=128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_inbound_landing_events")),
    )
    op.create_index(op.f("ix_inbound_landing_events_channel"), "inbound_landing_events", ["channel"])
    op.create_index(
        op.f("ix_inbound_landing_events_coarse_session_id"),
        "inbound_landing_events",
        ["coarse_session_id"],
    )
    op.create_index(op.f("ix_inbound_landing_events_landing_path"), "inbound_landing_events", ["landing_path"])
    op.create_index(op.f("ix_inbound_landing_events_occurred_at"), "inbound_landing_events", ["occurred_at"])
    op.create_index(op.f("ix_inbound_landing_events_referrer_domain"), "inbound_landing_events", ["referrer_domain"])
    op.create_index(op.f("ix_inbound_landing_events_utm_source"), "inbound_landing_events", ["utm_source"])


def downgrade() -> None:
    op.drop_index(op.f("ix_inbound_landing_events_utm_source"), table_name="inbound_landing_events")
    op.drop_index(op.f("ix_inbound_landing_events_referrer_domain"), table_name="inbound_landing_events")
    op.drop_index(op.f("ix_inbound_landing_events_occurred_at"), table_name="inbound_landing_events")
    op.drop_index(op.f("ix_inbound_landing_events_landing_path"), table_name="inbound_landing_events")
    op.drop_index(op.f("ix_inbound_landing_events_coarse_session_id"), table_name="inbound_landing_events")
    op.drop_index(op.f("ix_inbound_landing_events_channel"), table_name="inbound_landing_events")
    op.drop_table("inbound_landing_events")
