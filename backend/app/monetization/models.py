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
REFERRAL_OPERATIONS_VERSION = "referral-operations-v1"


class ReferralLifecycleStatus(str, Enum):
    NONE = "NONE"
    DISCOVERED = "DISCOVERED"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    APPLICATION_REQUIRED = "APPLICATION_REQUIRED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    NO_PROGRAM_FOUND = "NO_PROGRAM_FOUND"
    REVERIFY = "REVERIFY"


class ReferralCoverageState(str, Enum):
    REFERRAL_ACTIVE = "REFERRAL_ACTIVE"
    REFERRAL_PENDING = "REFERRAL_PENDING"
    REFERRAL_MISSING = "REFERRAL_MISSING"
    REFERRAL_RESEARCH_REQUIRED = "REFERRAL_RESEARCH_REQUIRED"
    NO_PROGRAM_FOUND = "NO_PROGRAM_FOUND"
    REFERRAL_EXPIRED = "REFERRAL_EXPIRED"
    REFERRAL_PAUSED = "REFERRAL_PAUSED"
    REFERRAL_REVERIFY = "REFERRAL_REVERIFY"


class ReferralTaskType(str, Enum):
    FIND_REFERRAL_PROGRAM = "FIND_REFERRAL_PROGRAM"
    APPLY_TO_PROGRAM = "APPLY_TO_PROGRAM"
    VERIFY_REFERRAL_LINK = "VERIFY_REFERRAL_LINK"
    RECHECK_PENDING_APPLICATION = "RECHECK_PENDING_APPLICATION"
    REVERIFY_PROGRAM = "REVERIFY_PROGRAM"
    REPLACE_EXPIRED_LINK = "REPLACE_EXPIRED_LINK"


class ReferralTaskStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


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


class ContentPerformancePlatform(str, Enum):
    X = "X"
    YOUTUBE = "YOUTUBE"


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
    official_url: str | None
    referral_url: str | None
    referral_code: str | None
    referral_url_template: str | None
    program_type: str | None
    commission_description: str | None
    eligibility_notes: str | None
    geographic_restrictions: str | None
    evidence_url: str | None
    evidence: MappingProxyType[str, Any]
    applied_at: datetime | None
    verified_at: datetime | None
    last_checked_at: datetime | None
    expires_at: datetime | None
    operator_notes: str | None
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
    settlement_reference_id: str | None
    notes: str | None
    evidence: MappingProxyType[str, Any]
    imported_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class ReferralTask:
    task_id: str
    opportunity_id: str
    destination_slug: str | None
    task_type: ReferralTaskType
    reason: str
    status: ReferralTaskStatus
    due_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


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


@dataclass(frozen=True)
class InboundLandingEvent:
    event_id: str
    landing_path: str
    referrer_domain: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    channel: str
    coarse_session_id: str | None
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class ContentPerformanceRecord:
    """Source-backed platform metrics for one content item and period.

    These are distribution metrics only. They never become ROI inputs or
    verified revenue without a separate partner attribution record.
    """

    performance_id: str
    platform: ContentPerformancePlatform
    content_id: str
    period_start: datetime
    period_end: datetime
    impressions: int | None
    views: int | None
    engagements: int | None
    link_clicks: int | None
    profile_visits: int | None
    followers_gained: int | None
    subscribers_gained: int | None
    average_retention_percent: Decimal | None
    evidence_url: str | None
    evidence_reference: str | None
    notes: str | None
    imported_at: datetime
    created_at: datetime
