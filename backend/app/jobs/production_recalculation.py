"""Production scheduled recalculation entry point."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection

from app.adapters.defi_kingdoms_jeweler import DfkJewelerAdapter
from app.adapters.defi_kingdoms_jeweler_probe import load_live_observations as load_dfk_observations
from app.adapters.farmers_world import FarmersWorldAxeAdapter
from app.adapters.farmers_world_probe import load_live_observations as load_farmers_world_observations
from app.adapters.splinterlands import SplinterlandsModernRankedAdapter
from app.adapters.splinterlands_probe import load_live_observations as load_splinterlands_observations
from app.config.settings import Settings, get_settings
from app.jobs.recalculation import RecalculationRunResult, ScheduledRecalculator, StrategyCalculationTask
from app.risk.scoring import SnapshotScorer
from app.sources.observations import Observation
from app.storage.database import create_database_engine
from app.storage.history import CalculationWindow, HistoryRepository, StrategySnapshot
from app.storage.scoring import ScoringRepository
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1

logger = logging.getLogger(__name__)
SCHEDULER_LOCK_KEY = 913_013_013


@dataclass(frozen=True)
class ProductionRecalculationSummary:
    status: str
    calculated_at: datetime
    intended_window: CalculationWindow
    snapshot_ids: tuple[str, ...]
    failure_ids: tuple[str, ...]
    score_count: int


@dataclass(frozen=True)
class SchedulerLockLease:
    acquired: bool
    bind: Engine | Connection


class HardStaleInputError(RuntimeError):
    """Raised when live production observations exceed the hard-stale threshold."""


def build_production_tasks(settings: Settings | None = None) -> tuple[StrategyCalculationTask, ...]:
    active_settings = settings or get_settings()
    hard_stale = timedelta(seconds=active_settings.production_hard_stale_seconds)
    return (
        StrategyCalculationTask(
            strategy_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
            strategy_version=DFK_CJEWEL_MAX_LOCK_V1.strategy_version,
            adapter=DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1),
            load_observations=with_hard_stale_check(load_dfk_observations, hard_stale=hard_stale),
        ),
        StrategyCalculationTask(
            strategy_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
            strategy_version=FARMERS_WORLD_AXE_WOOD_V1.strategy_version,
            adapter=FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1),
            load_observations=with_hard_stale_check(load_farmers_world_observations, hard_stale=hard_stale),
        ),
        StrategyCalculationTask(
            strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
            strategy_version=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_version,
            adapter=SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1),
            load_observations=with_hard_stale_check(load_splinterlands_observations, hard_stale=hard_stale),
        ),
    )


def run_production_recalculation(
    *,
    settings: Settings | None = None,
    calculated_at: datetime | None = None,
) -> ProductionRecalculationSummary:
    active_settings = settings or get_settings()
    engine = create_database_engine(active_settings)
    try:
        return run_recalculation_tasks(
            engine=engine,
            tasks=build_production_tasks(active_settings),
            calculated_at=calculated_at,
            cadence_minutes=active_settings.scheduler_cadence_minutes,
        )
    finally:
        engine.dispose()


def run_recalculation_tasks(
    *,
    engine: Engine,
    tasks: tuple[StrategyCalculationTask, ...],
    calculated_at: datetime | None = None,
    cadence_minutes: int = 30,
) -> ProductionRecalculationSummary:
    active_time = _normalize_utc(datetime.now(UTC) if calculated_at is None else calculated_at)
    intended_window = cadence_window(active_time, cadence_minutes=cadence_minutes)
    with scheduler_lock(engine) as lock:
        if not lock.acquired:
            logger.info("scheduler_lock_busy window_start=%s", intended_window.start.isoformat())
            return ProductionRecalculationSummary(
                status="skipped_lock_busy",
                calculated_at=active_time,
                intended_window=intended_window,
                snapshot_ids=(),
                failure_ids=(),
                score_count=0,
            )

        repository = HistoryRepository(lock.bind)
        run = ScheduledRecalculator(repository).run_once(
            tasks,
            intended_window=intended_window,
            calculated_at=active_time,
        )
        score_count = _persist_scores(bind=lock.bind, snapshots=run.snapshots, scored_at=run.calculated_at)
        _log_run_result(run, score_count=score_count)
        return ProductionRecalculationSummary(
            status="ok" if run.snapshots else "failed",
            calculated_at=run.calculated_at,
            intended_window=run.intended_window,
            snapshot_ids=tuple(snapshot.snapshot_id for snapshot in run.snapshots),
            failure_ids=tuple(failure.failure_id for failure in run.failures),
            score_count=score_count,
        )


def cadence_window(containing: datetime, *, cadence_minutes: int) -> CalculationWindow:
    if cadence_minutes <= 0:
        raise ValueError("cadence_minutes must be positive")
    active_time = _normalize_utc(containing)
    cadence_seconds = cadence_minutes * 60
    start_timestamp = int(active_time.timestamp()) - (int(active_time.timestamp()) % cadence_seconds)
    start = datetime.fromtimestamp(start_timestamp, UTC)
    return CalculationWindow(start=start, end=start + timedelta(minutes=cadence_minutes))


def with_hard_stale_check(loader, *, hard_stale: timedelta):
    def load(active_time: datetime) -> tuple[Observation, ...]:
        observations = loader(active_time)
        enforce_hard_stale_inputs(observations, active_time=active_time, hard_stale=hard_stale)
        return observations

    return load


def enforce_hard_stale_inputs(
    observations: tuple[Observation, ...],
    *,
    active_time: datetime,
    hard_stale: timedelta,
) -> None:
    stale_metrics: list[str] = []
    active_time = _normalize_utc(active_time)
    for observation in observations:
        if observation.metadata.get("classification") != "LIVE":
            continue
        evidence_time = observation.observed_at or observation.retrieved_at
        if active_time - evidence_time > hard_stale:
            stale_metrics.append(observation.metric)
    if stale_metrics:
        raise HardStaleInputError(
            "Required live observations exceed production hard-stale threshold: " + ", ".join(sorted(stale_metrics))
        )


@contextmanager
def scheduler_lock(engine: Engine) -> Iterator[SchedulerLockLease]:
    if engine.dialect.name != "postgresql":
        yield SchedulerLockLease(acquired=True, bind=engine)
        return

    connection = engine.connect()
    acquired = False
    try:
        acquired = bool(connection.execute(text("select pg_try_advisory_lock(:key)"), {"key": SCHEDULER_LOCK_KEY}).scalar())
        _commit_if_active(connection)
        yield SchedulerLockLease(acquired=acquired, bind=connection)
    finally:
        if acquired:
            _rollback_if_active(connection)
            connection.execute(text("select pg_advisory_unlock(:key)"), {"key": SCHEDULER_LOCK_KEY})
            _commit_if_active(connection)
        connection.close()


def _persist_scores(*, bind: Engine | Connection, snapshots: tuple[StrategySnapshot, ...], scored_at: datetime) -> int:
    if not snapshots:
        return 0
    history_repository = HistoryRepository(bind)
    scoring_repository = ScoringRepository(bind)
    scorer = SnapshotScorer()
    saved = 0
    for snapshot in snapshots:
        history = history_repository.ordered_time_series(
            snapshot.strategy_id,
            start=scored_at - timedelta(days=30),
            end=scored_at,
            strategy_version=snapshot.strategy_version,
            model_version=snapshot.model_version,
        )
        scoring_repository.save_score(scorer.score(snapshot, history=history, scored_at=scored_at))
        saved += 1
    return saved


def _commit_if_active(connection: Connection) -> None:
    if connection.in_transaction():
        connection.commit()


def _rollback_if_active(connection: Connection) -> None:
    if connection.in_transaction():
        connection.rollback()


def _log_run_result(run: RecalculationRunResult, *, score_count: int) -> None:
    logger.info(
        "production_recalculation_complete calculated_at=%s snapshots=%s failures=%s scores=%s",
        run.calculated_at.isoformat(),
        len(run.snapshots),
        len(run.failures),
        score_count,
    )
    for failure in run.failures:
        logger.error(
            "strategy_calculation_failure strategy_id=%s strategy_version=%s error_type=%s error_message=%s",
            failure.strategy_id,
            failure.strategy_version,
            failure.error_type,
            failure.error_message,
        )


def _summary_payload(summary: ProductionRecalculationSummary) -> dict[str, Any]:
    return {
        "status": summary.status,
        "calculated_at": summary.calculated_at.isoformat(),
        "intended_window": {
            "start": summary.intended_window.start.isoformat(),
            "end": summary.intended_window.end.isoformat(),
        },
        "snapshot_ids": list(summary.snapshot_ids),
        "failure_ids": list(summary.failure_ids),
        "score_count": summary.score_count,
    }


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Production recalculation timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)


def main() -> int:
    summary = run_production_recalculation()
    print(json.dumps(_summary_payload(summary), indent=2, sort_keys=True))
    return 0 if summary.snapshot_ids or summary.status == "skipped_lock_busy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
