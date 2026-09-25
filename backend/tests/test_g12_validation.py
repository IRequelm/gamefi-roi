from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import re

import pytest

from app.adapters.contract import AdapterInputError
from app.adapters.defi_kingdoms_jeweler import (
    ENTRY_VALUE_USD as DFK_ENTRY_VALUE_USD,
    REWARD_REALIZABLE_VALUE_USD,
    DfkJewelerAdapter,
)
from app.engine.calculator import calculate_strategy_roi
from app.storage.history import HistoryRepository
from app.validation.e2e import (
    ManualValidationError,
    assert_manual_matches_expected,
    load_golden_fixture,
    manual_common_outputs,
    manual_from_golden_fixture,
    manual_from_snapshot_references,
)
from test_api_v1 import NOW, _seed_snapshots_and_scores, _seeded_client
from test_dfk_jeweler_adapter import _observations_from_fixture as dfk_observations
from test_farmers_world_adapter import _observations_from_fixture as farmers_observations
from test_splinterlands_adapter import _observations_from_fixture as splinterlands_observations
from app.adapters.farmers_world import FarmersWorldAxeAdapter
from app.adapters.splinterlands import SplinterlandsModernRankedAdapter
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1


STRATEGY_IDS = (
    DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
    FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
    SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
)
FIXTURE_CALCULATED_AT = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

CORE_FIELDS = (
    "total_capital",
    "recoverable_capital",
    "capital_at_risk",
    "gross_nominal_earnings_day",
    "realizable_earnings_day",
    "operating_cost_day",
    "transaction_cost_day",
    "net_earnings_day",
    "break_even_days",
    "roi_total_7d",
    "roi_total_30d",
    "roi_total_90d",
    "roi_risk_7d",
    "roi_risk_30d",
    "roi_risk_90d",
    "exit_adjusted_pnl",
)


@pytest.mark.parametrize("strategy_id", STRATEGY_IDS)
def test_g12_independent_manual_fixture_matches_expected_values(strategy_id: str) -> None:
    result = manual_from_golden_fixture(strategy_id)
    expected = load_golden_fixture(strategy_id)["manual_expected"]

    assert_manual_matches_expected(result, expected, fields=tuple(field for field in CORE_FIELDS if field in expected))


@pytest.mark.parametrize("strategy_id", STRATEGY_IDS)
def test_g12_manual_fixture_matches_adapter_and_engine_output(strategy_id: str) -> None:
    fixture = load_golden_fixture(strategy_id)
    manual = manual_from_golden_fixture(strategy_id).metrics
    adapter_result, engine_result = _fixture_engine_result(strategy_id, fixture["strategy"])

    assert engine_result.total_capital.amount == manual["total_capital"]
    assert engine_result.recoverable_capital.amount == manual["recoverable_capital"]
    assert engine_result.capital_at_risk.amount == manual["capital_at_risk"]
    assert engine_result.gross_nominal_earnings_day.amount == manual["gross_nominal_earnings_day"]
    assert engine_result.realizable_earnings_day.amount == manual["realizable_earnings_day"]
    assert engine_result.operating_cost_day.amount == manual["operating_cost_day"]
    assert engine_result.transaction_cost_day.amount == manual["transaction_cost_day"]
    assert engine_result.net_earnings_day.amount == manual["net_earnings_day"]
    assert engine_result.break_even.days == manual["break_even_days"]
    assert engine_result.roi_total_30d.value == manual["roi_total_30d"]
    assert engine_result.roi_risk_30d.value == manual["roi_risk_30d"]
    assert engine_result.exit_adjusted_pnl.amount == manual["exit_adjusted_pnl"]
    assert set(adapter_result.economics_input.input_observation_ids)


