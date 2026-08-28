from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.contract import ADAPTER_CONTRACT_VERSION, AdapterInputError, AdapterResultV1, ValueClassification, live_observation
from app.adapters.scenario_yield import GROSS_NOMINAL_VALUE_DAY_USD, NET_EARNINGS_DAY_USD, ScenarioYieldAdapter
from app.adapters.scenario_yield_probe import (
    REWARD_TOKEN_PRICE_USD,
    build_scenario_observations,
    load_fixture_observations,
)
from app.engine.calculator import MODEL_VERSION, calculate_strategy_roi
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.strategies.catalog import get_opportunity, list_opportunities, list_strategies
from app.strategies.scenario_yield import (
    DIMO_SOFTWARE_ONLY_V1,
    SCENARIO_YIELD_STRATEGIES,
    ScenarioYieldStrategyDefinition,
    scenario_metric,
)

FIXTURE = Path(__file__).parent / "fixtures" / "v1_strategy_expansion_golden.json"
CALCULATED_AT = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("strategy", SCENARIO_YIELD_STRATEGIES)
def test_scenario_yield_strategies_conform_to_adapter_contract_and_golden_fixture(
    strategy: ScenarioYieldStrategyDefinition,
) -> None:
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))["manual_expected"][strategy.strategy_id]
    observations = load_fixture_observations(CALCULATED_AT, strategy=strategy)

    adapter_result = ScenarioYieldAdapter(strategy).build_engine_input(
        observations,
        calculated_at=CALCULATED_AT,
    )
    roi_result = calculate_strategy_roi(adapter_result.economics_input)

    assert isinstance(adapter_result, AdapterResultV1)
    assert adapter_result.contract_version == ADAPTER_CONTRACT_VERSION
    assert adapter_result.economics_input.model_version == MODEL_VERSION
    assert adapter_result.economics_input.reporting_currency == "USD"
    assert adapter_result.economics_input.input_observation_ids
    assert adapter_result.warnings
    assert adapter_result.uncertainty_ranges
    for metric in adapter_result.derived_values:
        assert adapter_result.classifications[metric] is ValueClassification.DERIVED
    for metric_range in adapter_result.uncertainty_ranges.values():
        low = adapter_result.derived_values[metric_range.low_metric]
        base = adapter_result.derived_values[metric_range.base_metric]
        high = adapter_result.derived_values[metric_range.high_metric]
        assert low <= base <= high

    actual = _roi_fields(roi_result)
    assert {field: actual[field] for field in expected} == {
        field: Decimal(value) if value is not None else None for field, value in expected.items()
    }


def test_scenario_yield_preserves_live_config_and_derived_provenance() -> None:
    observations = load_fixture_observations(CALCULATED_AT, strategy=DIMO_SOFTWARE_ONLY_V1)
    adapter_result = ScenarioYieldAdapter(DIMO_SOFTWARE_ONLY_V1).build_engine_input(
        observations,
        calculated_at=CALCULATED_AT,
    )

    assert scenario_metric(DIMO_SOFTWARE_ONLY_V1, REWARD_TOKEN_PRICE_USD) in adapter_result.classifications
    assert (
        adapter_result.classifications[scenario_metric(DIMO_SOFTWARE_ONLY_V1, REWARD_TOKEN_PRICE_USD)]
        is ValueClassification.LIVE
    )
    assert (
        adapter_result.classifications[scenario_metric(DIMO_SOFTWARE_ONLY_V1, GROSS_NOMINAL_VALUE_DAY_USD)]
        is ValueClassification.DERIVED
    )
    assert any(observation.metric.endswith(".source.weekly_baseline_dimo") for observation in observations)
    assert any(observation.source_type == SourceType.OFFICIAL_DOCS for observation in observations)
    assert any(observation.source_type == SourceType.VERIFIED_CONFIG for observation in observations)
    assert set(adapter_result.economics_input.input_observation_ids) == {observation.observation_id for observation in observations}


def test_missing_required_market_price_fails_without_fake_zero_roi() -> None:
    missing_price = Observation(
        observation_id="missing-dimo-price",
        entity_type="asset",
        entity_id=DIMO_SOFTWARE_ONLY_V1.reward.reward_asset_id,
        metric=scenario_metric(DIMO_SOFTWARE_ONLY_V1, REWARD_TOKEN_PRICE_USD),
        value=None,
        unit="USD",
        quote_currency="USD",
        source_provider="coingecko",
        source_type=SourceType.MARKET_API,
        source_locator="coingecko:dimo",
        observed_at=None,
        retrieved_at=CALCULATED_AT,
        fresh_until=CALCULATED_AT,
        status=ObservationStatus.MISSING,
        metadata={"classification": ValueClassification.LIVE.value},
    )
    observations = build_scenario_observations(
        CALCULATED_AT,
        strategy=DIMO_SOFTWARE_ONLY_V1,
        price_observation=missing_price,
    )

    with pytest.raises(AdapterInputError, match="Missing required"):
        ScenarioYieldAdapter(DIMO_SOFTWARE_ONLY_V1).build_engine_input(observations, calculated_at=CALCULATED_AT)
    derived_metrics = {observation.metric for observation in observations}
    assert scenario_metric(DIMO_SOFTWARE_ONLY_V1, GROSS_NOMINAL_VALUE_DAY_USD) not in derived_metrics
    assert scenario_metric(DIMO_SOFTWARE_ONLY_V1, NET_EARNINGS_DAY_USD) not in derived_metrics


