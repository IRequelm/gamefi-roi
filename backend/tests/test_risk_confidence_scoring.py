from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.recalculation import ScheduledRecalculator
from app.risk.results import ConfidenceLabel, METHODOLOGY_VERSION, RiskLabel
from app.risk.scoring import SnapshotScorer
from app.storage.history import CalculationWindow, HistoryRepository, StrategySnapshot
from app.storage.scoring import ScoringRepository
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from test_history_storage import _dfk_calculation, _migrated_engine

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def test_high_confidence_low_risk_scenario_marks_missing_history_unavailable() -> None:
    snapshot = _snapshot(
        refs=(
            _ref("obs-price", "token.price", "market_api", "2.00"),
            _ref("obs-reward", "strategy.reward_rate", "onchain", "5"),
            _ref("obs-entry", "entry.value", "onchain", "100"),
        ),
        gross="10",
        realizable="10",
        net="10",
        total="100",
        recoverable="95",
        break_even="10",
        roi_30d="3.0",
    )

    score = SnapshotScorer().score(snapshot, history=(), scored_at=NOW)

    assert score.methodology_version == METHODOLOGY_VERSION
    assert score.confidence.label == ConfidenceLabel.HIGH
    assert score.confidence.score >= 95
    assert score.risk.label == RiskLabel.LOW
    assert score.risk.score <= 10
    assert any(factor.factor == "roi_yield_deterioration_trend" for factor in score.risk.unavailable_factors)


def test_high_confidence_high_risk_lock_exit_penalty_is_independent() -> None:
    snapshot = _snapshot(
        refs=(
            _ref("obs-price", "token.price", "market_api", "2.00", locator="dex:quote_exact_input"),
            _ref("obs-lock", "strategy.lock_days", "onchain", "1095"),
            _ref("obs-reward", "strategy.reward_rate", "onchain", "5"),
        ),
        gross="10",
        realizable="8",
        net="1",
        total="100",
        recoverable="40",
        break_even="100",
        roi_30d="0.30",
        assumptions={"emergency_withdrawal_penalty_bps": 5000},
    )

    score = SnapshotScorer().score(snapshot, scored_at=NOW)

    assert score.confidence.label == ConfidenceLabel.HIGH
    assert score.risk.label == RiskLabel.VERY_HIGH
    assert _contribution(score.risk.contributions, "lock_exit_penalty").points == 35


def test_low_confidence_scenario_from_stale_data_and_incomplete_provenance() -> None:
    refs = tuple(
        _ref(f"obs-config-{index}", f"strategy.config_{index}", "verified_config", str(index), status="stale")
        for index in range(8)
    ) + (
        _ref("obs-live", "token.price", "market_api", "1.00"),
        {"observation_id": "obs-bad", "metric": "broken.metric", "source_type": "verified_config"},
    )
    snapshot = _snapshot(
        refs=refs,
        gross="1",
        realizable="0.5",
        net="0.1",
        total="100",
        recoverable="20",
        break_even="1000",
        roi_30d="0.03",
        stale=8,
    )

    score = SnapshotScorer().score(snapshot, scored_at=NOW)

    assert score.confidence.label == ConfidenceLabel.LOW
    assert _contribution(score.confidence.contributions, "freshness").points > 0
    assert _contribution(score.confidence.contributions, "provenance_completeness").points > 0
    assert _contribution(score.confidence.contributions, "config_dependence").points > 0


def test_heavy_config_dependence_penalizes_confidence_more_than_live_inputs() -> None:
    live_snapshot = _snapshot(
        refs=tuple(_ref(f"obs-live-{index}", f"metric.{index}", "onchain", "1") for index in range(8)),
    )
    config_snapshot = _snapshot(
        refs=tuple(_ref(f"obs-config-{index}", f"metric.{index}", "verified_config", "1") for index in range(8)),
    )

    live_score = SnapshotScorer().score(live_snapshot, scored_at=NOW)
    config_score = SnapshotScorer().score(config_snapshot, scored_at=NOW)

    assert live_score.confidence.score > config_score.confidence.score
    assert _contribution(config_score.confidence.contributions, "config_dependence").points >= 20
    assert _contribution(config_score.risk.contributions, "config_dependence").points >= 15


def test_poor_liquidity_and_slippage_add_risk_contribution() -> None:
    snapshot = _snapshot(
        refs=(
            _ref("obs-quote", "reward.realizable_quote", "market_api", "75", locator="dex:quote_exact_input"),
            _ref("obs-volume", "alcor.market.volume_usd_24h", "market_api", "500"),
        ),
        gross="100",
        realizable="75",
        assumptions={"capital_at_risk_basis": "entry value while market liquidity remains thin"},
    )

    score = SnapshotScorer().score(snapshot, scored_at=NOW)
    liquidity = _contribution(score.risk.contributions, "liquidity_exit_quality")

    assert liquidity.points == 35
    assert liquidity.evidence["thin_liquidity_text"] is True