def test_g12_snapshot_api_values_match_independent_snapshot_references(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "g12-pipeline.db")
    repository = HistoryRepository(engine)
    expected_scores = {
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id: (82, "HIGH", 79, "VERY HIGH"),
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id: (77, "MODERATE", 31, "MEDIUM"),
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id: (39, "LOW", 100, "VERY HIGH"),
    }

    for strategy_id in STRATEGY_IDS:
        snapshot = repository.latest_snapshot(strategy_id)
        assert snapshot is not None
        manual = manual_from_snapshot_references(strategy_id, snapshot.input_observation_references).metrics
        response = client.get(f"/api/v1/strategies/{strategy_id}/latest")
        assert response.status_code == 200
        payload = response.json()

        assert _money_decimal(snapshot.capital_metrics, "total_capital") == manual["total_capital"]
        assert _money_decimal(snapshot.earnings_cost_metrics, "net_earnings_day") == manual["net_earnings_day"]
        assert _ratio_decimal(snapshot.roi_outputs, "roi_total_30d") == manual["roi_total_30d"]
        assert _money_decimal(snapshot.roi_outputs, "exit_adjusted_pnl") == manual["exit_adjusted_pnl"]

        assert payload["capital"]["total_capital"] == snapshot.capital_metrics["total_capital"]
        assert payload["earnings"]["net_earnings_day"] == snapshot.earnings_cost_metrics["net_earnings_day"]
        assert payload["roi"]["roi_total_30d"] == snapshot.roi_outputs["roi_total_30d"]
        assert payload["roi"]["exit_adjusted_pnl"] == snapshot.roi_outputs["exit_adjusted_pnl"]
        assert payload["freshness"]["overall_status"] == "fresh"

        confidence, confidence_label, risk, risk_label = expected_scores[strategy_id]
        assert payload["confidence"]["score"] == confidence
        assert payload["confidence"]["label"] == confidence_label
        assert payload["risk"]["score"] == risk
        assert payload["risk"]["label"] == risk_label


def test_g12_history_versions_provenance_and_ordering_are_preserved(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "g12-history.db")
    _seed_snapshots_and_scores(engine, calculated_at=NOW + timedelta(hours=1))
    repository = HistoryRepository(engine)
    history = repository.ordered_time_series(
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        start=NOW - timedelta(minutes=1),
        end=NOW + timedelta(hours=2),
        strategy_version=DFK_CJEWEL_MAX_LOCK_V1.strategy_version,
        model_version="roi-core-v1",
    )

    assert len(history) == 2
    assert [snapshot.calculated_at for snapshot in history] == sorted(snapshot.calculated_at for snapshot in history)
    assert {snapshot.adapter_contract_version for snapshot in history} == {"adapter-contract-v1"}
    assert {snapshot.model_version for snapshot in history} == {"roi-core-v1"}
    assert history[0].snapshot_id != history[1].snapshot_id
    assert all(snapshot.input_observation_references for snapshot in history)

    response = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/history")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"]["total"] == 2
    assert [item["snapshot_id"] for item in payload["items"]] == [snapshot.snapshot_id for snapshot in history]


def test_g12_required_missing_and_stale_inputs_fail_explicitly() -> None:
    fixture = load_golden_fixture(DFK_CJEWEL_MAX_LOCK_V1.strategy_id)
    observations = dfk_observations(fixture["strategy"])
    missing_entry_value = tuple(observation for observation in observations if observation.metric != DFK_ENTRY_VALUE_USD)
    stale_reward = tuple(
        observation.model_copy(update={"fresh_until": observation.retrieved_at - timedelta(seconds=1)})
        if observation.metric == REWARD_REALIZABLE_VALUE_USD
        else observation
        for observation in observations
    )

    with pytest.raises(AdapterInputError, match=DFK_ENTRY_VALUE_USD):
        DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(missing_entry_value)

    with pytest.raises(AdapterInputError, match="not fresh"):
        DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(stale_reward)


