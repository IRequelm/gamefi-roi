from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from alembic import command
from sqlalchemy import create_engine

from app.adapters.contract import AdapterResultV1
from app.adapters.defi_kingdoms_jeweler import DfkJewelerAdapter, REWARD_REALIZABLE_VALUE_USD
from app.adapters.farmers_world import FarmersWorldAxeAdapter
from app.adapters.splinterlands import SplinterlandsModernRankedAdapter
from app.config.settings import get_settings
from app.doctor.checks import build_alembic_config
from app.engine.calculator import calculate_strategy_roi
from app.jobs.recalculation import ScheduledRecalculator, StrategyCalculationTask
from app.sources.observations import Observation
from app.storage.history import CalculationWindow, HistoryRepository
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from test_dfk_jeweler_adapter import FIXTURE_PATH as DFK_FIXTURE_PATH
from test_dfk_jeweler_adapter import _observations_from_fixture as dfk_observations
from test_farmers_world_adapter import FIXTURE_PATH as FARMERS_FIXTURE_PATH
from test_farmers_world_adapter import _observations_from_fixture as farmers_observations
from test_splinterlands_adapter import FIXTURE_PATH as SPLINTERLANDS_FIXTURE_PATH
from test_splinterlands_adapter import _observations_from_fixture as splinterlands_observations

CALCULATED_AT = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def test_snapshot_persistence_preserves_reproducibility_payload(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "history.db")
    repository = HistoryRepository(engine)
    adapter_result, roi_result, observations = _dfk_calculation(CALCULATED_AT)
    window = CalculationWindow(CALCULATED_AT, CALCULATED_AT + timedelta(minutes=5))

    snapshot = repository.save_snapshot(
        adapter_result=adapter_result,
        roi_result=roi_result,
        observations=observations,
        calculated_at=CALCULATED_AT,
        intended_window=window,
    )

    assert snapshot.strategy_id == DFK_CJEWEL_MAX_LOCK_V1.strategy_id
    assert snapshot.strategy_version == DFK_CJEWEL_MAX_LOCK_V1.strategy_version
    assert snapshot.adapter_contract_version == "adapter-contract-v1"
    assert snapshot.model_version == "roi-core-v1"
    assert snapshot.capital_metrics["total_capital"] == {
        "amount": str(roi_result.total_capital.amount),
        "currency": "USD",
    }
    assert snapshot.earnings_cost_metrics["net_earnings_day"]["amount"] == str(roi_result.net_earnings_day.amount)
    assert snapshot.roi_outputs["break_even"]["days"] == str(roi_result.break_even.days)
    assert snapshot.input_observation_ids == roi_result.input_observation_ids
    assert snapshot.freshness_summary["status_counts"]["fresh"] == len(roi_result.input_observation_ids)
    assert snapshot.classification_summary["counts"]["CONFIG"] == 3
    assert snapshot.classification_summary["counts"]["LIVE"] == 2
    assert snapshot.classification_summary["counts"]["DERIVED"] >= 4
    first_reference = snapshot.input_observation_references[roi_result.input_observation_ids[0]]
    assert first_reference["source_provider"] == "verified-config"
    assert first_reference["status_at_calculation"] == "fresh"
    assert snapshot.assumptions["claim_interval_days"] == 1


