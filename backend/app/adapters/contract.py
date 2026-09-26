"""Adapter Contract v1 shared types and helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable
from uuid import NAMESPACE_URL, uuid5

from app.engine.decimal_context import decimal_from_int, decimal_from_text
from app.engine.inputs import StrategyEconomicsInput
from app.sources.observations import Observation, ObservationStatus, SourceType

ADAPTER_CONTRACT_VERSION = "adapter-contract-v1"


class ValueClassification(StrEnum):
    LIVE = "LIVE"
    DERIVED = "DERIVED"
    CONFIG = "CONFIG"


class AdapterInputError(ValueError):
    """Raised when an adapter cannot safely produce ROI engine inputs."""


@dataclass(frozen=True)
class AdapterWarning:
    code: str
    message: str
    severity: str = "warning"

    def __post_init__(self) -> None:
        if not self.code:
            raise AdapterInputError("AdapterWarning.code is required")
        if not self.message:
            raise AdapterInputError("AdapterWarning.message is required")
        if self.severity not in {"info", "warning", "critical"}:
            raise AdapterInputError("AdapterWarning.severity must be info, warning, or critical")


@dataclass(frozen=True)
class AdapterMetricRange:
    metric: str
    low_metric: str
    base_metric: str
    high_metric: str
    unit: str
    description: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("metric", self.metric),
            ("low_metric", self.low_metric),
            ("base_metric", self.base_metric),
            ("high_metric", self.high_metric),
            ("unit", self.unit),
            ("description", self.description),
        ):
            if not value:
                raise AdapterInputError(f"AdapterMetricRange.{field_name} is required")


@dataclass(frozen=True)
class AdapterResultV1:
    economics_input: StrategyEconomicsInput
    classifications: Mapping[str, ValueClassification]
    derived_values: Mapping[str, Decimal]
    warnings: tuple[AdapterWarning, ...] = ()
    uncertainty_ranges: Mapping[str, AdapterMetricRange] = field(default_factory=dict)
    contract_version: str = ADAPTER_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != ADAPTER_CONTRACT_VERSION:
            raise AdapterInputError(f"Unsupported adapter contract version: {self.contract_version}")
        if not isinstance(self.economics_input, StrategyEconomicsInput):
            raise AdapterInputError("AdapterResultV1.economics_input must be StrategyEconomicsInput")
        if not self.economics_input.strategy_id:
            raise AdapterInputError("AdapterResultV1 strategy_id is required")
        if not self.economics_input.strategy_version:
            raise AdapterInputError("AdapterResultV1 strategy_version is required")
        if not self.economics_input.input_observation_ids:
            raise AdapterInputError("AdapterResultV1 must preserve input observation ids")

        classifications = {
            metric: ValueClassification(classification)
            for metric, classification in dict(self.classifications).items()
        }
        if not classifications:
            raise AdapterInputError("AdapterResultV1.classifications may not be empty")
        for metric in classifications:
            if not isinstance(metric, str) or not metric:
                raise AdapterInputError("AdapterResultV1 classification metrics must be non-empty strings")

        derived_values = dict(self.derived_values)
        for metric, value in derived_values.items():
            if not isinstance(metric, str) or not metric:
                raise AdapterInputError("AdapterResultV1 derived value metrics must be non-empty strings")
            if not isinstance(value, Decimal):
                raise AdapterInputError(f"AdapterResultV1 derived value must be Decimal: {metric}")

        warnings = tuple(self.warnings)
        for warning in warnings:
            if not isinstance(warning, AdapterWarning):
                raise AdapterInputError("AdapterResultV1 warnings must be AdapterWarning objects")

        ranges = dict(self.uncertainty_ranges)
        for metric, metric_range in ranges.items():
            if not isinstance(metric, str) or not metric:
                raise AdapterInputError("AdapterResultV1 uncertainty range keys must be non-empty strings")
            if not isinstance(metric_range, AdapterMetricRange):
                raise AdapterInputError("AdapterResultV1 uncertainty ranges must be AdapterMetricRange objects")
            for range_metric in (metric_range.low_metric, metric_range.base_metric, metric_range.high_metric):
                if range_metric not in derived_values:
                    raise AdapterInputError(f"Uncertainty range metric is missing from derived values: {range_metric}")

        object.__setattr__(self, "classifications", MappingProxyType(classifications))
        object.__setattr__(self, "derived_values", MappingProxyType(derived_values))
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "uncertainty_ranges", MappingProxyType(ranges))


@runtime_checkable
class StrategyAdapterV1(Protocol):
    def build_engine_input(
        self,
        observations: tuple[Observation, ...],
        *,
        calculated_at: datetime | None = None,
    ) -> AdapterResultV1:
        ...


def verified_config_observation(
    *,
    strategy_id: str,
    metric: str,
    value: str,
    unit: str,
    source_locator: str,
    retrieved_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Observation:
    active_time = utc_now() if retrieved_at is None else normalize_utc(retrieved_at)
    return Observation(
        observation_id=_observation_id("verified-config", strategy_id, metric, active_time),
        entity_type="strategy",
        entity_id=strategy_id,
        metric=metric,
        value=decimal_from_text(value),
        unit=unit,
        quote_currency="USD" if unit.upper() == "USD" else None,
        source_provider="verified-config",
        source_type=SourceType.VERIFIED_CONFIG,
        source_locator=source_locator,
        observed_at=active_time,
        retrieved_at=active_time,
        fresh_until=active_time + timedelta(days=365),
        status=ObservationStatus.FRESH,
        metadata={"classification": ValueClassification.CONFIG.value, **(metadata or {})},
    )


def derived_observation(
    *,
    provider: str,
    entity_type: str,
    entity_id: str,
    metric: str,
    value: Decimal,
    unit: str,
    source_locator: str,
    input_observation_ids: tuple[str, ...],
    retrieved_at: datetime | None = None,
    freshness: timedelta = timedelta(minutes=5),
    metadata: dict[str, Any] | None = None,
) -> Observation:
    active_time = utc_now() if retrieved_at is None else normalize_utc(retrieved_at)
    return Observation(
        observation_id=_observation_id(provider, entity_id, metric, active_time),
        entity_type=entity_type,
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency="USD" if unit.upper() == "USD" else None,
        source_provider=provider,
        source_type=SourceType.DERIVED_PROVIDER_DATA,
        source_locator=source_locator,
        observed_at=active_time,
        retrieved_at=active_time,
        fresh_until=active_time + freshness,
        status=ObservationStatus.FRESH,
        metadata={
            "classification": ValueClassification.DERIVED.value,
            "input_observation_ids": input_observation_ids,
            **(metadata or {}),
        },
    )


def live_observation(
    *,
    provider: str,
    entity_type: str,
    entity_id: str,
    metric: str,
    value: Decimal,
    unit: str,
    source_locator: str,
    source_type: SourceType,
    retrieved_at: datetime | None = None,
    observed_at: datetime | None = None,
    freshness: timedelta = timedelta(minutes=5),
    metadata: dict[str, Any] | None = None,
) -> Observation:
    active_time = utc_now() if retrieved_at is None else normalize_utc(retrieved_at)
    observed_time = active_time if observed_at is None else normalize_utc(observed_at)
    return Observation(
        observation_id=_observation_id(provider, entity_id, metric, observed_time),
        entity_type=entity_type,
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency="USD" if unit.upper() == "USD" else None,
        source_provider=provider,
        source_type=source_type,
        source_locator=source_locator,
        observed_at=observed_time,
        retrieved_at=active_time,
        fresh_until=active_time + freshness,
        status=ObservationStatus.FRESH,
        metadata={"classification": ValueClassification.LIVE.value, **(metadata or {})},
    )


def index_required_observations(
    observations: tuple[Observation, ...],
    active_time: datetime,
    *,
    required_metrics: tuple[str, ...],
    adapter_name: str,
) -> dict[str, Observation]:
    by_metric = {observation.metric: observation for observation in observations}
    missing = [metric for metric in required_metrics if metric not in by_metric]
    if missing:
        raise AdapterInputError(f"Missing required {adapter_name} observations: {', '.join(missing)}")
    for metric in required_metrics:
        observation = by_metric[metric]
        if observation.status_at(active_time) != ObservationStatus.FRESH:
            raise AdapterInputError(f"Required {adapter_name} observation is not fresh: {metric}")
        if observation.value is None:
            raise AdapterInputError(f"Required {adapter_name} observation has no value: {metric}")
    return {metric: by_metric[metric] for metric in required_metrics}


def observation_decimal_value(observation: Observation) -> Decimal:
    if observation.value is None:
        raise AdapterInputError(f"Observation {observation.metric} has no value")
    return observation.value


def classify_observation(observation: Observation) -> ValueClassification:
    raw = observation.metadata.get("classification")
    if raw is not None:
        return ValueClassification(raw)
    if observation.source_type in {SourceType.MARKET_API, SourceType.ONCHAIN, SourceType.OFFICIAL_API}:
        return ValueClassification.LIVE
    if observation.source_type == SourceType.VERIFIED_CONFIG:
        return ValueClassification.CONFIG
    if observation.source_type == SourceType.DERIVED_PROVIDER_DATA:
        return ValueClassification.DERIVED
    raise AdapterInputError(f"Observation {observation.metric} is missing classification metadata")


def require_positive(value: Decimal, field_name: str) -> None:
    if value <= Decimal("0"):
        raise AdapterInputError(f"{field_name} must be positive")


def require_non_negative(value: Decimal, field_name: str) -> None:
    if value < Decimal("0"):
        raise AdapterInputError(f"{field_name} must be non-negative")


def require_probability(value: Decimal, field_name: str) -> None:
    if value < Decimal("0") or value > Decimal("1"):
        raise AdapterInputError(f"{field_name} must be between 0 and 1")


def require_bps(value: Decimal, field_name: str) -> None:
    if value < Decimal("0") or value > decimal_from_int(10_000):
        raise AdapterInputError(f"{field_name} must be between 0 and 10000")


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdapterInputError("Adapter timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)


def unix_seconds(value: datetime) -> int:
    return int(value.timestamp())


def _observation_id(provider: str, entity_id: str, metric: str, observed_at: datetime) -> str:
    key = f"{provider}|{entity_id}|{metric}|{observed_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
