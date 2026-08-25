from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.farmers_world import (
    CYCLE_HOURS,
    CYCLES_PER_DAY,
    ENTRY_VALUE_USD,
    EXIT_VALUE_USD,
    FWF_INPUT_PER_CYCLE,
    FWF_OPERATING_COST_DAY_USD,
    FWG_INPUT_PER_CYCLE,
    FWG_OPERATING_COST_DAY_USD,
    FWW_OUTPUT_PER_CYCLE,
    FWW_REALIZABLE_VALUE_DAY_USD,
    FWW_REFERENCE_PRICE_USD,
    TOOL_COUNT,
    TRANSACTION_COST_DAY_USD,
    AdapterInputError,
    FarmersWorldAxeAdapter,
    ValueClassification,
    derived_observation,
    verified_config_observation,
)
from app.engine.calculator import calculate_strategy_roi
from app.engine.results import MetricStatus
from app.sources.observations import Observation
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "farmers_world_axe_golden.json"


def test_farmers_world_axe_golden_fixture_matches_manual_expected_roi() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = _observations_from_fixture(fixture["strategy"])
    expected = fixture["manual_expected"]

    adapter_result = FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(
        observations,
        calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )
    result = calculate_strategy_roi(adapter_result.economics_input)

    assert adapter_result.derived_values["farmers_world.axe.fww_output_day"] == Decimal(expected["fww_output_day"])
    assert adapter_result.derived_values["farmers_world.axe.fwf_input_day"] == Decimal(expected["fwf_input_day"])
    assert adapter_result.derived_values["farmers_world.axe.fwg_input_day"] == Decimal(expected["fwg_input_day"])
    assert adapter_result.derived_values["farmers_world.axe.gross_nominal_value_day_usd"] == Decimal(
        expected["gross_nominal_earnings_day"]
    )
    assert adapter_result.classifications[TOOL_COUNT] == ValueClassification.CONFIG
    assert adapter_result.classifications[FWW_REALIZABLE_VALUE_DAY_USD] == ValueClassification.DERIVED

    assert result.total_capital.amount == Decimal(expected["total_capital"])
    assert result.recoverable_capital.amount == Decimal(expected["recoverable_capital"])
    assert result.capital_at_risk.amount == Decimal(expected["capital_at_risk"])
    assert result.gross_nominal_earnings_day.amount == Decimal(expected["gross_nominal_earnings_day"])
    assert result.realizable_earnings_day.amount == Decimal(expected["realizable_earnings_day"])
    assert result.operating_cost_day.amount == Decimal(expected["operating_cost_day"])
    assert result.transaction_cost_day.amount == Decimal(expected["transaction_cost_day"])
    assert result.net_earnings_day.amount == Decimal(expected["net_earnings_day"])
    assert result.break_even.status == MetricStatus.AVAILABLE
    assert result.break_even.days == Decimal(expected["break_even_days"])
    assert result.roi_total_7d.value == Decimal(expected["roi_total_7d"])
    assert result.roi_total_30d.value == Decimal(expected["roi_total_30d"])
    assert result.roi_total_90d.value == Decimal(expected["roi_total_90d"])
    assert result.roi_risk_7d.value == Decimal(expected["roi_risk_7d"])
    assert result.roi_risk_30d.value == Decimal(expected["roi_risk_30d"])
    assert result.roi_risk_90d.value == Decimal(expected["roi_risk_90d"])
    assert result.exit_adjusted_pnl.amount == Decimal(expected["exit_adjusted_pnl"])


def test_farmers_world_adapter_fails_when_required_observation_is_missing() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = tuple(
        observation
        for observation in _observations_from_fixture(fixture["strategy"])
        if observation.metric != FWF_OPERATING_COST_DAY_USD
    )

    with pytest.raises(AdapterInputError, match=FWF_OPERATING_COST_DAY_USD):
        FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(observations)


