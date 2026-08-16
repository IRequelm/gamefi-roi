"""DeFi Kingdoms Jeweler adapter."""

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
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_int
from app.engine.inputs import BreakEvenBasis, CapitalInput, CostInput, RewardInput, StrategyEconomicsInput
from app.engine.money import Money
from app.sources.observations import Observation
from app.strategies.defi_kingdoms import DfkJewelerStrategyDefinition


DfkJewelerAdapterResult = AdapterResultV1


LOCKED_JEWEL_AMOUNT = "dfk.jeweler.locked_jewel_amount"
LOCK_DAYS = "dfk.jeweler.lock_days"
MAX_LOCK_DAYS = "dfk.jeweler.max_lock_days"
YESTERDAY_CJEWEL_BALANCE = "dfk.jeweler.yesterday_cjewel_balance"
YESTERDAY_REWARD_JEWEL = "dfk.jeweler.yesterday_reward_jewel"
ENTRY_VALUE_USD = "dfk.jeweler.entry_value_usd"
EMERGENCY_EXIT_VALUE_USD = "dfk.jeweler.emergency_exit_value_usd"
JEWEL_REFERENCE_PRICE_USD = "dfk.jeweler.jewel_reference_price_usd"
REWARD_REALIZABLE_VALUE_USD = "dfk.jeweler.reward_realizable_value_usd"
CLAIM_TRANSACTION_COST_USD = "dfk.jeweler.claim_transaction_cost_usd"

REQUIRED_METRICS = (
    LOCKED_JEWEL_AMOUNT,
    LOCK_DAYS,
    MAX_LOCK_DAYS,
    YESTERDAY_CJEWEL_BALANCE,
    YESTERDAY_REWARD_JEWEL,
    ENTRY_VALUE_USD,
    EMERGENCY_EXIT_VALUE_USD,
    JEWEL_REFERENCE_PRICE_USD,
    REWARD_REALIZABLE_VALUE_USD,
    CLAIM_TRANSACTION_COST_USD,
)


class DfkJewelerAdapter:
    def __init__(self, strategy: DfkJewelerStrategyDefinition) -> None:
        self.strategy = strategy

    def build_engine_input(
        self,
        observations: tuple[Observation, ...],
        *,
        calculated_at: datetime | None = None,
    ) -> DfkJewelerAdapterResult:
        active_time = utc_now() if calculated_at is None else normalize_utc(calculated_at)
        by_metric = _index_required_observations(observations, active_time)

        locked_jewel = _value(by_metric[LOCKED_JEWEL_AMOUNT])
        lock_days = _value(by_metric[LOCK_DAYS])
        max_lock_days = _value(by_metric[MAX_LOCK_DAYS])
        yesterday_cjewel_balance = _value(by_metric[YESTERDAY_CJEWEL_BALANCE])
        yesterday_reward_jewel = _value(by_metric[YESTERDAY_REWARD_JEWEL])
        entry_value_usd = _value(by_metric[ENTRY_VALUE_USD])
        emergency_exit_value_usd = _value(by_metric[EMERGENCY_EXIT_VALUE_USD])
        jewel_reference_price_usd = _value(by_metric[JEWEL_REFERENCE_PRICE_USD])
        reward_realizable_value_usd = _value(by_metric[REWARD_REALIZABLE_VALUE_USD])
        claim_transaction_cost_usd = _value(by_metric[CLAIM_TRANSACTION_COST_USD])

        require_positive(locked_jewel, LOCKED_JEWEL_AMOUNT)
        require_positive(lock_days, LOCK_DAYS)
        require_positive(max_lock_days, MAX_LOCK_DAYS)
        require_positive(yesterday_cjewel_balance, YESTERDAY_CJEWEL_BALANCE)
        require_non_negative(yesterday_reward_jewel, YESTERDAY_REWARD_JEWEL)
        require_non_negative(entry_value_usd, ENTRY_VALUE_USD)
        require_non_negative(emergency_exit_value_usd, EMERGENCY_EXIT_VALUE_USD)
        require_non_negative(reward_realizable_value_usd, REWARD_REALIZABLE_VALUE_USD)
        require_non_negative(claim_transaction_cost_usd, CLAIM_TRANSACTION_COST_USD)

        reward_projection = calculate_jeweler_reward_projection(
            locked_jewel=locked_jewel,
            lock_days=lock_days,
            max_lock_days=max_lock_days,
            yesterday_cjewel_balance=yesterday_cjewel_balance,
            yesterday_reward_jewel=yesterday_reward_jewel,
        )
        gross_nominal_value_day = FINANCIAL_DECIMAL_CONTEXT.multiply(
            reward_projection.reward_jewel_day,
            jewel_reference_price_usd,
        )

        economics_input = StrategyEconomicsInput(
            strategy_id=self.strategy.strategy_id,
            strategy_version=self.strategy.strategy_version,
            model_version=MODEL_VERSION,
            reporting_currency="USD",
            capital=CapitalInput(
                sunk_cost=Money.zero("USD"),
                recoverable_entry_cost=Money(entry_value_usd, "USD"),
                current_recoverable_value=Money(emergency_exit_value_usd, "USD"),
                initial_operating_reserve=Money.zero("USD"),
                capital_at_risk=Money(entry_value_usd, "USD"),
            ),
            rewards=RewardInput(
                gross_nominal_value_day=Money(gross_nominal_value_day, "USD"),
                realizable_value_day=Money(reward_realizable_value_usd, "USD"),
            ),
            costs=CostInput(
                operating_cost_day=Money.zero("USD"),
                transaction_cost_day=Money(claim_transaction_cost_usd, "USD"),
                other_cost_day=Money.zero("USD"),
            ),
            cumulative_net_cash_earnings=Money.zero("USD"),
            total_cash_invested_to_date=Money(entry_value_usd, "USD"),
            break_even_basis=BreakEvenBasis(self.strategy.break_even_basis),
            input_observation_ids=tuple(by_metric[metric].observation_id for metric in REQUIRED_METRICS),
            assumptions=MappingProxyType(
                {
                    "claim_interval_days": self.strategy.claim_interval_days,
                    "capital_at_risk_basis": "total entry value while JEWEL remains locked",
                    "emergency_withdrawal_penalty_bps": self.strategy.emergency_withdrawal_penalty_bps,
                    "reward_projection_basis": "yesterday reward and cJEWEL balance from Jeweler contract",
                }
            ),
        )

        return AdapterResultV1(
            economics_input=economics_input,
            classifications=MappingProxyType(
                {metric: _classification(by_metric[metric]) for metric in REQUIRED_METRICS}
                | {
                    "dfk.jeweler.cjewel_received": ValueClassification.DERIVED,
                    "dfk.jeweler.user_reward_share": ValueClassification.DERIVED,
                    "dfk.jeweler.reward_jewel_day": ValueClassification.DERIVED,
                    "dfk.jeweler.gross_nominal_value_day_usd": ValueClassification.DERIVED,
                }
            ),
            derived_values=MappingProxyType(
                {
                    "dfk.jeweler.cjewel_received": reward_projection.cjewel_received,
                    "dfk.jeweler.user_reward_share": reward_projection.user_share,
                    "dfk.jeweler.reward_jewel_day": reward_projection.reward_jewel_day,
                    "dfk.jeweler.gross_nominal_value_day_usd": gross_nominal_value_day,
                }
            ),
        )