def test_latest_snapshot_ordered_history_and_idempotent_duplicate(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "ordered.db")
    repository = HistoryRepository(engine)
    first_time = CALCULATED_AT
    second_time = CALCULATED_AT + timedelta(minutes=4)

    first_adapter_result, first_roi_result, first_observations = _dfk_calculation(first_time)
    second_adapter_result, second_roi_result, second_observations = _dfk_calculation(second_time)
    first_window = CalculationWindow(first_time, first_time + timedelta(minutes=1))
    second_window = CalculationWindow(second_time, second_time + timedelta(minutes=1))

    first = repository.save_snapshot(
        adapter_result=first_adapter_result,
        roi_result=first_roi_result,
        observations=first_observations,
        calculated_at=first_time,
        intended_window=first_window,
    )
    duplicate = repository.save_snapshot(
        adapter_result=first_adapter_result,
        roi_result=first_roi_result,
        observations=first_observations,
        calculated_at=first_time,
        intended_window=first_window,
    )
    second = repository.save_snapshot(
        adapter_result=second_adapter_result,
        roi_result=second_roi_result,
        observations=second_observations,
        calculated_at=second_time,
        intended_window=second_window,
    )

    assert duplicate.snapshot_id == first.snapshot_id
    latest = repository.latest_snapshot(DFK_CJEWEL_MAX_LOCK_V1.strategy_id)
    history = repository.ordered_time_series(
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        start=first_time - timedelta(minutes=1),
        end=second_time + timedelta(minutes=1),
    )

    assert latest is not None
    assert latest.snapshot_id == second.snapshot_id
    assert [snapshot.snapshot_id for snapshot in history] == [first.snapshot_id, second.snapshot_id]


def test_strategy_and_model_version_changes_are_retained(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "versions.db")
    repository = HistoryRepository(engine)
    adapter_result, roi_result, observations = _dfk_calculation(CALCULATED_AT)
    window = CalculationWindow(CALCULATED_AT, CALCULATED_AT + timedelta(minutes=5))

    base = repository.save_snapshot(
        adapter_result=adapter_result,
        roi_result=roi_result,
        observations=observations,
        calculated_at=CALCULATED_AT,
        intended_window=window,
    )
    versioned_adapter_result, versioned_roi_result = _versioned_result(adapter_result, "v2", "roi-core-v2-test")
    versioned = repository.save_snapshot(
        adapter_result=versioned_adapter_result,
        roi_result=versioned_roi_result,
        observations=observations,
        calculated_at=CALCULATED_AT,
        intended_window=window,
    )
    version_info = repository.strategy_version_info(DFK_CJEWEL_MAX_LOCK_V1.strategy_id)

    assert base.snapshot_id != versioned.snapshot_id
    assert {(item.strategy_version, item.model_version, item.snapshot_count) for item in version_info} == {
        ("v1", "roi-core-v1", 1),
        ("v2", "roi-core-v2-test", 1),
    }


def test_snapshot_preserves_uncertainty_ranges_and_warnings(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "uncertainty.db")
    repository = HistoryRepository(engine)
    adapter_result, roi_result, observations = _splinterlands_calculation(CALCULATED_AT)
    snapshot = repository.save_snapshot(
        adapter_result=adapter_result,
        roi_result=roi_result,
        observations=observations,
        calculated_at=CALCULATED_AT,
        intended_window=CalculationWindow(CALCULATED_AT, CALCULATED_AT + timedelta(minutes=5)),
    )

    assert "splinterlands.modern_ranked.expected_sps_day" in snapshot.uncertainty_ranges
    assert snapshot.warnings[0]["code"] == "expected_value_not_guaranteed"
    assert snapshot.adapter_derived_values["splinterlands.modern_ranked.net_earnings_day_usd_low"] == "0.01227500"


def test_recalculation_failure_isolation_records_failure_without_fake_snapshot(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "failure-isolation.db")
    repository = HistoryRepository(engine)
    runner = ScheduledRecalculator(repository)
    window = CalculationWindow(CALCULATED_AT, CALCULATED_AT + timedelta(minutes=5))

    result = runner.run_once(
        (
            StrategyCalculationTask(
                strategy_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
                strategy_version=DFK_CJEWEL_MAX_LOCK_V1.strategy_version,
                adapter=DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1),
                load_observations=lambda _: _dfk_observations_missing_required(),
            ),
            StrategyCalculationTask(
                strategy_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
                strategy_version=FARMERS_WORLD_AXE_WOOD_V1.strategy_version,
                adapter=FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1),
                load_observations=lambda _: _farmers_observations(),
            ),
        ),
        intended_window=window,
        calculated_at=CALCULATED_AT,
    )

    assert len(result.snapshots) == 1
    assert len(result.failures) == 1
    assert repository.latest_snapshot(FARMERS_WORLD_AXE_WOOD_V1.strategy_id) is not None
    assert repository.latest_snapshot(DFK_CJEWEL_MAX_LOCK_V1.strategy_id) is None
    assert result.failures[0].error_type == "AdapterInputError"
    assert REWARD_REALIZABLE_VALUE_USD in result.failures[0].error_message