def test_farmers_world_adapter_fails_when_required_observation_is_stale() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = list(_observations_from_fixture(fixture["strategy"]))
    stale = observations[-1].model_copy(update={"fresh_until": datetime(2026, 8, 15, 11, 59, tzinfo=UTC)})
    observations[-1] = stale

    with pytest.raises(AdapterInputError, match="not fresh"):
        FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(
            tuple(observations),
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )


def test_farmers_world_adapter_rejects_zero_market_derived_entry_value() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload = dict(fixture["strategy"])
    payload["entry_value_usd"] = "0"
    observations = _observations_from_fixture(payload)

    with pytest.raises(AdapterInputError, match=ENTRY_VALUE_USD):
        FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(
            observations,
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )


def test_farmers_world_adapter_rejects_zero_reward_market_value_but_allows_zero_transaction_cost() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload = dict(fixture["strategy"])
    payload["fww_realizable_value_day_usd"] = "0"
    payload["transaction_cost_day_usd"] = "0"
    observations = _observations_from_fixture(payload)

    with pytest.raises(AdapterInputError, match=FWW_REALIZABLE_VALUE_DAY_USD):
        FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(
            observations,
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )

    valid_payload = dict(fixture["strategy"])
    valid_payload["transaction_cost_day_usd"] = "0"
    valid_result = FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(
        _observations_from_fixture(valid_payload),
        calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )

    assert valid_result.economics_input.costs.transaction_cost_day.amount == Decimal("0")


def _observations_from_fixture(payload: dict[str, str]) -> tuple[Observation, ...]:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    strategy_id = FARMERS_WORLD_AXE_WOOD_V1.strategy_id
    configs = (
        verified_config_observation(
            strategy_id=strategy_id,
            metric=TOOL_COUNT,
            value=payload["tool_count"],
            unit="tool",
            source_locator="fixture:farmers-world-axe",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=CYCLES_PER_DAY,
            value=payload["cycles_per_day"],
            unit="cycle/day",
            source_locator="fixture:farmers-world-axe",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=CYCLE_HOURS,
            value=payload["cycle_hours"],
            unit="hour",
            source_locator="fixture:farmers-world-axe",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=FWW_OUTPUT_PER_CYCLE,
            value=payload["fww_output_per_cycle"],
            unit="FWW",
            source_locator="fixture:farmers-world-axe",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=FWF_INPUT_PER_CYCLE,
            value=payload["fwf_input_per_cycle"],
            unit="FWF",
            source_locator="fixture:farmers-world-axe",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=FWG_INPUT_PER_CYCLE,
            value=payload["fwg_input_per_cycle"],
            unit="FWG",
            source_locator="fixture:farmers-world-axe",
            retrieved_at=now,
        ),
    )
    derived = (
        _derived_observation(ENTRY_VALUE_USD, payload["entry_value_usd"], now),
        _derived_observation(EXIT_VALUE_USD, payload["exit_value_usd"], now),
        _derived_observation(FWW_REFERENCE_PRICE_USD, payload["fww_reference_price_usd"], now),
        _derived_observation(FWW_REALIZABLE_VALUE_DAY_USD, payload["fww_realizable_value_day_usd"], now),
        _derived_observation(FWF_OPERATING_COST_DAY_USD, payload["fwf_operating_cost_day_usd"], now),
        _derived_observation(FWG_OPERATING_COST_DAY_USD, payload["fwg_operating_cost_day_usd"], now),
        _derived_observation(TRANSACTION_COST_DAY_USD, payload["transaction_cost_day_usd"], now),
    )
    return (*configs, *derived)


def _derived_observation(metric: str, value: str, retrieved_at: datetime) -> Observation:
    return derived_observation(
        provider="fixture-derived",
        entity_type="strategy",
        entity_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        metric=metric,
        value=Decimal(value),
        unit="USD",
        source_locator="fixture:derived",
        input_observation_ids=("fixture-input",),
        retrieved_at=retrieved_at,
    )
