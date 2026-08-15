from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine import (
    BreakEvenBasis,
    CapitalInput,
    CostInput,
    Money,
    RewardInput,
    StrategyEconomicsInput,
    calculate_strategy_roi,
)
from app.engine.errors import EngineInputError
from app.engine.results import MetricStatus

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "roi_core_stationary_scenarios.json"


def _fixtures() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_stationary_fixture_calculates_manually_verified_roi_outputs() -> None:
    fixture = _fixtures()["stationary_quote_with_costs_and_recoverable_asset"]
    strategy_input = _strategy_input_from_fixture(fixture["input"])
    expected = fixture["expected"]

    result = calculate_strategy_roi(strategy_input)

    assert result.total_capital.amount == Decimal(expected["total_capital"])
    assert result.sunk_cost.amount == Decimal(expected["sunk_cost"])
    assert result.recoverable_capital.amount == Decimal(expected["recoverable_capital"])
    assert result.capital_at_risk.amount == Decimal(expected["capital_at_risk"])
    assert result.gross_nominal_earnings_day.amount == Decimal(expected["gross_nominal_earnings_day"])
    assert result.realizable_earnings_day.amount == Decimal(expected["realizable_earnings_day"])
    assert result.operating_cost_day.amount == Decimal(expected["operating_cost_day"])
    assert result.transaction_cost_day.amount == Decimal(expected["transaction_cost_day"])
    assert result.other_cost_day.amount == Decimal(expected["other_cost_day"])
    assert result.net_earnings_day.amount == Decimal(expected["net_earnings_day"])
    assert result.break_even.basis == BreakEvenBasis.TOTAL_CAPITAL
    assert result.break_even.recovery_target.amount == Decimal(expected["total_capital"])
    assert result.break_even.days == Decimal(expected["break_even_days"])
    assert result.break_even.status == MetricStatus.AVAILABLE
    assert result.roi_total_7d.value == Decimal(expected["roi_total_7d"])
    assert result.roi_total_30d.value == Decimal(expected["roi_total_30d"])
    assert result.roi_total_90d.value == Decimal(expected["roi_total_90d"])
    assert result.roi_risk_7d.value == Decimal(expected["roi_risk_7d"])
    assert result.roi_risk_30d.value == Decimal(expected["roi_risk_30d"])
    assert result.roi_risk_90d.value == Decimal(expected["roi_risk_90d"])
    assert result.exit_adjusted_pnl.amount == Decimal(expected["exit_adjusted_pnl"])
    assert result.input_observation_ids == ("obs-price", "obs-executable-quote", "obs-fee")


@pytest.mark.parametrize(
    ("basis", "expected_target", "expected_days"),
    [
        (BreakEvenBasis.TOTAL_CAPITAL, Decimal("110.00"), Decimal("32.35294117647058823529411765")),
        (BreakEvenBasis.SUNK_COST, Decimal("35.00"), Decimal("10.29411764705882352941176471")),
        (BreakEvenBasis.CAPITAL_AT_RISK, Decimal("70.00"), Decimal("20.58823529411764705882352941")),
    ],
)
def test_break_even_basis_is_explicit(
    basis: BreakEvenBasis,
    expected_target: Decimal,
    expected_days: Decimal,
) -> None:
    strategy_input = _base_strategy_input(break_even_basis=basis)

    result = calculate_strategy_roi(strategy_input)

    assert result.break_even.basis == basis
    assert result.break_even.recovery_target.amount == expected_target
    assert result.break_even.days == expected_days


def test_zero_net_earnings_makes_break_even_not_computable_without_fake_zero() -> None:
    fixture = _fixtures()["zero_net_no_break_even"]
    strategy_input = _strategy_input_from_fixture(fixture["input"])
    expected = fixture["expected"]

    result = calculate_strategy_roi(strategy_input)

    assert result.net_earnings_day.amount == Decimal(expected["net_earnings_day"])
    assert result.break_even.days is None
    assert result.break_even.status == MetricStatus(expected["break_even_status"])
    assert "positive" in result.break_even.reason
    assert result.roi_total_7d.value == Decimal(expected["roi_total_7d"])


def test_negative_net_earnings_keeps_negative_roi_and_no_break_even() -> None:
    fixture = _fixtures()["negative_net_no_break_even"]
    strategy_input = _strategy_input_from_fixture(fixture["input"])
    expected = fixture["expected"]

    result = calculate_strategy_roi(strategy_input)

    assert result.net_earnings_day.amount == Decimal(expected["net_earnings_day"])
    assert result.break_even.status == MetricStatus(expected["break_even_status"])
    assert result.roi_total_7d.value == Decimal(expected["roi_total_7d"])


def test_zero_total_capital_roi_is_explicitly_not_computable() -> None:
    fixture = _fixtures()["zero_total_capital_with_risk_roi"]
    strategy_input = _strategy_input_from_fixture(fixture["input"])
    expected = fixture["expected"]

    result = calculate_strategy_roi(strategy_input)

    assert result.total_capital.amount == Decimal(expected["total_capital"])
    assert result.roi_total_7d.value is None
    assert result.roi_total_7d.status == MetricStatus(expected["roi_total_7d_status"])
    assert result.roi_risk_7d.value == Decimal(expected["roi_risk_7d"])


