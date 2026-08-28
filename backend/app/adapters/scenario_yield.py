"""Generic scenario-yield adapter for reproducible post-V1 opportunity models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType

from app.adapters.contract import (
    AdapterInputError,
    AdapterMetricRange,
    AdapterResultV1,
    AdapterWarning,
    classify_observation,
    index_required_observations,
    normalize_utc,
    observation_decimal_value,
    require_non_negative,
    require_positive,
)
from app.engine.calculator import MODEL_VERSION
from app.engine.inputs import BreakEvenBasis, CapitalInput, CostInput, RewardInput, StrategyEconomicsInput
from app.engine.money import Money
from app.sources.observations import Observation
from app.strategies.scenario_yield import ScenarioYieldStrategyDefinition, scenario_metric

SUNK_COST_USD = "capital.sunk_cost_usd"
RECOVERABLE_ENTRY_COST_USD = "capital.recoverable_entry_cost_usd"
CURRENT_RECOVERABLE_VALUE_USD = "capital.current_recoverable_value_usd"
INITIAL_OPERATING_RESERVE_USD = "capital.initial_operating_reserve_usd"
CAPITAL_AT_RISK_USD = "capital.capital_at_risk_usd"
GROSS_NOMINAL_VALUE_DAY_USD = "earnings.gross_nominal_value_day_usd"
REALIZABLE_VALUE_DAY_USD = "earnings.realizable_value_day_usd"
OPERATING_COST_DAY_USD = "costs.operating_cost_day_usd"
TRANSACTION_COST_DAY_USD = "costs.transaction_cost_day_usd"
OTHER_COST_DAY_USD = "costs.other_cost_day_usd"
NET_EARNINGS_DAY_USD = "earnings.net_earnings_day_usd"
NET_EARNINGS_DAY_LOW_USD = "earnings.net_earnings_day_low_usd"
NET_EARNINGS_DAY_HIGH_USD = "earnings.net_earnings_day_high_usd"

REQUIRED_ECONOMIC_SUFFIXES = (
    SUNK_COST_USD,
    RECOVERABLE_ENTRY_COST_USD,
    CURRENT_RECOVERABLE_VALUE_USD,
    INITIAL_OPERATING_RESERVE_USD,
    CAPITAL_AT_RISK_USD,
    GROSS_NOMINAL_VALUE_DAY_USD,
    REALIZABLE_VALUE_DAY_USD,
    OPERATING_COST_DAY_USD,
    TRANSACTION_COST_DAY_USD,
    OTHER_COST_DAY_USD,
)


class ScenarioYieldAdapter:
    """Map explicit scenario economics into Adapter Contract v1 without ROI-core changes."""

    def __init__(self, strategy: ScenarioYieldStrategyDefinition) -> None:
        self.strategy = strategy

    def build_engine_input(
        self,
        observations: tuple[Observation, ...],
        *,
        calculated_at: datetime | None = None,
    ) -> AdapterResultV1:
        active_time = datetime.now(UTC) if calculated_at is None else normalize_utc(calculated_at)
        required_metrics = tuple(scenario_metric(self.strategy, suffix) for suffix in REQUIRED_ECONOMIC_SUFFIXES)
        indexed = index_required_observations(
            observations,
            active_time,
            required_metrics=required_metrics,
            adapter_name=self.strategy.name,
        )

        values = {
            suffix: observation_decimal_value(indexed[scenario_metric(self.strategy, suffix)])
            for suffix in REQUIRED_ECONOMIC_SUFFIXES
        }
        self._validate_values(values)

        total_capital = (
            values[SUNK_COST_USD]
            + values[RECOVERABLE_ENTRY_COST_USD]
            + values[INITIAL_OPERATING_RESERVE_USD]
        )
        economics_input = StrategyEconomicsInput(
            strategy_id=self.strategy.strategy_id,
            strategy_version=self.strategy.strategy_version,
            model_version=MODEL_VERSION,
            reporting_currency=self.strategy.reporting_currency,
            capital=CapitalInput(
                sunk_cost=Money(values[SUNK_COST_USD], self.strategy.reporting_currency),
                recoverable_entry_cost=Money(values[RECOVERABLE_ENTRY_COST_USD], self.strategy.reporting_currency),
                current_recoverable_value=Money(values[CURRENT_RECOVERABLE_VALUE_USD], self.strategy.reporting_currency),
                initial_operating_reserve=Money(values[INITIAL_OPERATING_RESERVE_USD], self.strategy.reporting_currency),
                capital_at_risk=Money(values[CAPITAL_AT_RISK_USD], self.strategy.reporting_currency),
            ),
            rewards=RewardInput(
                gross_nominal_value_day=Money(values[GROSS_NOMINAL_VALUE_DAY_USD], self.strategy.reporting_currency),
                realizable_value_day=Money(values[REALIZABLE_VALUE_DAY_USD], self.strategy.reporting_currency),
            ),
            costs=CostInput(
                operating_cost_day=Money(values[OPERATING_COST_DAY_USD], self.strategy.reporting_currency),
                transaction_cost_day=Money(values[TRANSACTION_COST_DAY_USD], self.strategy.reporting_currency),
                other_cost_day=Money(values[OTHER_COST_DAY_USD], self.strategy.reporting_currency),
            ),
            cumulative_net_cash_earnings=Money(Decimal("0"), self.strategy.reporting_currency),
            total_cash_invested_to_date=Money(total_capital, self.strategy.reporting_currency),
            break_even_basis=BreakEvenBasis(self.strategy.break_even_basis),
            input_observation_ids=tuple(observation.observation_id for observation in observations),
            assumptions=MappingProxyType(
                {
                    **dict(self.strategy.assumptions),
                    "reward_asset": self.strategy.reward.reward_asset_symbol,
                    "reward_model_note": self.strategy.reward.note,
                    "cost_model_note": self.strategy.costs.note,
                    "capital_model_note": self.strategy.capital.note,
                    "hardware_requirements": list(self.strategy.hardware_requirements),
                    "geography_dependency": self.strategy.geography_dependency,
                }
            ),
        )

        classifications = {observation.metric: classify_observation(observation) for observation in observations}
        derived_values = {
            observation.metric: observation_decimal_value(observation)
            for observation in observations
            if classify_observation(observation).value == "DERIVED"
        }
        uncertainty_ranges = self._uncertainty_ranges(derived_values)

        return AdapterResultV1(
            economics_input=economics_input,
            classifications=classifications,
            derived_values=derived_values,
            warnings=tuple(
                AdapterWarning(code=warning.code, message=warning.message, severity=warning.severity)
                for warning in self.strategy.warnings
            ),
            uncertainty_ranges=uncertainty_ranges,
        )

    def _validate_values(self, values: dict[str, Decimal]) -> None:
        total_capital = (
            values[SUNK_COST_USD]
            + values[RECOVERABLE_ENTRY_COST_USD]
            + values[INITIAL_OPERATING_RESERVE_USD]
        )
        require_positive(total_capital, "total_capital")
        require_positive(values[CAPITAL_AT_RISK_USD], "capital_at_risk")
        for suffix, value in values.items():
            require_non_negative(value, suffix)
        if values[GROSS_NOMINAL_VALUE_DAY_USD] > Decimal("0"):
            require_positive(values[REALIZABLE_VALUE_DAY_USD], "realizable_value_day")
        if values[REALIZABLE_VALUE_DAY_USD] > values[GROSS_NOMINAL_VALUE_DAY_USD]:
            raise AdapterInputError("realizable_value_day cannot exceed gross_nominal_value_day")

    def _uncertainty_ranges(
        self,
        derived_values: dict[str, Decimal],
    ) -> dict[str, AdapterMetricRange]:
        if self.strategy.uncertainty is None:
            return {}

        metric = scenario_metric(self.strategy, NET_EARNINGS_DAY_USD)
        low_metric = scenario_metric(self.strategy, NET_EARNINGS_DAY_LOW_USD)
        high_metric = scenario_metric(self.strategy, NET_EARNINGS_DAY_HIGH_USD)
        if low_metric not in derived_values or metric not in derived_values or high_metric not in derived_values:
            raise AdapterInputError(f"Scenario uncertainty range observations are missing for {self.strategy.strategy_id}")
        if derived_values[low_metric] > derived_values[metric] or derived_values[metric] > derived_values[high_metric]:
            raise AdapterInputError(f"Scenario uncertainty range is not ordered for {self.strategy.strategy_id}")

        return {
            metric: AdapterMetricRange(
                metric=metric,
                low_metric=low_metric,
                base_metric=metric,
                high_metric=high_metric,
                unit=self.strategy.reporting_currency,
                description=self.strategy.uncertainty.description,
            )
        }
