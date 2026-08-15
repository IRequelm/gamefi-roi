from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.splinterlands import (
    BATTLES_PER_DAY,
    CARD_RENTAL_COST_DAY_USD,
    ENERGY_MAX,
    ENERGY_REGEN_PER_HOUR,
    REALIZATION_HAIRCUT_BPS,
    SEASON_END_UNIX,
    SEASON_ID,
    SPELLBOOK_COST_USD,
    SPS_REFERENCE_PRICE_USD,
    SPS_REWARD_PER_WIN,
    TRANSACTION_COST_DAY_USD,
    WIN_PROBABILITY,
    WIN_PROBABILITY_HIGH,
    WIN_PROBABILITY_LOW,
    AdapterInputError,
    SplinterlandsModernRankedAdapter,
    ValueClassification,
    live_observation,
    verified_config_observation,
)
from app.engine.calculator import calculate_strategy_roi
from app.engine.results import MetricStatus
from app.sources.observations import Observation, SourceType
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "splinterlands_modern_ranked_golden.json"


def test_splinterlands_modern_ranked_golden_fixture_matches_manual_expected_roi() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = _observations_from_fixture(fixture["strategy"])
    expected = fixture["manual_expected"]

    adapter_result = SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(
        observations,
        calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )
    result = calculate_strategy_roi(adapter_result.economics_input)

    assert adapter_result.derived_values["splinterlands.modern_ranked.expected_wins_day"] == Decimal(
        expected["expected_wins_day"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.expected_wins_day_low"] == Decimal(
        expected["expected_wins_day_low"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.expected_wins_day_high"] == Decimal(
        expected["expected_wins_day_high"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.expected_sps_day"] == Decimal(
        expected["expected_sps_day"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.expected_sps_day_low"] == Decimal(
        expected["expected_sps_day_low"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.expected_sps_day_high"] == Decimal(
        expected["expected_sps_day_high"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.gross_nominal_value_day_usd"] == Decimal(
        expected["gross_nominal_earnings_day"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.realizable_value_day_usd"] == Decimal(
        expected["realizable_earnings_day"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.realizable_value_day_usd_low"] == Decimal(
        expected["realizable_earnings_day_low"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.realizable_value_day_usd_high"] == Decimal(
        expected["realizable_earnings_day_high"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.net_earnings_day_usd_low"] == Decimal(
        expected["net_earnings_day_low"]
    )
    assert adapter_result.derived_values["splinterlands.modern_ranked.net_earnings_day_usd_high"] == Decimal(
        expected["net_earnings_day_high"]
    )
    assert adapter_result.classifications[SPELLBOOK_COST_USD] == ValueClassification.LIVE
    assert adapter_result.classifications[SPS_REFERENCE_PRICE_USD] == ValueClassification.LIVE
    assert adapter_result.classifications[BATTLES_PER_DAY] == ValueClassification.CONFIG

    assert result.total_capital.amount == Decimal(expected["total_capital"])
    assert result.sunk_cost.amount == Decimal(expected["sunk_cost"])
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


def test_splinterlands_adapter_fails_when_required_observation_is_missing() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = tuple(
        observation for observation in _observations_from_fixture(fixture["strategy"]) if observation.metric != SPS_REWARD_PER_WIN
    )

    with pytest.raises(AdapterInputError, match=SPS_REWARD_PER_WIN):
        SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(observations)


def test_splinterlands_adapter_fails_when_required_observation_is_stale() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = list(_observations_from_fixture(fixture["strategy"]))
    stale = observations[-1].model_copy(update={"fresh_until": datetime(2026, 8, 15, 11, 59, tzinfo=UTC)})
    observations[-1] = stale

    with pytest.raises(AdapterInputError, match="not fresh"):
        SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(
            tuple(observations),
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )


def test_splinterlands_adapter_rejects_probability_range_that_excludes_expected_probability() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = [
        observation.model_copy(update={"value": Decimal("0.70")})
        if observation.metric == WIN_PROBABILITY_LOW
        else observation
        for observation in _observations_from_fixture(fixture["strategy"])
    ]

    with pytest.raises(AdapterInputError, match="inside the configured low/high range"):
        SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(
            tuple(observations),
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )


def test_splinterlands_adapter_rejects_ended_season() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    observations = [
        observation.model_copy(update={"value": Decimal("1786780000")})
        if observation.metric == SEASON_END_UNIX
        else observation
        for observation in _observations_from_fixture(fixture["strategy"])
    ]

    with pytest.raises(AdapterInputError, match="season end"):
        SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(
            tuple(observations),
            calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        )


def _observations_from_fixture(payload: dict[str, str]) -> tuple[Observation, ...]:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    strategy_id = SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id
    live = (
        _live(SPELLBOOK_COST_USD, payload["spellbook_cost_usd"], "USD", now, entity_type="game", entity_id="splinterlands"),
        _live(SEASON_ID, payload["season_id"], "season", now, entity_type="season", entity_id="splinterlands:season:189"),
        _live(
            SEASON_END_UNIX,
            payload["season_end_unix"],
            "unix_second",
            now,
            entity_type="season",
            entity_id="splinterlands:season:189",
        ),
        _live(ENERGY_MAX, payload["energy_max"], "energy", now, entity_type="game", entity_id="splinterlands"),
        _live(
            ENERGY_REGEN_PER_HOUR,
            payload["energy_regen_per_hour"],
            "energy/hour",
            now,
            entity_type="game",
            entity_id="splinterlands",
        ),
        _live(
            SPS_REFERENCE_PRICE_USD,
            payload["sps_reference_price_usd"],
            "USD",
            now,
            entity_type="asset",
            entity_id="splinterlands:sps",
            source_provider="coingecko",
            source_type=SourceType.MARKET_API,
        ),
    )
    configs = (
        _config(strategy_id, BATTLES_PER_DAY, payload["battles_per_day"], "battle/day", now),
        _config(strategy_id, WIN_PROBABILITY, payload["win_probability"], "probability", now),
        _config(strategy_id, WIN_PROBABILITY_LOW, payload["win_probability_low"], "probability", now),
        _config(strategy_id, WIN_PROBABILITY_HIGH, payload["win_probability_high"], "probability", now),
        _config(strategy_id, SPS_REWARD_PER_WIN, payload["sps_reward_per_win"], "SPS", now),
        _config(strategy_id, REALIZATION_HAIRCUT_BPS, payload["realization_haircut_bps"], "basis_point", now),
        _config(strategy_id, CARD_RENTAL_COST_DAY_USD, payload["card_rental_cost_day_usd"], "USD", now),
        _config(strategy_id, TRANSACTION_COST_DAY_USD, payload["transaction_cost_day_usd"], "USD", now),
    )
    return (*live, *configs)


def _live(
    metric: str,
    value: str,
    unit: str,
    retrieved_at: datetime,
    *,
    entity_type: str,
    entity_id: str,
    source_provider: str = "splinterlands",
    source_type: SourceType = SourceType.OFFICIAL_API,
) -> Observation:
    return live_observation(
        provider=source_provider,
        entity_type=entity_type,
        entity_id=entity_id,
        metric=metric,
        value=Decimal(value),
        unit=unit,
        source_locator=f"fixture:{metric}",
        source_type=source_type,
        retrieved_at=retrieved_at,
        observed_at=retrieved_at,
        freshness=timedelta(minutes=5),
    )


def _config(strategy_id: str, metric: str, value: str, unit: str, retrieved_at: datetime) -> Observation:
    return verified_config_observation(
        strategy_id=strategy_id,
        metric=metric,
        value=value,
        unit=unit,
        source_locator="fixture:splinterlands-modern-ranked",
        retrieved_at=retrieved_at,
    )