def test_stale_required_inputs_are_recorded_as_failure_and_deduplicated(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "stale.db")
    repository = HistoryRepository(engine)
    runner = ScheduledRecalculator(repository)
    stale_calculated_at = CALCULATED_AT + timedelta(minutes=6)
    window = CalculationWindow(CALCULATED_AT, CALCULATED_AT + timedelta(minutes=5))
    task = StrategyCalculationTask(
        strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
        strategy_version=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_version,
        adapter=SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1),
        load_observations=lambda _: _splinterlands_observations(),
    )

    first = runner.run_once((task,), intended_window=window, calculated_at=stale_calculated_at)
    duplicate = runner.run_once((task,), intended_window=window, calculated_at=stale_calculated_at)
    failures = repository.list_failures(strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id)

    assert first.snapshots == ()
    assert len(first.failures) == 1
    assert duplicate.failures[0].failure_id == first.failures[0].failure_id
    assert len(failures) == 1
    assert "not fresh" in first.failures[0].error_message
    assert repository.latest_snapshot(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id) is None


def _migrated_engine(monkeypatch, tmp_path, name: str):
    database_url = f"sqlite+pysqlite:///{(tmp_path / name).as_posix()}"
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", database_url)
    settings = get_settings()
    command.upgrade(build_alembic_config(settings), "head")
    return create_engine(database_url)


def _dfk_calculation(calculated_at: datetime):
    observations = _dfk_observations()
    adapter_result = DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1).build_engine_input(
        observations,
        calculated_at=calculated_at,
    )
    return adapter_result, calculate_strategy_roi(adapter_result.economics_input), observations


def _splinterlands_calculation(calculated_at: datetime):
    observations = _splinterlands_observations()
    adapter_result = SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1).build_engine_input(
        observations,
        calculated_at=calculated_at,
    )
    return adapter_result, calculate_strategy_roi(adapter_result.economics_input), observations


def _versioned_result(
    adapter_result: AdapterResultV1,
    strategy_version: str,
    model_version: str,
):
    economics_input = replace(
        adapter_result.economics_input,
        strategy_version=strategy_version,
        model_version=model_version,
    )
    versioned_adapter_result = AdapterResultV1(
        economics_input=economics_input,
        classifications=adapter_result.classifications,
        derived_values=adapter_result.derived_values,
        warnings=adapter_result.warnings,
        uncertainty_ranges=adapter_result.uncertainty_ranges,
    )
    return versioned_adapter_result, calculate_strategy_roi(versioned_adapter_result.economics_input)


def _dfk_observations() -> tuple[Observation, ...]:
    fixture = json.loads(DFK_FIXTURE_PATH.read_text(encoding="utf-8"))
    return dfk_observations(fixture["strategy"])


def _dfk_observations_missing_required() -> tuple[Observation, ...]:
    return tuple(observation for observation in _dfk_observations() if observation.metric != REWARD_REALIZABLE_VALUE_USD)


def _farmers_observations() -> tuple[Observation, ...]:
    fixture = json.loads(FARMERS_FIXTURE_PATH.read_text(encoding="utf-8"))
    return farmers_observations(fixture["strategy"])


def _splinterlands_observations() -> tuple[Observation, ...]:
    fixture = json.loads(SPLINTERLANDS_FIXTURE_PATH.read_text(encoding="utf-8"))
    return splinterlands_observations(fixture["strategy"])
