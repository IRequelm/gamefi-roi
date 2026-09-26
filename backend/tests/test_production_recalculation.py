from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from app.adapters.contract import live_observation
from app.adapters.defi_kingdoms_jeweler import DfkJewelerAdapter
from app.jobs import production_recalculation
from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.production_recalculation import (
    HardStaleInputError,
    SchedulerLockLease,
    cadence_window,
    enforce_hard_stale_inputs,
    run_recalculation_tasks,
)
from app.jobs.recalculation import StrategyCalculationTask
from app.sources.observations import SourceType
from app.storage.history import HistoryRepository
from app.storage.scoring import ScoringRepository
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from test_history_storage import _migrated_engine

NOW = datetime(2026, 8, 16, 12, 44, tzinfo=UTC)


def test_cadence_window_is_deterministic() -> None:
    window = cadence_window(NOW, cadence_minutes=30)

    assert window.start == datetime(2026, 8, 16, 12, 30, tzinfo=UTC)
    assert window.end == datetime(2026, 8, 16, 13, 0, tzinfo=UTC)


def test_production_recalculation_persists_snapshots_scores_and_failures(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "production-run.db")
    success_task = build_history_probe_tasks()[0]
    failing_task = StrategyCalculationTask(
        strategy_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        strategy_version=FARMERS_WORLD_AXE_WOOD_V1.strategy_version,
        adapter=DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1),
        load_observations=_provider_failure,
    )

    summary = run_recalculation_tasks(
        engine=engine,
        tasks=(success_task, failing_task),
        calculated_at=NOW,
        cadence_minutes=30,
    )

    assert summary.status == "failed"
    assert len(summary.snapshot_ids) == 1
    assert len(summary.failure_ids) == 1
    assert summary.score_count == 1
    assert HistoryRepository(engine).latest_snapshot(DFK_CJEWEL_MAX_LOCK_V1.strategy_id) is not None
    assert ScoringRepository(engine).get_score(summary.snapshot_ids[0]) is not None


def test_production_recalculation_is_idempotent_per_window(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "production-idempotent.db")
    task = build_history_probe_tasks()[0]

    first = run_recalculation_tasks(engine=engine, tasks=(task,), calculated_at=NOW, cadence_minutes=30)
    duplicate = run_recalculation_tasks(engine=engine, tasks=(task,), calculated_at=NOW, cadence_minutes=30)

    assert duplicate.snapshot_ids == first.snapshot_ids
    assert first.new_snapshot_count == 1
    assert first.reused_snapshot_count == 0
    assert duplicate.new_snapshot_count == 0
    assert duplicate.reused_snapshot_count == 1
    assert len(HistoryRepository(engine).ordered_time_series(DFK_CJEWEL_MAX_LOCK_V1.strategy_id, start=first.intended_window.start, end=first.intended_window.end)) == 1


def test_production_recalculation_reuses_lock_connection_with_constrained_pool(monkeypatch, tmp_path) -> None:
    setup_engine = _migrated_engine(monkeypatch, tmp_path, "production-constrained-pool.db")
    database_url = str(setup_engine.url)
    setup_engine.dispose()
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.1,
    )
    task = build_history_probe_tasks()[0]

    @contextmanager
    def same_pool_lock(active_engine):
        connection = active_engine.connect()
        try:
            yield SchedulerLockLease(acquired=True, bind=connection)
        finally:
            connection.close()

    monkeypatch.setattr(production_recalculation, "scheduler_lock", same_pool_lock)

    summary = run_recalculation_tasks(
        engine=engine,
        tasks=(task,),
        calculated_at=NOW,
        cadence_minutes=30,
    )

    assert len(summary.snapshot_ids) == 1
    assert summary.score_count == 1
    assert HistoryRepository(engine).latest_snapshot(DFK_CJEWEL_MAX_LOCK_V1.strategy_id) is not None
    assert ScoringRepository(engine).get_score(summary.snapshot_ids[0]) is not None


def test_hard_stale_live_inputs_fail_explicitly() -> None:
    stale_observation = live_observation(
        provider="provider",
        entity_type="asset",
        entity_id="asset",
        metric="token.price",
        value="1.00",
        unit="USD",
        source_locator="provider:asset",
        source_type=SourceType.MARKET_API,
        retrieved_at=NOW - timedelta(hours=2),
        observed_at=NOW - timedelta(hours=2),
        freshness=timedelta(days=1),
    )

    with pytest.raises(HardStaleInputError, match="token.price"):
        enforce_hard_stale_inputs((stale_observation,), active_time=NOW, hard_stale=timedelta(minutes=30))


def _provider_failure(_active_time: datetime):
    raise RuntimeError("provider unavailable")
