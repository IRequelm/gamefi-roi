"""Historical snapshot repository for strategy ROI calculations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Engine, desc, select
from sqlalchemy.orm import Session

from app.adapters.contract import ADAPTER_CONTRACT_VERSION, AdapterResultV1
from app.engine.calculator import MODEL_VERSION
from app.engine.money import Money
from app.engine.results import BreakEvenMetric, RatioMetric, RoiResult
from app.sources.observations import Observation
from app.storage.models import StrategyCalculationFailureRecord, StrategySnapshotRecord


class HistoryPersistenceError(ValueError):
    """Raised when a calculation result cannot be safely snapshotted."""


@dataclass(frozen=True)
class CalculationWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start = _normalize_utc(self.start)
        end = _normalize_utc(self.end)
        if end <= start:
            raise HistoryPersistenceError("CalculationWindow.end must be after start")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)


@dataclass(frozen=True)
class StrategySnapshot:
    snapshot_id: str
    idempotency_key: str
    strategy_id: str
    strategy_version: str
    adapter_contract_version: str
    model_version: str
    calculated_at: datetime
    intended_window: CalculationWindow
    reporting_currency: str
    capital_metrics: Mapping[str, Any]
    earnings_cost_metrics: Mapping[str, Any]
    roi_outputs: Mapping[str, Any]
    adapter_derived_values: Mapping[str, Any]
    uncertainty_ranges: Mapping[str, Any]
    warnings: tuple[Mapping[str, Any], ...]
    classification_summary: Mapping[str, Any]
    input_observation_ids: tuple[str, ...]
    input_observation_references: Mapping[str, Any]
    freshness_summary: Mapping[str, Any]
    assumptions: Mapping[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class StrategyCalculationFailure:
    failure_id: str
    idempotency_key: str
    strategy_id: str
    strategy_version: str
    adapter_contract_version: str
    model_version: str
    intended_window: CalculationWindow
    failed_at: datetime
    error_type: str
    error_message: str
    input_observation_ids: tuple[str, ...]
    input_observation_references: Mapping[str, Any]
    freshness_summary: Mapping[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class StrategyVersionInfo:
    strategy_id: str
    strategy_version: str
    adapter_contract_version: str
    model_version: str
    first_calculated_at: datetime
    last_calculated_at: datetime
    snapshot_count: int


class HistoryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save_snapshot(
        self,
        *,
        adapter_result: AdapterResultV1,
        roi_result: RoiResult,
        observations: tuple[Observation, ...],
        calculated_at: datetime,
        intended_window: CalculationWindow,
    ) -> StrategySnapshot:
        calculated_at = _normalize_utc(calculated_at)
        _validate_snapshot_inputs(adapter_result, roi_result)
        observation_references, freshness_summary = _input_observation_references(
            required_observation_ids=roi_result.input_observation_ids,
            observations=observations,
            calculated_at=calculated_at,
        )
        idempotency_key = snapshot_idempotency_key(
            strategy_id=roi_result.strategy_id,
            strategy_version=roi_result.strategy_version,
            adapter_contract_version=adapter_result.contract_version,
            model_version=roi_result.model_version,
            intended_window=intended_window,
        )
        now = datetime.now(UTC)

        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(StrategySnapshotRecord).where(StrategySnapshotRecord.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return _snapshot_from_record(existing)

            record = StrategySnapshotRecord(
                snapshot_id=_stable_uuid("snapshot", idempotency_key),
                idempotency_key=idempotency_key,
                strategy_id=roi_result.strategy_id,
                strategy_version=roi_result.strategy_version,
                adapter_contract_version=adapter_result.contract_version,
                model_version=roi_result.model_version,
                calculated_at=calculated_at,
                intended_window_start=intended_window.start,
                intended_window_end=intended_window.end,
                reporting_currency=roi_result.reporting_currency,
                capital_metrics_json=_capital_metrics(roi_result),
                earnings_cost_metrics_json=_earnings_cost_metrics(roi_result),
                roi_outputs_json=_roi_outputs(roi_result),
                adapter_derived_values_json={
                    metric: str(value) for metric, value in sorted(adapter_result.derived_values.items())
                },
                uncertainty_ranges_json=_uncertainty_ranges(adapter_result),
                warnings_json=_warnings(adapter_result),
                classification_summary_json=_classification_summary(adapter_result),
                input_observation_ids_json=list(roi_result.input_observation_ids),
                input_observation_references_json=observation_references,
                freshness_summary_json=freshness_summary,
                assumptions_json=_json_safe_mapping(adapter_result.economics_input.assumptions),
                created_at=now,
            )
            session.add(record)
            session.commit()
            return _snapshot_from_record(record)

    def record_failure(
        self,
        *,
        strategy_id: str,
        strategy_version: str,
        intended_window: CalculationWindow,
        failed_at: datetime,
        error: Exception,
        observations: tuple[Observation, ...] = (),
        adapter_contract_version: str = ADAPTER_CONTRACT_VERSION,
        model_version: str = MODEL_VERSION,
    ) -> StrategyCalculationFailure:
        failed_at = _normalize_utc(failed_at)
        idempotency_key = snapshot_idempotency_key(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            adapter_contract_version=adapter_contract_version,
            model_version=model_version,
            intended_window=intended_window,
        )
        observation_ids = tuple(observation.observation_id for observation in observations)
        observation_references, freshness_summary = _input_observation_references(
            required_observation_ids=observation_ids,
            observations=observations,
            calculated_at=failed_at,
        )
        now = datetime.now(UTC)

        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(StrategyCalculationFailureRecord).where(
                    StrategyCalculationFailureRecord.idempotency_key == idempotency_key
                )
            )
            if existing is not None:
                return _failure_from_record(existing)

            record = StrategyCalculationFailureRecord(
                failure_id=_stable_uuid("failure", idempotency_key),
                idempotency_key=idempotency_key,
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                adapter_contract_version=adapter_contract_version,
                model_version=model_version,
                intended_window_start=intended_window.start,
                intended_window_end=intended_window.end,
                failed_at=failed_at,
                error_type=type(error).__name__,
                error_message=str(error),
                input_observation_ids_json=list(observation_ids),
                input_observation_references_json=observation_references,
                freshness_summary_json=freshness_summary,
                created_at=now,
            )
            session.add(record)
            session.commit()
            return _failure_from_record(record)

    def latest_snapshot(self, strategy_id: str, *, strategy_version: str | None = None) -> StrategySnapshot | None:
        stmt = select(StrategySnapshotRecord).where(StrategySnapshotRecord.strategy_id == strategy_id)
        if strategy_version is not None:
            stmt = stmt.where(StrategySnapshotRecord.strategy_version == strategy_version)
        stmt = stmt.order_by(desc(StrategySnapshotRecord.calculated_at), desc(StrategySnapshotRecord.created_at))

        with Session(self.engine) as session:
            record = session.scalars(stmt).first()
            return None if record is None else _snapshot_from_record(record)

    def latest_snapshots(self) -> list[StrategySnapshot]:
        stmt = select(StrategySnapshotRecord).order_by(
            StrategySnapshotRecord.strategy_id,
            desc(StrategySnapshotRecord.calculated_at),
            desc(StrategySnapshotRecord.created_at),
        )
        latest_by_strategy: dict[str, StrategySnapshot] = {}
        with Session(self.engine) as session:
            for record in session.scalars(stmt).all():
                if record.strategy_id not in latest_by_strategy:
                    latest_by_strategy[record.strategy_id] = _snapshot_from_record(record)
        return [latest_by_strategy[strategy_id] for strategy_id in sorted(latest_by_strategy)]

    def snapshots_in_range(
        self,
        strategy_id: str,
        *,
        start: datetime,
        end: datetime,
        strategy_version: str | None = None,
        model_version: str | None = None,
    ) -> list[StrategySnapshot]:
        start = _normalize_utc(start)
        end = _normalize_utc(end)
        stmt = select(StrategySnapshotRecord).where(
            StrategySnapshotRecord.strategy_id == strategy_id,
            StrategySnapshotRecord.calculated_at >= start,
            StrategySnapshotRecord.calculated_at <= end,
        )
        if strategy_version is not None:
            stmt = stmt.where(StrategySnapshotRecord.strategy_version == strategy_version)
        if model_version is not None:
            stmt = stmt.where(StrategySnapshotRecord.model_version == model_version)
        stmt = stmt.order_by(StrategySnapshotRecord.calculated_at, StrategySnapshotRecord.created_at)

        with Session(self.engine) as session:
            return [_snapshot_from_record(record) for record in session.scalars(stmt).all()]

    def ordered_time_series(
        self,
        strategy_id: str,
        *,
        start: datetime,
        end: datetime,
        strategy_version: str | None = None,
        model_version: str | None = None,
    ) -> list[StrategySnapshot]:
        return self.snapshots_in_range(
            strategy_id,
            start=start,
            end=end,
            strategy_version=strategy_version,
            model_version=model_version,
        )

    def strategy_version_info(self, strategy_id: str) -> list[StrategyVersionInfo]:
        stmt = (
            select(StrategySnapshotRecord)
            .where(StrategySnapshotRecord.strategy_id == strategy_id)
            .order_by(StrategySnapshotRecord.calculated_at)
        )
        with Session(self.engine) as session:
            snapshots = [_snapshot_from_record(record) for record in session.scalars(stmt).all()]

        grouped: dict[tuple[str, str, str], list[StrategySnapshot]] = {}
        for snapshot in snapshots:
            key = (snapshot.strategy_version, snapshot.adapter_contract_version, snapshot.model_version)
            grouped.setdefault(key, []).append(snapshot)

        return [
            StrategyVersionInfo(
                strategy_id=strategy_id,
                strategy_version=key[0],
                adapter_contract_version=key[1],
                model_version=key[2],
                first_calculated_at=items[0].calculated_at,
                last_calculated_at=items[-1].calculated_at,
                snapshot_count=len(items),
            )
            for key, items in sorted(grouped.items(), key=lambda entry: entry[0])
        ]

    def list_failures(self, *, strategy_id: str | None = None) -> list[StrategyCalculationFailure]:
        stmt = select(StrategyCalculationFailureRecord)
        if strategy_id is not None:
            stmt = stmt.where(StrategyCalculationFailureRecord.strategy_id == strategy_id)
        stmt = stmt.order_by(StrategyCalculationFailureRecord.failed_at, StrategyCalculationFailureRecord.created_at)

        with Session(self.engine) as session:
            return [_failure_from_record(record) for record in session.scalars(stmt).all()]


def snapshot_idempotency_key(
    *,
    strategy_id: str,
    strategy_version: str,
    adapter_contract_version: str,
    model_version: str,
    intended_window: CalculationWindow,
) -> str:
    for field_name, value in (
        ("strategy_id", strategy_id),
        ("strategy_version", strategy_version),
        ("adapter_contract_version", adapter_contract_version),
        ("model_version", model_version),
    ):
        if not value:
            raise HistoryPersistenceError(f"{field_name} is required for history idempotency")
    raw = "|".join(
        (
            strategy_id,
            strategy_version,
            adapter_contract_version,
            model_version,
            intended_window.start.isoformat(),
            intended_window.end.isoformat(),
        )
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _validate_snapshot_inputs(adapter_result: AdapterResultV1, roi_result: RoiResult) -> None:
    economics_input = adapter_result.economics_input
    if economics_input.strategy_id != roi_result.strategy_id:
        raise HistoryPersistenceError("Adapter and ROI strategy ids do not match")
    if economics_input.strategy_version != roi_result.strategy_version:
        raise HistoryPersistenceError("Adapter and ROI strategy versions do not match")
    if economics_input.model_version != roi_result.model_version:
        raise HistoryPersistenceError("Adapter and ROI model versions do not match")
    if economics_input.reporting_currency != roi_result.reporting_currency:
        raise HistoryPersistenceError("Adapter and ROI reporting currencies do not match")
    if economics_input.input_observation_ids != roi_result.input_observation_ids:
        raise HistoryPersistenceError("Adapter and ROI input observation ids do not match")


def _input_observation_references(
    *,
    required_observation_ids: tuple[str, ...],
    observations: tuple[Observation, ...],
    calculated_at: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_id = {observation.observation_id: observation for observation in observations}
    missing = [observation_id for observation_id in required_observation_ids if observation_id not in by_id]
    if missing:
        raise HistoryPersistenceError(f"Missing observation references for snapshot: {', '.join(missing)}")

    references: dict[str, Any] = {}
    status_counts = {"fresh": 0, "stale": 0, "invalid": 0, "missing": 0}
    retrieved_times: list[datetime] = []
    fresh_until_times: list[datetime] = []
    for observation_id in required_observation_ids:
        observation = by_id[observation_id]
        status_at_calculation = observation.status_at(calculated_at).value
        status_counts[status_at_calculation] = status_counts.get(status_at_calculation, 0) + 1
        retrieved_times.append(observation.retrieved_at)
        fresh_until_times.append(observation.fresh_until)
        references[observation_id] = {
            "observation_id": observation.observation_id,
            "entity_type": observation.entity_type,
            "entity_id": observation.entity_id,
            "metric": observation.metric,
            "value": str(observation.value) if observation.value is not None else None,
            "unit": observation.unit,
            "quote_currency": observation.quote_currency,
            "source_provider": observation.source_provider,
            "source_type": observation.source_type.value,
            "source_locator": observation.source_locator,
            "observed_at": _iso_or_none(observation.observed_at),
            "retrieved_at": observation.retrieved_at.isoformat(),
            "fresh_until": observation.fresh_until.isoformat(),
            "stored_status": observation.status.value,
            "status_at_calculation": status_at_calculation,
            "metadata": _json_safe(observation.metadata),
        }

    freshness_summary = {
        "calculated_at": calculated_at.isoformat(),
        "input_count": len(required_observation_ids),
        "status_counts": status_counts,
        "oldest_retrieved_at": min(retrieved_times).isoformat() if retrieved_times else None,
        "newest_retrieved_at": max(retrieved_times).isoformat() if retrieved_times else None,
        "earliest_fresh_until": min(fresh_until_times).isoformat() if fresh_until_times else None,
    }
    return references, freshness_summary


def _capital_metrics(roi_result: RoiResult) -> dict[str, Any]:
    return {
        "total_capital": _money(roi_result.total_capital),
        "sunk_cost": _money(roi_result.sunk_cost),
        "recoverable_capital": _money(roi_result.recoverable_capital),
        "capital_at_risk": _money(roi_result.capital_at_risk),
    }


def _earnings_cost_metrics(roi_result: RoiResult) -> dict[str, Any]:
    return {
        "gross_nominal_earnings_day": _money(roi_result.gross_nominal_earnings_day),
        "realizable_earnings_day": _money(roi_result.realizable_earnings_day),
        "operating_cost_day": _money(roi_result.operating_cost_day),
        "transaction_cost_day": _money(roi_result.transaction_cost_day),
        "other_cost_day": _money(roi_result.other_cost_day),
        "net_earnings_day": _money(roi_result.net_earnings_day),
    }


def _roi_outputs(roi_result: RoiResult) -> dict[str, Any]:
    return {
        "break_even": _break_even(roi_result.break_even),
        "roi_total_7d": _ratio(roi_result.roi_total_7d),
        "roi_total_30d": _ratio(roi_result.roi_total_30d),
        "roi_total_90d": _ratio(roi_result.roi_total_90d),
        "roi_risk_7d": _ratio(roi_result.roi_risk_7d),
        "roi_risk_30d": _ratio(roi_result.roi_risk_30d),
        "roi_risk_90d": _ratio(roi_result.roi_risk_90d),
        "exit_adjusted_pnl": _money(roi_result.exit_adjusted_pnl),
    }


def _money(value: Money) -> dict[str, str]:
    return {"amount": str(value.amount), "currency": value.currency}


def _ratio(value: RatioMetric) -> dict[str, Any]:
    return {
        "value": str(value.value) if value.value is not None else None,
        "status": value.status.value,
        "reason": value.reason,
    }


def _break_even(value: BreakEvenMetric) -> dict[str, Any]:
    return {
        "basis": value.basis.value,
        "recovery_target": _money(value.recovery_target),
        "days": str(value.days) if value.days is not None else None,
        "status": value.status.value,
        "reason": value.reason,
    }


def _classification_summary(adapter_result: AdapterResultV1) -> dict[str, Any]:
    metrics = {metric: classification.value for metric, classification in sorted(adapter_result.classifications.items())}
    counts = {"LIVE": 0, "CONFIG": 0, "DERIVED": 0}
    for classification in metrics.values():
        counts[classification] = counts.get(classification, 0) + 1
    return {"counts": counts, "metrics": metrics}


def _uncertainty_ranges(adapter_result: AdapterResultV1) -> dict[str, Any]:
    return {
        metric: {
            "metric": metric_range.metric,
            "low_metric": metric_range.low_metric,
            "base_metric": metric_range.base_metric,
            "high_metric": metric_range.high_metric,
            "unit": metric_range.unit,
            "description": metric_range.description,
        }
        for metric, metric_range in sorted(adapter_result.uncertainty_ranges.items())
    }


def _warnings(adapter_result: AdapterResultV1) -> list[dict[str, str]]:
    return [
        {"code": warning.code, "message": warning.message, "severity": warning.severity}
        for warning in adapter_result.warnings
    ]


def _snapshot_from_record(record: StrategySnapshotRecord) -> StrategySnapshot:
    return StrategySnapshot(
        snapshot_id=record.snapshot_id,
        idempotency_key=record.idempotency_key,
        strategy_id=record.strategy_id,
        strategy_version=record.strategy_version,
        adapter_contract_version=record.adapter_contract_version,
        model_version=record.model_version,
        calculated_at=_as_utc(record.calculated_at),
        intended_window=CalculationWindow(
            start=_as_utc(record.intended_window_start),
            end=_as_utc(record.intended_window_end),
        ),
        reporting_currency=record.reporting_currency,
        capital_metrics=MappingProxyType(dict(record.capital_metrics_json)),
        earnings_cost_metrics=MappingProxyType(dict(record.earnings_cost_metrics_json)),
        roi_outputs=MappingProxyType(dict(record.roi_outputs_json)),
        adapter_derived_values=MappingProxyType(dict(record.adapter_derived_values_json)),
        uncertainty_ranges=MappingProxyType(dict(record.uncertainty_ranges_json)),
        warnings=tuple(MappingProxyType(dict(warning)) for warning in record.warnings_json),
        classification_summary=MappingProxyType(dict(record.classification_summary_json)),
        input_observation_ids=tuple(record.input_observation_ids_json),
        input_observation_references=MappingProxyType(dict(record.input_observation_references_json)),
        freshness_summary=MappingProxyType(dict(record.freshness_summary_json)),
        assumptions=MappingProxyType(dict(record.assumptions_json)),
        created_at=_as_utc(record.created_at),
    )


def _failure_from_record(record: StrategyCalculationFailureRecord) -> StrategyCalculationFailure:
    return StrategyCalculationFailure(
        failure_id=record.failure_id,
        idempotency_key=record.idempotency_key,
        strategy_id=record.strategy_id,
        strategy_version=record.strategy_version,
        adapter_contract_version=record.adapter_contract_version,
        model_version=record.model_version,
        intended_window=CalculationWindow(
            start=_as_utc(record.intended_window_start),
            end=_as_utc(record.intended_window_end),
        ),
        failed_at=_as_utc(record.failed_at),
        error_type=record.error_type,
        error_message=record.error_message,
        input_observation_ids=tuple(record.input_observation_ids_json),
        input_observation_references=MappingProxyType(dict(record.input_observation_references_json)),
        freshness_summary=MappingProxyType(dict(record.freshness_summary_json)),
        created_at=_as_utc(record.created_at),
    )


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return dict(_json_safe(value))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, bool | int | str):
        return value
    return str(value)


def _stable_uuid(prefix: str, idempotency_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gamefi-roi-history|{prefix}|{idempotency_key}"))


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HistoryPersistenceError("History timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_or_none(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()