def test_probabilistic_uncertainty_affects_both_scores() -> None:
    snapshot = _snapshot(
        refs=(
            _ref("obs-price", "token.price", "market_api", "0.01"),
            _ref("obs-win", "strategy.win_probability", "verified_config", "0.55"),
        ),
        gross="0.0275",
        realizable="0.027225",
        net="0.017225",
        total="10",
        recoverable="0",
        break_even="580.55",
        roi_30d="0.051675",
        derived_values={
            "expected_sps_day_low": "2.25",
            "expected_sps_day": "2.75",
            "expected_sps_day_high": "3.25",
        },
        uncertainty_ranges={
            "expected_sps_day": {
                "low_metric": "expected_sps_day_low",
                "base_metric": "expected_sps_day",
                "high_metric": "expected_sps_day_high",
            }
        },
        warnings=(
            {
                "code": "expected_value_not_guaranteed",
                "message": "Expected value is not guaranteed.",
                "severity": "warning",
            },
        ),
        assumptions={"expected_value_only": "Expected rewards are not guaranteed.", "probability_basis": "configured"},
    )

    score = SnapshotScorer().score(snapshot, scored_at=NOW)

    assert _contribution(score.confidence.contributions, "model_uncertainty").points > 0
    assert _contribution(score.risk.contributions, "probabilistic_uncertainty").points >= 20
    assert score.risk.label == RiskLabel.VERY_HIGH


def test_history_deterioration_uses_history_only_when_available() -> None:
    first = _snapshot(snapshot_id="snap-1", net="10", calculated_at=NOW - timedelta(days=2))
    second = _snapshot(snapshot_id="snap-2", net="8", calculated_at=NOW - timedelta(days=1))
    latest = _snapshot(snapshot_id="snap-3", net="4", calculated_at=NOW)

    score = SnapshotScorer().score(latest, history=(first, second, latest), scored_at=NOW)

    assert _contribution(score.risk.contributions, "roi_yield_deterioration_trend").points == 25
    assert not any(factor.factor == "roi_yield_deterioration_trend" for factor in score.risk.unavailable_factors)


def test_score_persistence_is_snapshot_and_methodology_versioned(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "scores.db")
    history_repository = HistoryRepository(engine)
    scoring_repository = ScoringRepository(engine)
    fixture_time = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    adapter_result, roi_result, observations = _dfk_calculation(fixture_time)
    snapshot = history_repository.save_snapshot(
        adapter_result=adapter_result,
        roi_result=roi_result,
        observations=observations,
        calculated_at=fixture_time,
        intended_window=CalculationWindow(fixture_time, fixture_time + timedelta(minutes=5)),
    )
    score = SnapshotScorer().score(snapshot, scored_at=fixture_time)

    saved = scoring_repository.save_score(score)
    duplicate = scoring_repository.save_score(score)
    next_methodology = scoring_repository.save_score(replace(score, methodology_version="risk-confidence-v2-test"))

    assert duplicate.snapshot_id == saved.snapshot_id
    assert duplicate.methodology_version == saved.methodology_version
    assert scoring_repository.get_score(snapshot.snapshot_id) == saved
    assert next_methodology.methodology_version == "risk-confidence-v2-test"


def test_existing_three_adapters_score_distinct_risk_and_confidence(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "adapter-scores.db")
    history_repository = HistoryRepository(engine)
    calculated_at = NOW
    run = ScheduledRecalculator(history_repository).run_once(
        build_history_probe_tasks(),
        intended_window=CalculationWindow(calculated_at, calculated_at + timedelta(minutes=5)),
        calculated_at=calculated_at,
    )
    scores = {
        score.strategy_id: score
        for score in (
            SnapshotScorer().score(snapshot, history=run.snapshots, scored_at=calculated_at)
            for snapshot in run.snapshots
        )
    }

    dfk = scores[DFK_CJEWEL_MAX_LOCK_V1.strategy_id]
    farmers = scores[FARMERS_WORLD_AXE_WOOD_V1.strategy_id]
    splinterlands = scores[SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id]

    assert dfk.confidence.label == ConfidenceLabel.HIGH
    assert dfk.risk.label == RiskLabel.VERY_HIGH
    assert farmers.confidence.score < dfk.confidence.score
    assert farmers.risk.label == RiskLabel.MEDIUM
    assert splinterlands.confidence.score < dfk.confidence.score
    assert splinterlands.risk.label == RiskLabel.VERY_HIGH
    assert _contribution(splinterlands.risk.contributions, "probabilistic_uncertainty").points > 0


