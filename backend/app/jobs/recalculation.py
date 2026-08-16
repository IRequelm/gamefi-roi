"""In-process scheduled recalculation runner for historical snapshots."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.adapters.contract import ADAPTER_CONTRACT_VERSION, StrategyAdapterV1
from app.engine.calculator import MODEL_VERSION, calculate_strategy_roi
from app.sources.observations import Observation
from app.storage.history import CalculationWindow, HistoryRepository, StrategyCalculationFailure, StrategySnapshot


ObservationLoader = Callable[[datetime], tuple[Observation, ...]]


@dataclass(frozen=True)
class StrategyCalculationTask:
    strategy_id: str
    strategy_version: str
    adapter: StrategyAdapterV1
    load_observations: ObservationLoader
    adapter_contract_version: str = ADAPTER_CONTRACT_VERSION
    model_version: str = MODEL_VERSION


@dataclass(frozen=True)
class RecalculationRunResult:
    calculated_at: datetime
    intended_window: CalculationWindow
    snapshots: tuple[StrategySnapshot, ...]
    failures: tuple[StrategyCalculationFailure, ...]


class ScheduledRecalculator:
    def __init__(self, repository: HistoryRepository) -> None:
        self.repository = repository

    def run_once(
        self,
        tasks: tuple[StrategyCalculationTask, ...],
        *,
        intended_window: CalculationWindow,
        calculated_at: datetime | None = None,
    ) -> RecalculationRunResult:
        active_time = _normalize_utc(datetime.now(UTC) if calculated_at is None else calculated_at)
        snapshots: list[StrategySnapshot] = []
        failures: list[StrategyCalculationFailure] = []

        for task in tasks:
            observations: tuple[Observation, ...] = ()
            try:
                observations = task.load_observations(active_time)
                adapter_result = task.adapter.build_engine_input(observations, calculated_at=active_time)
                roi_result = calculate_strategy_roi(adapter_result.economics_input)
                snapshots.append(
                    self.repository.save_snapshot(
                        adapter_result=adapter_result,
                        roi_result=roi_result,
                        observations=observations,
                        calculated_at=active_time,
                        intended_window=intended_window,
                    )
                )
            except Exception as exc:
                failures.append(
                    self.repository.record_failure(
                        strategy_id=task.strategy_id,
                        strategy_version=task.strategy_version,
                        adapter_contract_version=task.adapter_contract_version,
                        model_version=task.model_version,
                        intended_window=intended_window,
                        failed_at=active_time,
                        error=exc,
                        observations=observations,
                    )
                )

        return RecalculationRunResult(
            calculated_at=active_time,
            intended_window=intended_window,
            snapshots=tuple(snapshots),
            failures=tuple(failures),
        )


def hourly_window(containing: datetime | None = None) -> CalculationWindow:
    active_time = _normalize_utc(datetime.now(UTC) if containing is None else containing)
    start = active_time.replace(minute=0, second=0, microsecond=0)
    return CalculationWindow(start=start, end=start + timedelta(hours=1))


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Recalculation timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)
