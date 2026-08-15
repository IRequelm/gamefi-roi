"""Generic ROI engine input contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from app.engine.errors import EngineInputError
from app.engine.money import Money


class BreakEvenBasis(StrEnum):
    TOTAL_CAPITAL = "total_capital"
    SUNK_COST = "sunk_cost"
    CAPITAL_AT_RISK = "capital_at_risk"


@dataclass(frozen=True)
class CapitalInput:
    sunk_cost: Money
    recoverable_entry_cost: Money
    current_recoverable_value: Money
    initial_operating_reserve: Money
    capital_at_risk: Money

    def __post_init__(self) -> None:
        _require_money(self.sunk_cost, "capital.sunk_cost")
        _require_money(self.recoverable_entry_cost, "capital.recoverable_entry_cost")
        _require_money(self.current_recoverable_value, "capital.current_recoverable_value")
        _require_money(self.initial_operating_reserve, "capital.initial_operating_reserve")
        _require_money(self.capital_at_risk, "capital.capital_at_risk")
        for field_name, money in (
            ("capital.sunk_cost", self.sunk_cost),
            ("capital.recoverable_entry_cost", self.recoverable_entry_cost),
            ("capital.current_recoverable_value", self.current_recoverable_value),
            ("capital.initial_operating_reserve", self.initial_operating_reserve),
            ("capital.capital_at_risk", self.capital_at_risk),
        ):
            money.require_non_negative(field_name)
        _require_same_currency(
            "capital",
            self.sunk_cost,
            self.recoverable_entry_cost,
            self.current_recoverable_value,
            self.initial_operating_reserve,
            self.capital_at_risk,
        )


@dataclass(frozen=True)
class RewardInput:
    gross_nominal_value_day: Money
    realizable_value_day: Money

    def __post_init__(self) -> None:
        _require_money(self.gross_nominal_value_day, "rewards.gross_nominal_value_day")
        _require_money(self.realizable_value_day, "rewards.realizable_value_day")
        self.gross_nominal_value_day.require_non_negative("rewards.gross_nominal_value_day")
        self.realizable_value_day.require_non_negative("rewards.realizable_value_day")
        _require_same_currency("rewards", self.gross_nominal_value_day, self.realizable_value_day)


@dataclass(frozen=True)
class CostInput:
    operating_cost_day: Money
    transaction_cost_day: Money
    other_cost_day: Money

    def __post_init__(self) -> None:
        _require_money(self.operating_cost_day, "costs.operating_cost_day")
        _require_money(self.transaction_cost_day, "costs.transaction_cost_day")
        _require_money(self.other_cost_day, "costs.other_cost_day")
        for field_name, money in (
            ("costs.operating_cost_day", self.operating_cost_day),
            ("costs.transaction_cost_day", self.transaction_cost_day),
            ("costs.other_cost_day", self.other_cost_day),
        ):
            money.require_non_negative(field_name)
        _require_same_currency("costs", self.operating_cost_day, self.transaction_cost_day, self.other_cost_day)


@dataclass(frozen=True)
class StrategyEconomicsInput:
    strategy_id: str
    strategy_version: str
    model_version: str
    reporting_currency: str
    capital: CapitalInput
    rewards: RewardInput
    costs: CostInput
    cumulative_net_cash_earnings: Money
    total_cash_invested_to_date: Money
    break_even_basis: BreakEvenBasis
    input_observation_ids: tuple[str, ...] = field(default_factory=tuple)
    assumptions: MappingProxyType[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise EngineInputError("strategy_id is required")
        if not self.strategy_version:
            raise EngineInputError("strategy_version is required")
        if not self.model_version:
            raise EngineInputError("model_version is required")
        if not self.reporting_currency:
            raise EngineInputError("reporting_currency is required")
        if not isinstance(self.capital, CapitalInput):
            raise EngineInputError("capital is required")
        if not isinstance(self.rewards, RewardInput):
            raise EngineInputError("rewards is required")
        if not isinstance(self.costs, CostInput):
            raise EngineInputError("costs is required")
        _require_money(self.cumulative_net_cash_earnings, "cumulative_net_cash_earnings")
        _require_money(self.total_cash_invested_to_date, "total_cash_invested_to_date")
        self.total_cash_invested_to_date.require_non_negative("total_cash_invested_to_date")
        if not isinstance(self.break_even_basis, BreakEvenBasis):
            raise EngineInputError("break_even_basis is required")
        reporting_currency = self.reporting_currency.upper()
        for field_name, money in _money_fields(self):
            money.ensure_currency(reporting_currency, field_name)
        object.__setattr__(self, "reporting_currency", reporting_currency)
        object.__setattr__(self, "input_observation_ids", tuple(self.input_observation_ids))
        if self.assumptions is None:
            raise EngineInputError("assumptions must be a mapping")
        object.__setattr__(self, "assumptions", MappingProxyType(dict(self.assumptions)))


def _money_fields(strategy_input: StrategyEconomicsInput) -> tuple[tuple[str, Money], ...]:
    return (
        ("capital.sunk_cost", strategy_input.capital.sunk_cost),
        ("capital.recoverable_entry_cost", strategy_input.capital.recoverable_entry_cost),
        ("capital.current_recoverable_value", strategy_input.capital.current_recoverable_value),
        ("capital.initial_operating_reserve", strategy_input.capital.initial_operating_reserve),
        ("capital.capital_at_risk", strategy_input.capital.capital_at_risk),
        ("rewards.gross_nominal_value_day", strategy_input.rewards.gross_nominal_value_day),
        ("rewards.realizable_value_day", strategy_input.rewards.realizable_value_day),
        ("costs.operating_cost_day", strategy_input.costs.operating_cost_day),
        ("costs.transaction_cost_day", strategy_input.costs.transaction_cost_day),
        ("costs.other_cost_day", strategy_input.costs.other_cost_day),
        ("cumulative_net_cash_earnings", strategy_input.cumulative_net_cash_earnings),
        ("total_cash_invested_to_date", strategy_input.total_cash_invested_to_date),
    )


def _require_money(value: Money | None, field_name: str) -> None:
    if value is None:
        raise EngineInputError(f"{field_name} is required")
    if not isinstance(value, Money):
        raise EngineInputError(f"{field_name} must be Money")


def _require_same_currency(group_name: str, first: Money, *rest: Money) -> None:
    for money in rest:
        if money.currency != first.currency:
            raise EngineInputError(f"{group_name} currencies must match")
