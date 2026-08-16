"""Versioned API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


class StrategySnapshotPayload(BaseModel):
    snapshot_id: str
    strategy_id: str
    strategy_version: str
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


class GameSummary(BaseModel):
    game_id: str
    name: str
    chains: list[str]
    economy_types: list[str]
    status: str
    strategy_count: int


class GameDetail(GameSummary):
    strategies: list["StrategySummary"]


class StrategySummary(BaseModel):
    strategy_id: str
    strategy_version: str
    game_id: str
    game_name: str
    name: str
    chain: str
    economy_type: str
    description: str
    latest_snapshot: StrategySnapshotPayload | None = None


class GamesPage(BaseModel):
    items: list[GameSummary]
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


class HealthPayload(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    api_version: str


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: str


GameDetail.model_rebuild()