@dataclass(frozen=True)
class DfkJewelerRewardProjection:
    cjewel_received: Decimal
    user_share: Decimal
    reward_jewel_day: Decimal


def calculate_jeweler_reward_projection(
    *,
    locked_jewel: Decimal,
    lock_days: Decimal,
    max_lock_days: Decimal,
    yesterday_cjewel_balance: Decimal,
    yesterday_reward_jewel: Decimal,
) -> DfkJewelerRewardProjection:
    require_positive(locked_jewel, LOCKED_JEWEL_AMOUNT)
    require_positive(lock_days, LOCK_DAYS)
    require_positive(max_lock_days, MAX_LOCK_DAYS)
    require_positive(yesterday_cjewel_balance, YESTERDAY_CJEWEL_BALANCE)
    require_non_negative(yesterday_reward_jewel, YESTERDAY_REWARD_JEWEL)
    cjewel_received = FINANCIAL_DECIMAL_CONTEXT.divide(
        FINANCIAL_DECIMAL_CONTEXT.multiply(locked_jewel, lock_days),
        max_lock_days,
    )
    user_share = FINANCIAL_DECIMAL_CONTEXT.divide(cjewel_received, yesterday_cjewel_balance)
    reward_jewel_day = FINANCIAL_DECIMAL_CONTEXT.multiply(yesterday_reward_jewel, user_share)
    return DfkJewelerRewardProjection(
        cjewel_received=cjewel_received,
        user_share=user_share,
        reward_jewel_day=reward_jewel_day,
    )


def _index_required_observations(observations: tuple[Observation, ...], active_time: datetime) -> dict[str, Observation]:
    return index_required_observations(
        observations,
        active_time,
        required_metrics=REQUIRED_METRICS,
        adapter_name="DFK Jeweler",
    )


def _value(observation: Observation) -> Decimal:
    return observation_decimal_value(observation)


def _classification(observation: Observation) -> ValueClassification:
    return classify_observation(observation)


def decimal_percent_to_bps(value: Decimal) -> Decimal:
    return FINANCIAL_DECIMAL_CONTEXT.multiply(value, decimal_from_int(10_000))
