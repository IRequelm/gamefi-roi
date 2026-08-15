from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.defi_kingdoms_jeweler import (
    CLAIM_TRANSACTION_COST_USD,
    EMERGENCY_EXIT_VALUE_USD,
    ENTRY_VALUE_USD,
    JEWEL_REFERENCE_PRICE_USD,
    LOCK_DAYS,
    LOCKED_JEWEL_AMOUNT,
    MAX_LOCK_DAYS,
    REWARD_REALIZABLE_VALUE_USD,
    YESTERDAY_CJEWEL_BALANCE,
    YESTERDAY_REWARD_JEWEL,
    AdapterInputError,
    DfkJewelerAdapter,
    ValueClassification,
    derived_observation,
    verified_config_observation,
)
from app.engine.calculator import calculate_strategy_roi
from app.engine.results import MetricStatus
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "dfk_jeweler_golden.json"


def test_dfk_jeweler_golden_fixture_matches_manual_expected_roi() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = _observations_from_fixture(fixture["strategy"])
    expected = fixture["manual_expected"]

    adapter_result = DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(
        observations,
        calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )
    result = calculate_strategy_roi(adapter_result.economics_input)

    assert adapter_result.derived_values["dfk.jeweler.cjewel_received"] == Decimal(expected["cjewel_received"])
    assert adapter_result.derived_values["dfk.jeweler.user_reward_share"] == Decimal(expected["user_reward_share"])
    assert adapter_result.derived_values["dfk.jeweler.reward_jewel_day"] == Decimal(expected["reward_jewel_day"])
    assert adapter_result.classifications[LOCKED_JEWEL_AMOUNT] == ValueClassification.CONFIG
    assert adapter_result.classifications[YESTERDAY_REWARD_JEWEL] == ValueClassification.LIVE
    assert adapter_result.classifications[REWARD_REALIZABLE_VALUE_USD] == ValueClassification.DERIVED

    assert result.total_capital.amount == Decimal(expected["total_capital"])
    assert result.recoverable_capital.amount == Decimal(expected["recoverable_capital"])
    assert result.capital_at_risk.amount == Decimal(expected["capital_at_risk"])
    assert result.gross_nominal_earnings_day.amount == Decimal(expected["gross_nominal_earnings_day"])
    assert result.realizable_earnings_day.amount == Decimal(expected["realizable_earnings_day"])
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


def test_dfk_jeweler_adapter_fails_when_required_observation_is_missing() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = tuple(
        observation
        for observation in _observations_from_fixture(fixture["strategy"])
        if observation.metric != REWARD_REALIZABLE_VALUE_USD
    )

    with pytest.raises(AdapterInputError, match=REWARD_REALIZABLE_VALUE_USD):
        DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(observations)


def test_dfk_jeweler_adapter_fails_when_required_observation_is_stale() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = list(_observations_from_fixture(fixture["strategy"]))
    stale = observations[-1].model_copy(update={"fresh_until": datetime(2026, 8, 15, 11, 59, tzinfo=UTC)})
    observations[-1] = stale

    with pytest.raises(AdapterInputError, match="not fresh"):
        DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(
            tuple(observations),
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )


def _observations_from_fixture(payload: dict[str, str]) -> tuple[Observation, ...]:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    strategy_id = DFK_CJEWEL_MAX_LOCK_V1.strategy_id
    configs = (
        verified_config_observation(
            strategy_id=strategy_id,
            metric=LOCKED_JEWEL_AMOUNT,
            value=payload["locked_jewel_amount"],
            unit="JEWEL",
            source_locator="fixture:dfk-jeweler",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=LOCK_DAYS,
            value=payload["lock_days"],
            unit="day",
            source_locator="fixture:dfk-jeweler",
            retrieved_at=now,
        ),
        verified_config_observation(
            strategy_id=strategy_id,
            metric=MAX_LOCK_DAYS,
            value=payload["max_lock_days"],
            unit="day",
            source_locator="fixture:dfk-jeweler",
            retrieved_at=now,
        ),
    )
    live = (
        _live_observation(YESTERDAY_CJEWEL_BALANCE, payload["yesterday_cjewel_balance"], "cJEWEL", now),
        _live_observation(YESTERDAY_REWARD_JEWEL, payload["yesterday_reward_jewel"], "JEWEL", now),
    )
    derived = (
        _derived_observation(ENTRY_VALUE_USD, payload["entry_value_usd"], now),
        _derived_observation(EMERGENCY_EXIT_VALUE_USD, payload["emergency_exit_value_usd"], now),
        _derived_observation(JEWEL_REFERENCE_PRICE_USD, payload["jewel_reference_price_usd"], now),
        _derived_observation(REWARD_REALIZABLE_VALUE_USD, payload["reward_realizable_value_usd"], now),
        _derived_observation(CLAIM_TRANSACTION_COST_USD, payload["claim_transaction_cost_usd"], now),
    )
    return (*configs, *live, *derived)


def _live_observation(metric: str, value: str, unit: str, retrieved_at: datetime) -> Observation:
    return Observation(
        observation_id=f"live-{metric}",
        entity_type="strategy",
        entity_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        metric=metric,
        value=Decimal(value),
        unit=unit,
        quote_currency=None,
        source_provider="fixture-rpc",
        source_type=SourceType.ONCHAIN,
        source_locator="fixture:rpc",
        observed_at=retrieved_at,
        retrieved_at=retrieved_at,
        fresh_until=retrieved_at + timedelta(minutes=5),
        status=ObservationStatus.FRESH,
        metadata={"classification": ValueClassification.LIVE.value},
    )


def _derived_observation(metric: str, value: str, retrieved_at: datetime) -> Observation:
    return derived_observation(
        provider="fixture-derived",
        entity_type="strategy",
        entity_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        metric=metric,
        value=Decimal(value),
        unit="USD",
        source_locator="fixture:derived",
        input_observation_ids=("fixture-input",),
        retrieved_at=retrieved_at,
    )