def test_zero_market_price_is_rejected_but_zero_cost_assumptions_remain_allowed() -> None:
    zero_price = live_observation(
        provider="fixture-market",
        entity_type="asset",
        entity_id=DIMO_SOFTWARE_ONLY_V1.reward.reward_asset_id,
        metric=scenario_metric(DIMO_SOFTWARE_ONLY_V1, REWARD_TOKEN_PRICE_USD),
        value=Decimal("0"),
        unit="USD",
        source_locator="fixture:coingecko:dimo",
        source_type=SourceType.MARKET_API,
        retrieved_at=CALCULATED_AT,
        observed_at=CALCULATED_AT,
        freshness=timedelta(minutes=5),
    )

    with pytest.raises(AdapterInputError, match="market price must be strictly positive"):
        build_scenario_observations(CALCULATED_AT, strategy=DIMO_SOFTWARE_ONLY_V1, price_observation=zero_price)

    storj = next(strategy for strategy in SCENARIO_YIELD_STRATEGIES if strategy.strategy_id.startswith("storj-"))
    observations = load_fixture_observations(CALCULATED_AT, strategy=storj)
    adapter_result = ScenarioYieldAdapter(storj).build_engine_input(observations, calculated_at=CALCULATED_AT)
    roi_result = calculate_strategy_roi(adapter_result.economics_input)

    assert roi_result.other_cost_day.amount == Decimal("0")
    assert roi_result.transaction_cost_day.amount == Decimal("0.001")


def test_batch1_catalog_admits_only_defensible_models_and_parks_star_atlas() -> None:
    opportunities = {opportunity.opportunity_id: opportunity for opportunity in list_opportunities()}
    strategies = {strategy.strategy_id: strategy for strategy in list_strategies()}

    assert len(opportunities) == 32
    assert len(strategies) == 15
    assert get_opportunity("star-atlas-sage-labs").data_feasibility_status == "PARKED"
    assert get_opportunity("star-atlas-sage-labs").strategy_ids == ()
    assert not any(strategy.opportunity_id == "star-atlas-sage-labs" for strategy in strategies.values())
    assert not {"honeygain", "earnapp", "hivemapper", "sia-hostd"} & set(opportunities)
    assert {
        "storj-existing-hardware-storage-node",
        "geodnet-empty-hex-triple-band-base-station",
        "weatherxm-d1-wifi-station",
        "dimo-software-only-compatible-car",
        "mysterium-b2b-existing-device",
    } <= set(strategies)


def test_batch1_models_do_not_use_competitor_financial_inputs() -> None:
    forbidden_fragments = ("reddit", "youtube", "playtoearn", "dappradar", "roi calculator", "roicalculator")
    model_text = "\n".join(
        "\n".join(
            [
                strategy.description,
                strategy.capital.source_locator,
                strategy.reward.source_locator,
                strategy.costs.source_locator,
                *[source.url for source in strategy.source_references],
                *[metric.source_locator for metric in strategy.support_metrics],
            ]
        ).lower()
        for strategy in SCENARIO_YIELD_STRATEGIES
    )

    for fragment in forbidden_fragments:
        assert fragment not in model_text


def _roi_fields(result) -> dict[str, Decimal | None]:
    return {
        "total_capital": result.total_capital.amount,
        "sunk_cost": result.sunk_cost.amount,
        "recoverable_capital": result.recoverable_capital.amount,
        "capital_at_risk": result.capital_at_risk.amount,
        "gross_nominal_earnings_day": result.gross_nominal_earnings_day.amount,
        "realizable_earnings_day": result.realizable_earnings_day.amount,
        "operating_cost_day": result.operating_cost_day.amount,
        "transaction_cost_day": result.transaction_cost_day.amount,
        "net_earnings_day": result.net_earnings_day.amount,
        "break_even_days": result.break_even.days,
        "roi_total_7d": result.roi_total_7d.value,
        "roi_total_30d": result.roi_total_30d.value,
        "roi_total_90d": result.roi_total_90d.value,
        "roi_risk_7d": result.roi_risk_7d.value,
        "roi_risk_30d": result.roi_risk_30d.value,
        "roi_risk_90d": result.roi_risk_90d.value,
        "exit_adjusted_pnl": result.exit_adjusted_pnl.amount,
    }
