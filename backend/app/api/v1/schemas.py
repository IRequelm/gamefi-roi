"""Versioned API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class MoneyAmount(BaseModel):
    amount: str
    currency: str


class RatioMetric(BaseModel):
    value: str | None
    status: str
    reason: str | None = None


class BreakEvenMetric(BaseModel):
    basis: str
    recovery_target: MoneyAmount
    days: str | None
    status: str
    reason: str | None = None


class CapitalMetrics(BaseModel):
    total_capital: MoneyAmount
    sunk_cost: MoneyAmount
    recoverable_capital: MoneyAmount
    capital_at_risk: MoneyAmount


class EarningsMetrics(BaseModel):
    gross_nominal_earnings_day: MoneyAmount
    realizable_earnings_day: MoneyAmount
    operating_cost_day: MoneyAmount
    transaction_cost_day: MoneyAmount
    other_cost_day: MoneyAmount
    net_earnings_day: MoneyAmount


class RoiMetrics(BaseModel):
    break_even: BreakEvenMetric
    roi_total_7d: RatioMetric
    roi_total_30d: RatioMetric
    roi_total_90d: RatioMetric
    roi_risk_7d: RatioMetric
    roi_risk_30d: RatioMetric
    roi_risk_90d: RatioMetric
    exit_adjusted_pnl: MoneyAmount


class WarningPayload(BaseModel):
    code: str
    message: str
    severity: str


class FreshnessPayload(BaseModel):
    overall_status: str
    calculated_at: datetime
    status_counts: dict[str, int]
    input_count: int
    oldest_retrieved_at: datetime | None = None
    newest_retrieved_at: datetime | None = None
    earliest_fresh_until: datetime | None = None


class ScoreContributionPayload(BaseModel):
    factor: str
    points: int
    reason: str
    evidence: dict[str, Any]


class UnavailableFactorPayload(BaseModel):
    factor: str
    reason: str


class ScorePayload(BaseModel):
    available: bool
    score: int | None = None
    label: str | None = None
    methodology_version: str | None = None
    contributions: list[ScoreContributionPayload] = Field(default_factory=list)
    unavailable_factors: list[UnavailableFactorPayload] = Field(default_factory=list)


class VersionPayload(BaseModel):
    adapter_contract_version: str
    model_version: str
    scoring_methodology_version: str | None = None


class UncertaintyRangePayload(BaseModel):
    metric: str
    low_metric: str
    base_metric: str
    high_metric: str
    unit: str | None = None
    description: str | None = None
    values: dict[str, str | None] = Field(default_factory=dict)


class ClassificationSummaryPayload(BaseModel):
    counts: dict[str, int]
    metrics: dict[str, str]


class SourceReferencePayload(BaseModel):
    label: str
    url: str
    source_role: Literal["OFFICIAL_PROJECT", "OFFICIAL_CHAIN", "EXECUTABLE_MARKET", "AGGREGATOR", "OTHER_PUBLIC_EVIDENCE"] = "OFFICIAL_PROJECT"


class OutboundDestinationPayload(BaseModel):
    destination_id: str
    destination_slug: str
    opportunity_id: str
    opportunity_type: str
    game_id: str | None = None
    strategy_id: str | None = None
    destination_type: str
    label: str
    redirect_url: str
    official_url: str
    referral_url: str | None = None
    referral_code: str | None = None
    status: str
    is_affiliate: bool
    affiliate_program: str | None = None
    commercial_relationship: str
    disclosure_text: str
    source_reference: SourceReferencePayload
    reviewed_at: datetime
    verification_status: str
    allowed_surfaces: list[str]
    referral_status: str = "NONE"


class SponsoredPlacementPayload(BaseModel):
    placement_id: str
    opportunity_id: str
    strategy_id: str | None = None
    surface: str
    status: str
    label: str
    disclosure_text: str
    campaign_name: str | None = None
    sponsor_name: str | None = None


class RoiUnavailablePayload(BaseModel):
    reason: str
    missing_evidence: list[str] | None = None
    modeling_requirements: list[str] | None = None


class OpportunityLogoPayload(BaseModel):
    asset: str
    alt: str
    source_reference: SourceReferencePayload | None = None


class OpportunitySummary(BaseModel):
    opportunity_id: str
    opportunity_type: str
    name: str
    status: str
    platforms: list[str]
    chains: list[str]
    economy_types: list[str]
    reward_asset_or_points_type: list[str]
    value_realization_status: str
    data_feasibility_status: str
    strategy_count: int
    admission_mode: Literal["MODELED", "GUIDE_ONLY"]
    legacy_game_id: str | None = None
    primary_destination: OutboundDestinationPayload | None = None
    roi_unavailable: RoiUnavailablePayload | None = None
    logo: OpportunityLogoPayload | None = None


class OpportunityGuidancePayload(BaseModel):
    how_to_start: list[str] | None = None
    what_you_need: list[str] | None = None
    how_you_earn: list[str] | None = None
    how_to_exit_or_claim: list[str] | None = None


class OpportunityDetail(OpportunitySummary):
    feasibility_summary: str
    official_source_references: list[SourceReferencePayload]
    outbound_destinations: list[OutboundDestinationPayload]
    strategies: list["StrategySummary"]
    guidance: OpportunityGuidancePayload | None = None


class StrategySnapshotPayload(BaseModel):
    snapshot_id: str
    strategy_id: str
    strategy_version: str
    opportunity_id: str
    opportunity_type: str
    game_id: str
    game_name: str
    chain: str
    economy_type: str
    calculated_at: datetime
    capital: CapitalMetrics
    earnings: EarningsMetrics
    roi: RoiMetrics
    confidence: ScorePayload
    risk: ScorePayload
    warnings: list[WarningPayload]
    freshness: FreshnessPayload
    versions: VersionPayload
    uncertainty_ranges: list[UncertaintyRangePayload]
    classification_summary: ClassificationSummaryPayload


class GameSummary(BaseModel):
    game_id: str
    opportunity_id: str
    opportunity_type: str
    name: str
    chains: list[str]
    economy_types: list[str]
    status: str
    strategy_count: int
    primary_destination: OutboundDestinationPayload | None = None
    logo: OpportunityLogoPayload | None = None


class GameDetail(GameSummary):
    strategies: list["StrategySummary"]
    outbound_destinations: list[OutboundDestinationPayload]


class StrategySummary(BaseModel):
    strategy_id: str
    strategy_version: str
    opportunity_id: str
    opportunity_type: str
    game_id: str
    game_name: str
    name: str
    chain: str
    economy_type: str
    description: str
    outbound_destinations: list[OutboundDestinationPayload] = Field(default_factory=list)
    primary_destination: OutboundDestinationPayload | None = None
    latest_snapshot: StrategySnapshotPayload | None = None
    logo: OpportunityLogoPayload | None = None


class GamesPage(BaseModel):
    items: list[GameSummary]
    page: PageMeta


class OpportunitiesPage(BaseModel):
    items: list[OpportunitySummary]
    page: PageMeta


class StrategiesPage(BaseModel):
    items: list[StrategySummary]
    page: PageMeta


class HistoryPage(BaseModel):
    items: list[StrategySnapshotPayload]
    page: PageMeta


class RankingItem(BaseModel):
    rank: int
    strategy: StrategySummary
    latest_snapshot: StrategySnapshotPayload


class RankingsPage(BaseModel):
    items: list[RankingItem]
    page: PageMeta
    ordering: list[str]
    sponsored_placements: list[SponsoredPlacementPayload] = Field(default_factory=list)


class HealthPayload(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    api_version: str


class StrategyOpsStatusPayload(BaseModel):
    strategy_id: str
    strategy_version: str
    latest_snapshot_id: str | None = None
    latest_calculated_at: datetime | None = None
    freshness_status: str | None = None


class OpsStatusPayload(BaseModel):
    status: str
    generated_at: datetime
    database: dict[str, Any]
    scheduler: dict[str, Any]
    strategies: list[StrategyOpsStatusPayload]
    failed_calculation_count: int
    stale_strategy_count: int
    provider_errors: dict[str, int]
    application_errors: dict[str, Any]


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: str


GameDetail.model_rebuild()
OpportunityDetail.model_rebuild()
