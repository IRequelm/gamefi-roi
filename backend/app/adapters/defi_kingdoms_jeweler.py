"""DeFi Kingdoms Jeweler adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.engine.calculator import MODEL_VERSION
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_int, decimal_from_text
from app.engine.inputs import BreakEvenBasis, CapitalInput, CostInput, RewardInput, StrategyEconomicsInput
from app.engine.money import Money
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.strategies.defi_kingdoms import DfkJewelerStrategyDefinition


class ValueClassification(StrEnum):
    LIVE = "LIVE"
    DERIVED = "DERIVED"
    CONFIG = "CONFIG"


class AdapterInputError(ValueError):
    """Raised when a strategy adapter cannot safely produce engine inputs."""


@dataclass(frozen=True)
class DfkJewelerAdapterResult:
    economics_input: StrategyEconomicsInput
    classifications: MappingProxyType[str, ValueClassification]
    derived_values: MappingProxyType[str, Decimal]


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
        active_time = _utc_now() if calculated_at is None else _normalize_utc(calculated_at)
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

        _require_positive(locked_jewel, LOCKED_JEWEL_AMOUNT)
        _require_positive(lock_days, LOCK_DAYS)
        _require_positive(max_lock_days, MAX_LOCK_DAYS)
        _require_positive(yesterday_cjewel_balance, YESTERDAY_CJEWEL_BALANCE)
        _require_non_negative(yesterday_reward_jewel, YESTERDAY_REWARD_JEWEL)
        _require_non_negative(entry_value_usd, ENTRY_VALUE_USD)
        _require_non_negative(emergency_exit_value_usd, EMERGENCY_EXIT_VALUE_USD)
        _require_non_negative(reward_realizable_value_usd, REWARD_REALIZABLE_VALUE_USD)
        _require_non_negative(claim_transaction_cost_usd, CLAIM_TRANSACTION_COST_USD)

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

        return DfkJewelerAdapterResult(
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
    _require_positive(locked_jewel, LOCKED_JEWEL_AMOUNT)
    _require_positive(lock_days, LOCK_DAYS)
    _require_positive(max_lock_days, MAX_LOCK_DAYS)
    _require_positive(yesterday_cjewel_balance, YESTERDAY_CJEWEL_BALANCE)
    _require_non_negative(yesterday_reward_jewel, YESTERDAY_REWARD_JEWEL)
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
        raise AdapterInputError(f"Missing required DFK Jeweler observations: {', '.join(missing)}")
    for metric in REQUIRED_METRICS:
        observation = by_metric[metric]
        if observation.status_at(active_time) != ObservationStatus.FRESH:
            raise AdapterInputError(f"Required DFK Jeweler observation is not fresh: {metric}")
        if observation.value is None:
            raise AdapterInputError(f"Required DFK Jeweler observation has no value: {metric}")
    return {metric: by_metric[metric] for metric in REQUIRED_METRICS}


def _value(observation: Observation) -> Decimal:
    if observation.value is None:
        raise AdapterInputError(f"Observation {observation.metric} has no value")
    return observation.value


def _classification(observation: Observation) -> ValueClassification:
    raw = observation.metadata.get("classification")
    if raw is None:
        if observation.source_type == SourceType.ONCHAIN:
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


def decimal_percent_to_bps(value: Decimal) -> Decimal:
    return FINANCIAL_DECIMAL_CONTEXT.multiply(value, decimal_from_int(10_000))
