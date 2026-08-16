"""Farmers World resource-production adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType

from app.adapters.contract import (
    AdapterInputError,
    AdapterResultV1,
    ValueClassification,
    classify_observation,
    derived_observation,
    index_required_observations,
    normalize_utc,
    observation_decimal_value,
    require_non_negative,
    require_positive,
    utc_now,
    verified_config_observation,
)
from app.engine.calculator import MODEL_VERSION
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT
from app.engine.inputs import BreakEvenBasis, CapitalInput, CostInput, RewardInput, StrategyEconomicsInput
from app.engine.money import Money
from app.sources.observations import Observation
from app.strategies.farmers_world import FarmersWorldAxeStrategyDefinition


FarmersWorldAdapterResult = AdapterResultV1


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
        active_time = utc_now() if calculated_at is None else normalize_utc(calculated_at)
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

        require_positive(tool_count, TOOL_COUNT)
        require_positive(cycles_per_day, CYCLES_PER_DAY)
        require_positive(cycle_hours, CYCLE_HOURS)
        require_positive(fww_output_per_cycle, FWW_OUTPUT_PER_CYCLE)
        require_non_negative(fwf_input_per_cycle, FWF_INPUT_PER_CYCLE)
        require_non_negative(fwg_input_per_cycle, FWG_INPUT_PER_CYCLE)
        require_non_negative(entry_value_usd, ENTRY_VALUE_USD)
        require_non_negative(exit_value_usd, EXIT_VALUE_USD)
        require_non_negative(fww_reference_price_usd, FWW_REFERENCE_PRICE_USD)
        require_non_negative(fww_realizable_value_day_usd, FWW_REALIZABLE_VALUE_DAY_USD)
        require_non_negative(fwf_operating_cost_day_usd, FWF_OPERATING_COST_DAY_USD)
        require_non_negative(fwg_operating_cost_day_usd, FWG_OPERATING_COST_DAY_USD)
        require_non_negative(transaction_cost_day_usd, TRANSACTION_COST_DAY_USD)

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

        return AdapterResultV1(
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
        require_positive(value, name)
    require_non_negative(fwf_input_per_cycle, FWF_INPUT_PER_CYCLE)
    require_non_negative(fwg_input_per_cycle, FWG_INPUT_PER_CYCLE)

    production_cycles = FINANCIAL_DECIMAL_CONTEXT.multiply(tool_count, cycles_per_day)
    return FarmersWorldAxeDailyQuantities(
        fww_output_day=FINANCIAL_DECIMAL_CONTEXT.multiply(production_cycles, fww_output_per_cycle),
        fwf_input_day=FINANCIAL_DECIMAL_CONTEXT.multiply(production_cycles, fwf_input_per_cycle),
        fwg_input_day=FINANCIAL_DECIMAL_CONTEXT.multiply(production_cycles, fwg_input_per_cycle),
    )


def _index_required_observations(observations: tuple[Observation, ...], active_time: datetime) -> dict[str, Observation]:
    return index_required_observations(
        observations,
        active_time,
        required_metrics=REQUIRED_METRICS,
        adapter_name="Farmers World",
    )


def _value(observation: Observation) -> Decimal:
    return observation_decimal_value(observation)


def _classification(observation: Observation) -> ValueClassification:
    return classify_observation(observation)
