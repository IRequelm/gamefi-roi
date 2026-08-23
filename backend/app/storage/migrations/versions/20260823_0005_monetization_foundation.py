"""Add monetization foundation tables.

Revision ID: 20260823_0005
Revises: 20260816_0004
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20260823_0005"
down_revision = "20260816_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbound_click_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("destination_slug", sa.String(length=255), nullable=False),
        sa.Column("destination_id", sa.String(length=255), nullable=False),
        sa.Column("opportunity_id", sa.String(length=255), nullable=True),
        sa.Column("opportunity_type", sa.String(length=64), nullable=True),
        sa.Column("game_id", sa.String(length=255), nullable=True),
        sa.Column("strategy_id", sa.String(length=255), nullable=True),
        sa.Column("destination_type", sa.String(length=64), nullable=False),
        sa.Column("referral_status", sa.String(length=64), nullable=False),
        sa.Column("commercial_relationship", sa.String(length=64), nullable=False),
        sa.Column("is_affiliate", sa.Boolean(), nullable=False),
        sa.Column("target_url_kind", sa.String(length=32), nullable=False),
        sa.Column("source_page", sa.String(length=128), nullable=True),
        sa.Column("placement", sa.String(length=128), nullable=True),
        sa.Column("coarse_session_id", sa.String(length=128), nullable=True),
        sa.Column("user_agent_category", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_outbound_click_events")),
    )
    op.create_index(op.f("ix_outbound_click_events_coarse_session_id"), "outbound_click_events", ["coarse_session_id"])
    op.create_index(op.f("ix_outbound_click_events_destination_slug"), "outbound_click_events", ["destination_slug"])
    op.create_index(op.f("ix_outbound_click_events_occurred_at"), "outbound_click_events", ["occurred_at"])
    op.create_index(op.f("ix_outbound_click_events_opportunity_id"), "outbound_click_events", ["opportunity_id"])
    op.create_index(op.f("ix_outbound_click_events_referral_status"), "outbound_click_events", ["referral_status"])
    op.create_index(op.f("ix_outbound_click_events_strategy_id"), "outbound_click_events", ["strategy_id"])

    op.create_table(
        "referral_programs",
        sa.Column("program_id", sa.String(length=64), nullable=False),
        sa.Column("destination_slug", sa.String(length=255), nullable=False),
        sa.Column("opportunity_id", sa.String(length=255), nullable=True),
        sa.Column("strategy_id", sa.String(length=255), nullable=True),
        sa.Column("affiliate_program", sa.String(length=255), nullable=True),
        sa.Column("referral_status", sa.String(length=64), nullable=False),
        sa.Column("commercial_relationship", sa.String(length=64), nullable=False),
        sa.Column("disclosure_text", sa.String(length=2048), nullable=False),
        sa.Column("verification_status", sa.String(length=64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("program_id", name=op.f("pk_referral_programs")),
        sa.UniqueConstraint("destination_slug", name=op.f("uq_referral_programs_destination_slug")),
    )
    op.create_index(op.f("ix_referral_programs_destination_slug"), "referral_programs", ["destination_slug"])
    op.create_index(op.f("ix_referral_programs_opportunity_id"), "referral_programs", ["opportunity_id"])
    op.create_index(op.f("ix_referral_programs_referral_status"), "referral_programs", ["referral_status"])
    op.create_index(op.f("ix_referral_programs_strategy_id"), "referral_programs", ["strategy_id"])

    op.create_table(
        "revenue_attributions",
        sa.Column("attribution_id", sa.String(length=64), nullable=False),
        sa.Column("destination_slug", sa.String(length=255), nullable=False),
        sa.Column("opportunity_id", sa.String(length=255), nullable=True),
        sa.Column("strategy_id", sa.String(length=255), nullable=True),
        sa.Column("attribution_status", sa.String(length=64), nullable=False),
        sa.Column("click_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("click_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_conversion_count", sa.Integer(), nullable=True),
        sa.Column("revenue_amount", sa.String(length=128), nullable=True),
        sa.Column("revenue_currency", sa.String(length=32), nullable=True),
        sa.Column("source_program", sa.String(length=255), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("attribution_id", name=op.f("pk_revenue_attributions")),
    )
    op.create_index(op.f("ix_revenue_attributions_attribution_status"), "revenue_attributions", ["attribution_status"])
    op.create_index(op.f("ix_revenue_attributions_destination_slug"), "revenue_attributions", ["destination_slug"])
    op.create_index(op.f("ix_revenue_attributions_imported_at"), "revenue_attributions", ["imported_at"])
    op.create_index(op.f("ix_revenue_attributions_opportunity_id"), "revenue_attributions", ["opportunity_id"])
    op.create_index(op.f("ix_revenue_attributions_strategy_id"), "revenue_attributions", ["strategy_id"])

    op.create_table(
        "sponsored_placements",
        sa.Column("placement_id", sa.String(length=64), nullable=False),
        sa.Column("opportunity_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_id", sa.String(length=255), nullable=True),
        sa.Column("surface", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("disclosure_text", sa.String(length=2048), nullable=False),
        sa.Column("campaign_name", sa.String(length=255), nullable=True),
        sa.Column("sponsor_name", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audit_trail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("placement_id", name=op.f("pk_sponsored_placements")),
    )
    op.create_index(op.f("ix_sponsored_placements_opportunity_id"), "sponsored_placements", ["opportunity_id"])
    op.create_index(op.f("ix_sponsored_placements_status"), "sponsored_placements", ["status"])
    op.create_index(op.f("ix_sponsored_placements_strategy_id"), "sponsored_placements", ["strategy_id"])
    op.create_index(op.f("ix_sponsored_placements_surface"), "sponsored_placements", ["surface"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sponsored_placements_surface"), table_name="sponsored_placements")
    op.drop_index(op.f("ix_sponsored_placements_strategy_id"), table_name="sponsored_placements")
    op.drop_index(op.f("ix_sponsored_placements_status"), table_name="sponsored_placements")
    op.drop_index(op.f("ix_sponsored_placements_opportunity_id"), table_name="sponsored_placements")
    op.drop_table("sponsored_placements")
    op.drop_index(op.f("ix_revenue_attributions_strategy_id"), table_name="revenue_attributions")
    op.drop_index(op.f("ix_revenue_attributions_opportunity_id"), table_name="revenue_attributions")
    op.drop_index(op.f("ix_revenue_attributions_imported_at"), table_name="revenue_attributions")
    op.drop_index(op.f("ix_revenue_attributions_destination_slug"), table_name="revenue_attributions")
    op.drop_index(op.f("ix_revenue_attributions_attribution_status"), table_name="revenue_attributions")
    op.drop_table("revenue_attributions")
    op.drop_index(op.f("ix_referral_programs_strategy_id"), table_name="referral_programs")
    op.drop_index(op.f("ix_referral_programs_referral_status"), table_name="referral_programs")
    op.drop_index(op.f("ix_referral_programs_opportunity_id"), table_name="referral_programs")
    op.drop_index(op.f("ix_referral_programs_destination_slug"), table_name="referral_programs")
    op.drop_table("referral_programs")
    op.drop_index(op.f("ix_outbound_click_events_strategy_id"), table_name="outbound_click_events")
    op.drop_index(op.f("ix_outbound_click_events_referral_status"), table_name="outbound_click_events")
    op.drop_index(op.f("ix_outbound_click_events_opportunity_id"), table_name="outbound_click_events")
    op.drop_index(op.f("ix_outbound_click_events_occurred_at"), table_name="outbound_click_events")
    op.drop_index(op.f("ix_outbound_click_events_destination_slug"), table_name="outbound_click_events")
    op.drop_index(op.f("ix_outbound_click_events_coarse_session_id"), table_name="outbound_click_events")
    op.drop_table("outbound_click_events")