def test_missing_required_money_input_fails_explicitly() -> None:
    fixture = _fixtures()["missing_transaction_cost_error"]
    expected_error = fixture["expected"]["error"]
    with pytest.raises(EngineInputError, match=expected_error):
        CostInput(
            operating_cost_day=Money.from_text(fixture["input"]["operating_cost_day"], "USD"),
            transaction_cost_day=None,
            other_cost_day=Money.from_text(fixture["input"]["other_cost_day"], "USD"),
        )


def test_missing_required_component_fails_explicitly() -> None:
    with pytest.raises(EngineInputError, match="capital is required"):
        StrategyEconomicsInput(
            strategy_id="fixture-strategy",
            strategy_version="fixture-v1",
            model_version="roi-core-v1",
            reporting_currency="USD",
            capital=None,
            rewards=RewardInput(
                gross_nominal_value_day=Money.from_text("1.00", "USD"),
                realizable_value_day=Money.from_text("1.00", "USD"),
            ),
            costs=CostInput(
                operating_cost_day=Money.from_text("0.00", "USD"),
                transaction_cost_day=Money.from_text("0.00", "USD"),
                other_cost_day=Money.from_text("0.00", "USD"),
            ),
            cumulative_net_cash_earnings=Money.from_text("0.00", "USD"),
            total_cash_invested_to_date=Money.from_text("0.00", "USD"),
            break_even_basis=BreakEvenBasis.TOTAL_CAPITAL,
        )


def test_money_rejects_binary_float_amounts() -> None:
    with pytest.raises(EngineInputError, match="Money.amount must be a Decimal"):
        Money(1.25, "USD")


def test_currency_mismatch_fails_before_calculation() -> None:
    with pytest.raises(EngineInputError, match="rewards currencies must match"):
        RewardInput(
            gross_nominal_value_day=Money.from_text("2.00", "USD"),
            realizable_value_day=Money.from_text("1.50", "RON"),
        )


def _strategy_input_from_fixture(payload: dict) -> StrategyEconomicsInput:
    currency = payload["reporting_currency"]
    return _base_strategy_input(
        strategy_id=payload["strategy_id"],
        strategy_version=payload["strategy_version"],
        model_version=payload["model_version"],
        reporting_currency=currency,
        break_even_basis=BreakEvenBasis(payload["break_even_basis"]),
        capital=CapitalInput(
            sunk_cost=Money.from_text(payload["capital"]["sunk_cost"], currency),
            recoverable_entry_cost=Money.from_text(payload["capital"]["recoverable_entry_cost"], currency),
            current_recoverable_value=Money.from_text(payload["capital"]["current_recoverable_value"], currency),
            initial_operating_reserve=Money.from_text(payload["capital"]["initial_operating_reserve"], currency),
            capital_at_risk=Money.from_text(payload["capital"]["capital_at_risk"], currency),
        ),
        rewards=RewardInput(
            gross_nominal_value_day=Money.from_text(payload["rewards"]["gross_nominal_value_day"], currency),
            realizable_value_day=Money.from_text(payload["rewards"]["realizable_value_day"], currency),
        ),
        costs=CostInput(
            operating_cost_day=Money.from_text(payload["costs"]["operating_cost_day"], currency),
            transaction_cost_day=Money.from_text(payload["costs"]["transaction_cost_day"], currency),
            other_cost_day=Money.from_text(payload["costs"]["other_cost_day"], currency),
        ),
        cumulative_net_cash_earnings=Money.from_text(payload["cumulative_net_cash_earnings"], currency),
        total_cash_invested_to_date=Money.from_text(payload["total_cash_invested_to_date"], currency),
        input_observation_ids=tuple(payload["input_observation_ids"]),
    )


def _base_strategy_input(
    *,
    strategy_id: str = "fixture-strategy",
    strategy_version: str = "fixture-v1",
    model_version: str = "roi-core-v1",
    reporting_currency: str = "USD",
    break_even_basis: BreakEvenBasis = BreakEvenBasis.TOTAL_CAPITAL,
    capital: CapitalInput | None = None,
    rewards: RewardInput | None = None,
    costs: CostInput | None = None,
    cumulative_net_cash_earnings: Money | None = None,
    total_cash_invested_to_date: Money | None = None,
    input_observation_ids: tuple[str, ...] = ("obs-price", "obs-executable-quote", "obs-fee"),
) -> StrategyEconomicsInput:
    currency = reporting_currency
    return StrategyEconomicsInput(
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        model_version=model_version,
        reporting_currency=currency,
        capital=capital
        or CapitalInput(
            sunk_cost=Money.from_text("35.00", currency),
            recoverable_entry_cost=Money.from_text("65.00", currency),
            current_recoverable_value=Money.from_text("42.00", currency),
            initial_operating_reserve=Money.from_text("10.00", currency),
            capital_at_risk=Money.from_text("70.00", currency),
        ),
        rewards=rewards
        or RewardInput(
            gross_nominal_value_day=Money.from_text("6.00", currency),
            realizable_value_day=Money.from_text("5.40", currency),
        ),
        costs=costs
        or CostInput(
            operating_cost_day=Money.from_text("1.10", currency),
            transaction_cost_day=Money.from_text("0.40", currency),
            other_cost_day=Money.from_text("0.50", currency),
        ),
        cumulative_net_cash_earnings=cumulative_net_cash_earnings or Money.from_text("41.20", currency),
        total_cash_invested_to_date=total_cash_invested_to_date or Money.from_text("110.00", currency),
        break_even_basis=break_even_basis,
        input_observation_ids=input_observation_ids,
    )
