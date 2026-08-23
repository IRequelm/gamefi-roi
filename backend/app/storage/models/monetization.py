"""Persistent commercial monetization records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.metadata import Base


class OutboundClickEventRecord(Base):
    __tablename__ = "outbound_click_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    destination_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    destination_id: Mapped[str] = mapped_column(String(255), nullable=False)
    opportunity_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    opportunity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    game_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strategy_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    destination_type: Mapped[str] = mapped_column(String(64), nullable=False)
    referral_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    commercial_relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    is_affiliate: Mapped[bool] = mapped_column(Boolean, nullable=False)
    target_url_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_page: Mapped[str | None] = mapped_column(String(128), nullable=True)
    placement: Mapped[str | None] = mapped_column(String(128), nullable=True)
    coarse_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    user_agent_category: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralProgramRecord(Base):
    __tablename__ = "referral_programs"

    program_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    destination_slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    affiliate_program: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referral_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    commercial_relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    disclosure_text: Mapped[str] = mapped_column(String(2048), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column("evidence", JSON, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RevenueAttributionRecord(Base):
    __tablename__ = "revenue_attributions"

    attribution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    destination_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    attribution_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    click_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    click_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_conversion_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_amount: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revenue_currency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_program: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_json: Mapped[dict[str, Any]] = mapped_column("evidence", JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SponsoredPlacementRecord(Base):
    __tablename__ = "sponsored_placements"

    placement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    surface: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    disclosure_text: Mapped[str] = mapped_column(String(2048), nullable=False)
    campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sponsor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audit_trail_json: Mapped[dict[str, Any]] = mapped_column("audit_trail", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
