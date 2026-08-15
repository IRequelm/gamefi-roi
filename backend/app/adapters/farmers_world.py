"""Farmers World resource-production adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.engine.calculator import MODEL_VERSION
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_text
from app.engine.inputs import BreakEvenBasis, CapitalInput, CostInput, RewardInput, StrategyEconomicsInput
from app.engine.money import Money
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.strategies.farmers_world import FarmersWorldAxeStrategyDefinition


class ValueClassification(StrEnum):
    LIVE = "LIVE"
    DERIVED = "DERIVED"
    CONFIG = "CONFIG"


class AdapterInputError(ValueError):
    """Raised when the Farmers World adapter cannot safely produce engine inputs."""


@dataclass(frozen=True)
class FarmersWorldAdapterResult:
    economics_input: StrategyEconomicsInput
    classifications: MappingProxyType[str, ValueClassification]
    derived_values: MappingProxyType[str, Decimal]


TOOL_COUNT = "farmers_world.axe.tool_count"
CYCLES_PER_DAY = "farmers_world.axe.cycles_per_day"
CYCLE_HOURS = "farmers_world.axe.cycle_hours"
FWW_OUTPUT_PER_CYCLE = "farmers_world.axe.fww_output_per_cycle"
FWF_INPUT_PER_CYCLE = "farmers_world.axe.fwf_input_per_cycle"
FWG_INPUT_PER_CYCLE = "farmers_world.axe.fwg_input_per_cycle"
ENTRY_VALUE_USD = "farmers_world.axe.entry_value_usd"
EXIT_VALUE_USD = "farmers_world.axe.exit_value_usd"
FWW_REFERENCE_PRICE_USD = "farmers_world.axe.fww_reference_price_usd"
FWW_REALIZABLE_VALUE_DAY_USD = "farmers_world.axe.fww_realizable_value_day_usd"
FWF_OPERATING_COST_DAY_USD = "farmers_world.axe.fwf_operating_cost_day_usd"
FWG_OPERATING_COST_DAY_USD = "farmers_world.axe.fwg_operating_cost_day_usd"
TRANSACTION_COST_DAY_USD = "farmers_world.axe.transaction_cost_day_usd"

REQUIRED_METRICS = (
    TOOL_COUNT,
    CYCLES_PER_DAY,
    CYCLE_HOURS,
    FWW_OUTPUT_PER_CYCLE,
    FWF_INPUT_PER_CYCLE,
    FWG_INPUT_PER_CYCLE,
    ENTRY_VALUE_USD,
    EXIT_VALUE_USD,
    FWW_REFERENCE_PRICE_USD,
    FWW_REALIZABLE_VALUE_DAY_USD,
    FWF_OPERATING_COST_DAY_USD,
    FWG_OPERATING_COST_DAY_USD,
    TRANSACTION_COST_DAY_USD,
)


class FarmersWorldAxeAdapter:
    def __init__(self, strategy: FarmersWorldAxeStrategyDefinition) -> None:
        self.strategy = strategy

    def build_engine_input(
        self,
        observations: tuple[Observation, ...],
        *,
        calculated_at: datetime | None = None,
    ) -> FarmersWorldAdapterResult:
        active_time = _utc_now() if calculated_at is None else _normalize_utc(calculated_at)
        by_metric = _index_required_observations(observations, active_time)

        tool_count = _value(by_metric[TOOL_COUNT])
        cycles_per_day = _value(by_metric[CYCLES_PER_DAY])
        cycle_hours = _value(by_metric[CYCLE_HOURS])
        fww_output_per_cycle = _value(by_metric[FWW_OUTPUT_PER_CYCLE])
        fwf_input_per_cycle = _value(by_metric[FWF_INPUT_PER_CYCLE])
        fwg_input_per_cycle = _value(by_metric[FWG_INPUT_PER_CYCLE])
        entry_value_usd = _value(by_metric[ENTRY_VALUE_USD])
        exit_value_usd = _value(by_metric[EXIT_VALUE_USD])
        fww_reference_price_usd = _value(by_metric[FWW_REFERENCE_PRICE_USD])
        fww_realizable_value_day_usd = _value(by_metric[FWW_REALIZABLE_VALUE_DAY_USD])
        fwf_operating_cost_day_usd = _value(by_metric[FWF_OPERATING_COST_DAY_USD])
        fwg_operating_cost_day_usd = _value(by_metric[FWG_OPERATING_COST_DAY_USD])
        transaction_cost_day_usd = _value(by_metric[TRANSACTION_COST_DAY_USD])

        _require_positive(tool_count, TOOL_COUNT)
        _require_positive(cycles_per_day, CYCLES_PER_DAY)
        _require_positive(cycle_hours, CYCLE_HOURS)
        _require_positive(fww_output_per_cycle, FWW_OUTPUT_PER_CYCLE)
        _require_non_negative(fwf_input_per_cycle, FWF_INPUT_PER_CYCLE)
        _require_non_negative(fwg_input_per_cycle, FWG_INPUT_PER_CYCLE)
        _require_non_negative(entry_value_usd, ENTRY_VALUE_USD)
        _require_non_negative(exit_value_usd, EXIT_VALUE_USD)
        _require_non_negative(fww_reference_price_usd, FWW_REFERENCE_PRICE_USD)
        _require_non_negative(fww_realizable_value_day_usd, FWW_REALIZABLE_VALUE_DAY_USD)
        _require_non_negative(fwf_operating_cost_day_usd, FWF_OPERATING_COST_DAY_USD)
        _require_non_negative(fwg_operating_cost_day_usd, FWG_OPERATING_COST_DAY_USD)
        _require_non_negative(transaction_cost_day_usd, TRANSACTION_COST_DAY_USD)

        daily = calculate_axe_daily_quantities(
            tool_count=tool_count,
            cycles_per_day=cycles_per_day,
            fww_output_per_cycle=fww_output_per_cycle,
            fwf_input_per_cycle=fwf_input_per_cycle,
            fwg_input_per_cycle=fwg_input_per_cycle,
        )
        gross_nominal_value_day = FINANCIAL_DECIMAL_CONTEXT.multiply(
            daily.fww_output_day,
            fww_reference_price_usd,
        )
        operating_cost_day = FINANCIAL_DECIMAL_CONTEXT.add(
            fwf_operating_cost_day_usd,
            fwg_operating_cost_day_usd,
        )

        economics_input = StrategyEconomicsInput(
            strategy_id=self.strategy.strategy_id,
            strategy_version=self.strategy.strategy_version,
            model_version=MODEL_VERSION,
            reporting_currency=self.strategy.reporting_currency,
            capital=CapitalInput(
                sunk_cost=Money.zero(self.strategy.reporting_currency),
                recoverable_entry_cost=Money(entry_value_usd, self.strategy.reporting_currency),
                current_recoverable_value=Money(exit_value_usd, self.strategy.reporting_currency),
                initial_operating_reserve=Money.zero(self.strategy.reporting_currency),
                capital_at_risk=Money(entry_value_usd, self.strategy.reporting_currency),
            ),
            rewards=RewardInput(
                gross_nominal_value_day=Money(gross_nominal_value_day, self.strategy.reporting_currency),
                realizable_value_day=Money(fww_realizable_value_day_usd, self.strategy.reporting_currency),
            ),
            costs=CostInput(
                operating_cost_day=Money(operating_cost_day, self.strategy.reporting_currency),
                transaction_cost_day=Money(transaction_cost_day_usd, self.strategy.reporting_currency),
                other_cost_day=Money.zero(self.strategy.reporting_currency),
            ),
            cumulative_net_cash_earnings=Money.zero(self.strategy.reporting_currency),
            total_cash_invested_to_date=Money(entry_value_usd, self.strategy.reporting_currency),
            break_even_basis=BreakEvenBasis(self.strategy.break_even_basis),
            input_observation_ids=tuple(by_metric[metric].observation_id for metric in REQUIRED_METRICS),
            assumptions=MappingProxyType(
                {
                    "tool": self.strategy.tool_name,
                    "cycle_hours": str(cycle_hours),
                    "cycles_per_day": str(cycles_per_day),
                    "capital_at_risk_basis": "entry value of the tool NFT while market liquidity remains thin",
                    "transaction_cost_basis": "explicit WAX resource/transaction assumption from strategy config",
                    "production_config_source": "Farmers World docs plus corroborating public tool tables",
                }
            ),
        )

        return FarmersWorldAdapterResult(
            economics_input=economics_input,
            classifications=MappingProxyType(
                {metric: _classification(by_metric[metric]) for metric in REQUIRED_METRICS}
                | {
                    "farmers_world.axe.fww_output_day": ValueClassification.DERIVED,
                    "farmers_world.axe.fwf_input_day": ValueClassification.DERIVED,
                    "farmers_world.axe.fwg_input_day": ValueClassification.DERIVED,
                    "farmers_world.axe.gross_nominal_value_day_usd": ValueClassification.DERIVED,
                    "farmers_world.axe.operating_cost_day_usd": ValueClassification.DERIVED,
                }
            ),
            derived_values=MappingProxyType(
                {
                    "farmers_world.axe.fww_output_day": daily.fww_output_day,
                    "farmers_world.axe.fwf_input_day": daily.fwf_input_day,
                    "farmers_world.axe.fwg_input_day": daily.fwg_input_day,
                    "farmers_world.axe.gross_nominal_value_day_usd": gross_nominal_value_day,
                    "farmers_world.axe.operating_cost_day_usd": operating_cost_day,
                }
            ),
        )


@dataclass(frozen=True)
class FarmersWorldAxeDailyQuantities:
    fww_output_day: Decimal
    fwf_input_day: Decimal
    fwg_input_day: Decimal


def calculate_axe_daily_quantities(
    *,
    tool_count: Decimal,
    cycles_per_day: Decimal,
    fww_output_per_cycle: Decimal,
    fwf_input_per_cycle: Decimal,
    fwg_input_per_cycle: Decimal,
) -> FarmersWorldAxeDailyQuantities:
    for name, value in (
        (TOOL_COUNT, tool_count),
        (CYCLES_PER_DAY, cycles_per_day),
        (FWW_OUTPUT_PER_CYCLE, fww_output_per_cycle),
    ):
        _require_positive(value, name)
    _require_non_negative(fwf_input_per_cycle, FWF_INPUT_PER_CYCLE)
    _require_non_negative(fwg_input_per_cycle, FWG_INPUT_PER_CYCLE)

    production_cycles = FINANCIAL_DECIMAL_CONTEXT.multiply(tool_count, cycles_per_day)
    return FarmersWorldAxeDailyQuantities(
        fww_output_day=FINANCIAL_DECIMAL_CONTEXT.multiply(production_cycles, fww_output_per_cycle),
        fwf_input_day=FINANCIAL_DECIMAL_CONTEXT.multiply(production_cycles, fwf_input_per_cycle),
        fwg_input_day=FINANCIAL_DECIMAL_CONTEXT.multiply(production_cycles, fwg_input_per_cycle),
    )


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
    active_time = _utc_now() if retrieved_at is None else _normalize_utc(retrieved_at)
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
    metadata: dict[str, Any] | None = None,
) -> Observation:
    active_time = _utc_now() if retrieved_at is None else _normalize_utc(retrieved_at)
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
        fresh_until=active_time + timedelta(minutes=5),
        status=ObservationStatus.FRESH,
        metadata={
            "classification": ValueClassification.DERIVED.value,
            "input_observation_ids": input_observation_ids,
            **(metadata or {}),
        },
    )


def _index_required_observations(observations: tuple[Observation, ...], active_time: datetime) -> dict[str, Observation]:
    by_metric = {observation.metric: observation for observation in observations}
    missing = [metric for metric in REQUIRED_METRICS if metric not in by_metric]
    if missing:
        raise AdapterInputError(f"Missing required Farmers World observations: {', '.join(missing)}")
    for metric in REQUIRED_METRICS:
        observation = by_metric[metric]
        if observation.status_at(active_time) != ObservationStatus.FRESH:
            raise AdapterInputError(f"Required Farmers World observation is not fresh: {metric}")
        if observation.value is None:
            raise AdapterInputError(f"Required Farmers World observation has no value: {metric}")
    return {metric: by_metric[metric] for metric in REQUIRED_METRICS}


def _value(observation: Observation) -> Decimal:
    if observation.value is None:
        raise AdapterInputError(f"Observation {observation.metric} has no value")
    return observation.value


def _classification(observation: Observation) -> ValueClassification:
    raw = observation.metadata.get("classification")
    if raw is None:
        if observation.source_type in {SourceType.MARKET_API, SourceType.ONCHAIN, SourceType.OFFICIAL_API}:
            return ValueClassification.LIVE
        if observation.source_type == SourceType.VERIFIED_CONFIG:
            return ValueClassification.CONFIG
        if observation.source_type == SourceType.DERIVED_PROVIDER_DATA:
            return ValueClassification.DERIVED
        raise AdapterInputError(f"Observation {observation.metric} is missing classification metadata")
    return ValueClassification(raw)


def _require_positive(value: Decimal, field_name: str) -> None:
    if value <= Decimal("0"):
        raise AdapterInputError(f"{field_name} must be positive")


def _require_non_negative(value: Decimal, field_name: str) -> None:
    if value < Decimal("0"):
        raise AdapterInputError(f"{field_name} must be non-negative")


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdapterInputError("Adapter timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _observation_id(provider: str, entity_id: str, metric: str, observed_at: datetime) -> str:
    key = f"{provider}|{entity_id}|{metric}|{observed_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