def _snapshot(
    *,
    snapshot_id: str = "snapshot-test",
    refs: tuple[dict, ...] = (),
    gross: str = "10",
    realizable: str = "10",
    net: str = "10",
    total: str = "100",
    recoverable: str = "95",
    break_even: str = "10",
    roi_30d: str = "3.0",
    derived_values: dict | None = None,
    uncertainty_ranges: dict | None = None,
    warnings: tuple[dict, ...] = (),
    assumptions: dict | None = None,
    stale: int = 0,
    calculated_at: datetime = NOW,
) -> StrategySnapshot:
    references = {reference["observation_id"]: reference for reference in refs}
    input_ids = tuple(references)
    fresh_count = max(0, len(input_ids) - stale)
    config_count = sum(1 for reference in references.values() if reference.get("source_type") == "verified_config")
    live_count = sum(1 for reference in references.values() if reference.get("source_type") in {"onchain", "official_api", "market_api"})
    return StrategySnapshot(
        snapshot_id=snapshot_id,
        idempotency_key=f"idempotency-{snapshot_id}",
        strategy_id="strategy-test",
        strategy_version="v1",
        adapter_contract_version="adapter-contract-v1",
        model_version="roi-core-v1",
        calculated_at=calculated_at,
        intended_window=CalculationWindow(calculated_at, calculated_at + timedelta(minutes=5)),
        reporting_currency="USD",
        capital_metrics={
            "total_capital": {"amount": total, "currency": "USD"},
            "sunk_cost": {"amount": "0", "currency": "USD"},
            "recoverable_capital": {"amount": recoverable, "currency": "USD"},
            "capital_at_risk": {"amount": total, "currency": "USD"},
        },
        earnings_cost_metrics={
            "gross_nominal_earnings_day": {"amount": gross, "currency": "USD"},
            "realizable_earnings_day": {"amount": realizable, "currency": "USD"},
            "operating_cost_day": {"amount": "0", "currency": "USD"},
            "transaction_cost_day": {"amount": "1", "currency": "USD"},
            "other_cost_day": {"amount": "0", "currency": "USD"},
            "net_earnings_day": {"amount": net, "currency": "USD"},
        },
        roi_outputs={
            "break_even": {
                "basis": "total_capital",
                "recovery_target": {"amount": total, "currency": "USD"},
                "days": break_even,
                "status": "available",
                "reason": None,
            },
            "roi_total_7d": {"value": "0.7", "status": "available", "reason": None},
            "roi_total_30d": {"value": roi_30d, "status": "available", "reason": None},
            "roi_total_90d": {"value": "9.0", "status": "available", "reason": None},
            "roi_risk_7d": {"value": "0.7", "status": "available", "reason": None},
            "roi_risk_30d": {"value": roi_30d, "status": "available", "reason": None},
            "roi_risk_90d": {"value": "9.0", "status": "available", "reason": None},
            "exit_adjusted_pnl": {"amount": "-5", "currency": "USD"},
        },
        adapter_derived_values=derived_values or {},
        uncertainty_ranges=uncertainty_ranges or {},
        warnings=warnings,
        classification_summary={
            "counts": {"LIVE": live_count, "CONFIG": config_count, "DERIVED": 0},
            "metrics": {reference.get("metric", f"metric-{index}"): reference.get("metadata", {}).get("classification", "LIVE") for index, reference in enumerate(references.values())},
        },
        input_observation_ids=input_ids,
        input_observation_references=references,
        freshness_summary={
            "calculated_at": calculated_at.isoformat(),
            "input_count": len(input_ids),
            "status_counts": {"fresh": fresh_count, "stale": stale, "invalid": 0, "missing": 0},
        },
        assumptions=assumptions or {},
        created_at=calculated_at,
    )


def _ref(
    observation_id: str,
    metric: str,
    source_type: str,
    value: str,
    *,
    status: str = "fresh",
    locator: str = "fixture:source",
) -> dict:
    return {
        "observation_id": observation_id,
        "entity_type": "strategy",
        "entity_id": "strategy-test",
        "metric": metric,
        "value": value,
        "unit": "USD",
        "quote_currency": "USD",
        "source_provider": "fixture",
        "source_type": source_type,
        "source_locator": locator,
        "observed_at": NOW.isoformat(),
        "retrieved_at": NOW.isoformat(),
        "fresh_until": (NOW + timedelta(minutes=5)).isoformat(),
        "stored_status": status,
        "status_at_calculation": status,
        "metadata": {"classification": "CONFIG" if source_type == "verified_config" else "LIVE"},
    }


def _contribution(contributions, factor: str):
    for contribution in contributions:
        if contribution.factor == factor:
            return contribution
    raise AssertionError(f"Missing contribution factor: {factor}")