def test_g12_adversarial_edge_cases_are_explicit_and_decimal_safe() -> None:
    zero_liquidity = manual_common_outputs(
        sunk_cost=Decimal("0"),
        recoverable_entry_cost=Decimal("10"),
        current_recoverable_value=Decimal("10"),
        initial_operating_reserve=Decimal("0"),
        capital_at_risk=Decimal("10"),
        gross_nominal_earnings_day=Decimal("1"),
        realizable_earnings_day=Decimal("0"),
        operating_cost_day=Decimal("0"),
        transaction_cost_day=Decimal("0"),
        other_cost_day=Decimal("0"),
        cumulative_net_cash_earnings=Decimal("0"),
        total_cash_invested_to_date=Decimal("10"),
    )
    assert zero_liquidity["break_even_days"] is None
    assert zero_liquidity["roi_total_30d"] == Decimal("0")

    extreme_slippage = manual_common_outputs(
        sunk_cost=Decimal("0"),
        recoverable_entry_cost=Decimal("100"),
        current_recoverable_value=Decimal("80"),
        initial_operating_reserve=Decimal("0"),
        capital_at_risk=Decimal("100"),
        gross_nominal_earnings_day=Decimal("100"),
        realizable_earnings_day=Decimal("1"),
        operating_cost_day=Decimal("0"),
        transaction_cost_day=Decimal("0.10"),
        other_cost_day=Decimal("0"),
        cumulative_net_cash_earnings=Decimal("0"),
        total_cash_invested_to_date=Decimal("100"),
    )
    assert extreme_slippage["net_earnings_day"] == Decimal("0.90")
    assert extreme_slippage["exit_adjusted_pnl"] == Decimal("-20")

    price_collapse_negative_net = manual_common_outputs(
        sunk_cost=Decimal("10"),
        recoverable_entry_cost=Decimal("0"),
        current_recoverable_value=Decimal("0"),
        initial_operating_reserve=Decimal("0"),
        capital_at_risk=Decimal("10"),
        gross_nominal_earnings_day=Decimal("0"),
        realizable_earnings_day=Decimal("0"),
        operating_cost_day=Decimal("0.10"),
        transaction_cost_day=Decimal("0"),
        other_cost_day=Decimal("0"),
        cumulative_net_cash_earnings=Decimal("0"),
        total_cash_invested_to_date=Decimal("10"),
    )
    assert price_collapse_negative_net["net_earnings_day"] == Decimal("-0.10")
    assert price_collapse_negative_net["break_even_days"] is None
    assert price_collapse_negative_net["roi_total_30d"] == Decimal("-0.30")

    zero_denominator = manual_common_outputs(
        sunk_cost=Decimal("0"),
        recoverable_entry_cost=Decimal("0"),
        current_recoverable_value=Decimal("0"),
        initial_operating_reserve=Decimal("0"),
        capital_at_risk=Decimal("0"),
        gross_nominal_earnings_day=Decimal("1"),
        realizable_earnings_day=Decimal("1"),
        operating_cost_day=Decimal("0"),
        transaction_cost_day=Decimal("0"),
        other_cost_day=Decimal("0"),
        cumulative_net_cash_earnings=Decimal("0"),
        total_cash_invested_to_date=Decimal("0"),
    )
    assert zero_denominator["roi_total_30d"] is None
    assert zero_denominator["roi_risk_30d"] is None

    tiny_capital_high_roi = manual_common_outputs(
        sunk_cost=Decimal("0"),
        recoverable_entry_cost=Decimal("0.01"),
        current_recoverable_value=Decimal("0"),
        initial_operating_reserve=Decimal("0"),
        capital_at_risk=Decimal("0.01"),
        gross_nominal_earnings_day=Decimal("1"),
        realizable_earnings_day=Decimal("1"),
        operating_cost_day=Decimal("0"),
        transaction_cost_day=Decimal("0"),
        other_cost_day=Decimal("0"),
        cumulative_net_cash_earnings=Decimal("0"),
        total_cash_invested_to_date=Decimal("0.01"),
    )
    assert tiny_capital_high_roi["roi_total_30d"] == Decimal("3000")

    with pytest.raises(ManualValidationError, match="non-negative"):
        manual_common_outputs(
            sunk_cost=Decimal("0"),
            recoverable_entry_cost=Decimal("-1"),
            current_recoverable_value=Decimal("0"),
            initial_operating_reserve=Decimal("0"),
            capital_at_risk=Decimal("0"),
            gross_nominal_earnings_day=Decimal("0"),
            realizable_earnings_day=Decimal("0"),
            operating_cost_day=Decimal("0"),
            transaction_cost_day=Decimal("0"),
            other_cost_day=Decimal("0"),
            cumulative_net_cash_earnings=Decimal("0"),
            total_cash_invested_to_date=Decimal("0"),
        )


def test_g12_frontend_source_does_not_recompute_financial_metrics() -> None:
    source = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "app.js"
    text = source.read_text(encoding="utf-8")

    assert "parseFloat" not in text
    number_casts = re.findall(r"\bNumber\s*\(([^()]*)\)", text)
    assert number_casts == ["opportunity.strategy_count || 0"]
    assert "decimalStringToPercent" not in text


def _fixture_engine_result(strategy_id: str, payload: dict[str, str]):
    if strategy_id == DFK_CJEWEL_MAX_LOCK_V1.strategy_id:
        adapter_result = DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(
            dfk_observations(payload),
            calculated_at=FIXTURE_CALCULATED_AT,
        )
    elif strategy_id == FARMERS_WORLD_AXE_WOOD_V1.strategy_id:
        adapter_result = FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1).build_engine_input(
            farmers_observations(payload),
            calculated_at=FIXTURE_CALCULATED_AT,
        )
    elif strategy_id == SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id:
        adapter_result = SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(
            splinterlands_observations(payload),
            calculated_at=FIXTURE_CALCULATED_AT,
        )
    else:
        raise AssertionError(f"Unsupported strategy {strategy_id}")
    return adapter_result, calculate_strategy_roi(adapter_result.economics_input)


def _money_decimal(payload: dict, metric: str) -> Decimal:
    return Decimal(str(payload[metric]["amount"]))


def _ratio_decimal(payload: dict, metric: str) -> Decimal | None:
    value = payload[metric]["value"]
    return None if value is None else Decimal(str(value))
