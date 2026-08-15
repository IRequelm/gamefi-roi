"""Generic ROI engine result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.engine.inputs import BreakEvenBasis
from app.engine.money import Money


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    NOT_COMPUTABLE = "not_computable"


@dataclass(frozen=True)
class RatioMetric:
    value: Decimal | None
    status: MetricStatus
    reason: str | None = None


@dataclass(frozen=True)
class BreakEvenMetric:
    basis: BreakEvenBasis
    recovery_target: Money
    days: Decimal | None
    status: MetricStatus
    reason: str | None = None


@dataclass(frozen=True)
class RoiResult:
    strategy_id: str
    strategy_version: str
    model_version: str
    reporting_currency: str
    total_capital: Money
    sunk_cost: Money
    recoverable_capital: Money
    capital_at_risk: Money
    gross_nominal_earnings_day: Money
    realizable_earnings_day: Money
    operating_cost_day: Money
    transaction_cost_day: Money
    other_cost_day: Money
    net_earnings_day: Money
    break_even: BreakEvenMetric
    roi_total_7d: RatioMetric
    roi_total_30d: RatioMetric
    roi_total_90d: RatioMetric
    roi_risk_7d: RatioMetric
    roi_risk_30d: RatioMetric
    roi_risk_90d: RatioMetric
    exit_adjusted_pnl: Money
    input_observation_ids: tuple[str, ...]
