"""Transparent monetization data contracts.

Commercial records are intentionally separate from ROI snapshots, observations,
and risk/confidence scores. They may explain outbound and partner performance,
but they are never ROI model inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any


MONETIZATION_METHODOLOGY_VERSION = "monetization-foundation-v1"


class ReferralLifecycleStatus(str, Enum):
    NONE = "NONE"
    DISCOVERED = "DISCOVERED"
    APPLICATION_REQUIRED = "APPLICATION_REQUIRED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RevenueAttributionStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class SponsoredPlacementStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class OutboundClickEvent:
    event_id: str
    destination_slug: str
    destination_id: str
    opportunity_id: str | None
    opportunity_type: str | None
    game_id: str | None
    strategy_id: str | None
    destination_type: str
    referral_status: ReferralLifecycleStatus
    commercial_relationship: str
    is_affiliate: bool
    target_url_kind: str
    source_page: str | None
    placement: str | None
    coarse_session_id: str | None
    user_agent_category: str
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class ReferralProgram:
    program_id: str
    destination_slug: str
    opportunity_id: str | None
    strategy_id: str | None
    affiliate_program: str | None
    referral_status: ReferralLifecycleStatus
    commercial_relationship: str
    disclosure_text: str
    verification_status: str
    evidence: MappingProxyType[str, Any]
    verified_at: datetime | None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RevenueAttribution:
    attribution_id: str
    destination_slug: str
    opportunity_id: str | None
    strategy_id: str | None
    attribution_status: RevenueAttributionStatus
    click_period_start: datetime
    click_period_end: datetime
    verified_conversion_count: int | None
    revenue_amount: Decimal | None
    revenue_currency: str | None
    source_program: str | None
    evidence: MappingProxyType[str, Any]
    imported_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class SponsoredPlacement:
    placement_id: str
    opportunity_id: str
    strategy_id: str | None
    surface: str
    status: SponsoredPlacementStatus
    label: str
    disclosure_text: str
    campaign_name: str | None
    sponsor_name: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    audit_trail: MappingProxyType[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MonetizationMetricValue:
    value: str | None
    status: str
    reason: str | None = None


@dataclass(frozen=True)
class MonetizationMetrics:
    methodology_version: str
    destination_slug: str | None
    outbound_clicks: int
    coarse_sessions: MonetizationMetricValue
    click_through_rate: MonetizationMetricValue
    verified_conversions: MonetizationMetricValue
    verified_revenue: MonetizationMetricValue
    earnings_per_click: MonetizationMetricValue
    verified_conversion_rate: MonetizationMetricValue
