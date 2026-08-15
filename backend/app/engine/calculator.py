"""Generic strategy ROI calculations."""

from __future__ import annotations

from decimal import Decimal

from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_int
from app.engine.inputs import BreakEvenBasis, StrategyEconomicsInput
from app.engine.money import Money
from app.engine.results import BreakEvenMetric, MetricStatus, RatioMetric, RoiResult

MODEL_VERSION = "roi-core-v1"
ROI_PERIODS = (7, 30, 90)


def calculate_strategy_roi(strategy_input: StrategyEconomicsInput) -> RoiResult:
    total_capital = _total_capital(strategy_input)
    net_earnings_day = _net_earnings_day(strategy_input)
    break_even = _break_even(strategy_input.break_even_basis, _recovery_target(strategy_input, total_capital), net_earnings_day)
    exit_adjusted_pnl = (
        strategy_input.cumulative_net_cash_earnings
        + strategy_input.capital.current_recoverable_value
        - strategy_input.total_cash_invested_to_date
    )

    return RoiResult(
        strategy_id=strategy_input.strategy_id,
        strategy_version=strategy_input.strategy_version,
        model_version=strategy_input.model_version,
        reporting_currency=strategy_input.reporting_currency,
        total_capital=total_capital,
        sunk_cost=strategy_input.capital.sunk_cost,
        recoverable_capital=strategy_input.capital.current_recoverable_value,
        capital_at_risk=strategy_input.capital.capital_at_risk,
        gross_nominal_earnings_day=strategy_input.rewards.gross_nominal_value_day,
        realizable_earnings_day=strategy_input.rewards.realizable_value_day,
        operating_cost_day=strategy_input.costs.operating_cost_day,
        transaction_cost_day=strategy_input.costs.transaction_cost_day,
        other_cost_day=strategy_input.costs.other_cost_day,
        net_earnings_day=net_earnings_day,
        break_even=break_even,
        roi_total_7d=_roi(net_earnings_day, total_capital, 7),
        roi_total_30d=_roi(net_earnings_day, total_capital, 30),
        roi_total_90d=_roi(net_earnings_day, total_capital, 90),
        roi_risk_7d=_roi(net_earnings_day, strategy_input.capital.capital_at_risk, 7),
        roi_risk_30d=_roi(net_earnings_day, strategy_input.capital.capital_at_risk, 30),
        roi_risk_90d=_roi(net_earnings_day, strategy_input.capital.capital_at_risk, 90),
        exit_adjusted_pnl=exit_adjusted_pnl,
        input_observation_ids=strategy_input.input_observation_ids,
    )


def _total_capital(strategy_input: StrategyEconomicsInput) -> Money:
    capital = strategy_input.capital
    return capital.sunk_cost + capital.recoverable_entry_cost + capital.initial_operating_reserve


def _net_earnings_day(strategy_input: StrategyEconomicsInput) -> Money:
    costs = strategy_input.costs
    return (
        strategy_input.rewards.realizable_value_day
        - costs.operating_cost_day
        - costs.transaction_cost_day
        - costs.other_cost_day
    )


def _recovery_target(strategy_input: StrategyEconomicsInput, total_capital: Money) -> Money:
    if strategy_input.break_even_basis == BreakEvenBasis.TOTAL_CAPITAL:
        return total_capital
    if strategy_input.break_even_basis == BreakEvenBasis.SUNK_COST:
        return strategy_input.capital.sunk_cost
    return strategy_input.capital.capital_at_risk


def _break_even(basis: BreakEvenBasis, recovery_target: Money, net_earnings_day: Money) -> BreakEvenMetric:
    if net_earnings_day.amount <= Decimal("0"):
        return BreakEvenMetric(
            basis=basis,
            recovery_target=recovery_target,
            days=None,
            status=MetricStatus.NOT_COMPUTABLE,
            reason="Net earnings must be positive to calculate break-even days",
        )

    days = FINANCIAL_DECIMAL_CONTEXT.divide(recovery_target.amount, net_earnings_day.amount)
    return BreakEvenMetric(
        basis=basis,
        recovery_target=recovery_target,
        days=days,
        status=MetricStatus.AVAILABLE,
    )


def _roi(net_earnings_day: Money, denominator: Money, days: int) -> RatioMetric:
    if denominator.amount == Decimal("0"):
        return RatioMetric(
            value=None,
            status=MetricStatus.NOT_COMPUTABLE,
            reason="ROI denominator is zero",
        )

    period_earnings = net_earnings_day.multiply(decimal_from_int(days))
    ratio = FINANCIAL_DECIMAL_CONTEXT.divide(period_earnings.amount, denominator.amount)
    return RatioMetric(value=ratio, status=MetricStatus.AVAILABLE)
