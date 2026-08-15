"""Generic ROI engine."""

from app.engine.calculator import calculate_strategy_roi
from app.engine.inputs import BreakEvenBasis, CapitalInput, CostInput, StrategyEconomicsInput, RewardInput
from app.engine.money import Money
from app.engine.results import MetricStatus, RatioMetric, RoiResult

__all__ = [
    "BreakEvenBasis",
    "CapitalInput",
    "CostInput",
    "MetricStatus",
    "Money",
    "RatioMetric",
    "RewardInput",
    "RoiResult",
    "StrategyEconomicsInput",
    "calculate_strategy_roi",
]
