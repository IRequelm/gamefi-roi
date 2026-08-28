"""Deterministic and live observation loaders for scenario-yield strategies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from app.adapters.contract import (
    AdapterInputError,
    ValueClassification,
    derived_observation,
    live_observation,
    normalize_utc,
)
from app.adapters.scenario_yield import (
    CAPITAL_AT_RISK_USD,
    CURRENT_RECOVERABLE_VALUE_USD,
    GROSS_NOMINAL_VALUE_DAY_USD,
    INITIAL_OPERATING_RESERVE_USD,
    NET_EARNINGS_DAY_HIGH_USD,
    NET_EARNINGS_DAY_LOW_USD,
    NET_EARNINGS_DAY_USD,
    OPERATING_COST_DAY_USD,
    OTHER_COST_DAY_USD,
    REALIZABLE_VALUE_DAY_USD,
    RECOVERABLE_ENTRY_COST_USD,
    SUNK_COST_USD,
    TRANSACTION_COST_DAY_USD,
)
from app.config.settings import Settings, get_settings
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_text
from app.sources.coingecko import CoinGeckoMarketDataSource
from app.sources.market_data import TokenPriceRequest
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.strategies.scenario_yield import ScenarioSupportMetric, ScenarioYieldStrategyDefinition, scenario_metric


REWARD_TOKEN_PRICE_USD = "market.reward_token_price_usd"


def load_fixture_observations(
    active_time: datetime,
    *,
    strategy: ScenarioYieldStrategyDefinition,
) -> tuple[Observation, ...]:
    price = (
        decimal_from_text(strategy.reward.fixture_reward_token_price_usd)
        if strategy.reward.fixture_reward_token_price_usd is not None
        else None
    )
    price_observation = _fixture_price_observation(strategy, active_time, price) if price is not None else None
    return build_scenario_observations(
        active_time,
        strategy=strategy,
        price_observation=price_observation,
    )


def load_live_observations(
    active_time: datetime,
    *,
    strategy: ScenarioYieldStrategyDefinition,
    settings: Settings | None = None,
) -> tuple[Observation, ...]:
    if strategy.reward.price_provider_asset_id is None:
        return build_scenario_observations(active_time, strategy=strategy, price_observation=None)

    active_settings = settings or get_settings()
    source = CoinGeckoMarketDataSource(active_settings)
    try:
        market_observations = source.get_token_prices(
            TokenPriceRequest(
                provider_asset_ids=(strategy.reward.price_provider_asset_id,),
                quote_currency=strategy.reporting_currency,
                freshness_window=timedelta(seconds=active_settings.market_data_price_freshness_seconds),
            )
        )
    finally:
        source.close()

    price_observation = _market_price_observation(strategy, market_observations[0])
    return build_scenario_observations(
        active_time,
        strategy=strategy,
        price_observation=price_observation,
    )


def build_scenario_observations(
    active_time: datetime,
    *,
    strategy: ScenarioYieldStrategyDefinition,
    price_observation: Observation | None,
) -> tuple[Observation, ...]:
    active_time = normalize_utc(active_time)
    support = tuple(_support_observation(strategy, metric, active_time) for metric in strategy.support_metrics)
    assumptions = tuple(
        _assumption_observation(strategy, key, value, active_time)
        for key, value in sorted(strategy.assumptions)
        if _is_decimal_text(value)
    )
    support = (*support, *assumptions)
    economic_inputs = support + ((price_observation,) if price_observation is not None else ())

    if strategy.reward.kind == "token_day" and (price_observation is None or price_observation.value is None):
        return economic_inputs

    values = _economic_values(strategy, price_observation=price_observation)
    input_ids = tuple(observation.observation_id for observation in economic_inputs)
    derived = tuple(
        _derived(
            strategy,
            suffix,
            value,
            active_time,
            source_locator=source_locator,
            input_observation_ids=input_ids,
            note=note,
        )
        for suffix, value, source_locator, note in (
            (SUNK_COST_USD, values[SUNK_COST_USD], strategy.capital.source_locator, strategy.capital.note),
            (
                RECOVERABLE_ENTRY_COST_USD,
                values[RECOVERABLE_ENTRY_COST_USD],
                strategy.capital.source_locator,
                strategy.capital.note,
            ),
            (
                CURRENT_RECOVERABLE_VALUE_USD,
                values[CURRENT_RECOVERABLE_VALUE_USD],
                strategy.capital.source_locator,
                strategy.capital.note,
            ),
            (
                INITIAL_OPERATING_RESERVE_USD,
                values[INITIAL_OPERATING_RESERVE_USD],
                strategy.capital.source_locator,
                strategy.capital.note,
            ),
            (CAPITAL_AT_RISK_USD, values[CAPITAL_AT_RISK_USD], strategy.capital.source_locator, strategy.capital.note),
            (
                GROSS_NOMINAL_VALUE_DAY_USD,
                values[GROSS_NOMINAL_VALUE_DAY_USD],
                strategy.reward.source_locator,
                strategy.reward.note,
            ),
            (
                REALIZABLE_VALUE_DAY_USD,
                values[REALIZABLE_VALUE_DAY_USD],
                strategy.reward.source_locator,
                strategy.reward.note,
            ),
            (
                OPERATING_COST_DAY_USD,
                values[OPERATING_COST_DAY_USD],
                strategy.costs.source_locator,
                strategy.costs.note,
            ),
            (
                TRANSACTION_COST_DAY_USD,
                values[TRANSACTION_COST_DAY_USD],
                strategy.costs.source_locator,
                strategy.costs.note,
            ),
            (OTHER_COST_DAY_USD, values[OTHER_COST_DAY_USD], strategy.costs.source_locator, strategy.costs.note),
            (
                NET_EARNINGS_DAY_USD,
                values[NET_EARNINGS_DAY_USD],
                "GamCryp scenario calculation",
                "Net earnings/day = realizable reward value/day minus operating, transaction, and other costs.",
            ),
        )
    )
    range_observations = _range_observations(
        strategy,
        active_time,
        price_observation=price_observation,
        input_observation_ids=input_ids,
    )
    return (*economic_inputs, *derived, *range_observations)


def _economic_values(
    strategy: ScenarioYieldStrategyDefinition,
    *,
    price_observation: Observation | None,
) -> dict[str, Decimal]:
    gross = _gross_value(strategy, strategy.reward.amount_day, price_observation=price_observation)
    realizable = _realizable_value(strategy, gross)
    operating = decimal_from_text(strategy.costs.operating_cost_day_usd)
    transaction = decimal_from_text(strategy.costs.transaction_cost_day_usd)
    other = decimal_from_text(strategy.costs.other_cost_day_usd)
    net = FINANCIAL_DECIMAL_CONTEXT.subtract(
        FINANCIAL_DECIMAL_CONTEXT.subtract(FINANCIAL_DECIMAL_CONTEXT.subtract(realizable, operating), transaction),
        other,
    )
    return {
        SUNK_COST_USD: decimal_from_text(strategy.capital.sunk_cost_usd),
        RECOVERABLE_ENTRY_COST_USD: decimal_from_text(strategy.capital.recoverable_entry_cost_usd),
        CURRENT_RECOVERABLE_VALUE_USD: decimal_from_text(strategy.capital.current_recoverable_value_usd),
        INITIAL_OPERATING_RESERVE_USD: decimal_from_text(strategy.capital.initial_operating_reserve_usd),
        CAPITAL_AT_RISK_USD: decimal_from_text(strategy.capital.capital_at_risk_usd),
        GROSS_NOMINAL_VALUE_DAY_USD: gross,
        REALIZABLE_VALUE_DAY_USD: realizable,
        OPERATING_COST_DAY_USD: operating,
        TRANSACTION_COST_DAY_USD: transaction,
        OTHER_COST_DAY_USD: other,
        NET_EARNINGS_DAY_USD: net,
    }


def _range_observations(
    strategy: ScenarioYieldStrategyDefinition,
    active_time: datetime,
    *,
    price_observation: Observation | None,
    input_observation_ids: tuple[str, ...],
) -> tuple[Observation, ...]:
    if strategy.uncertainty is None:
        return ()
    low_gross = _gross_value(strategy, strategy.uncertainty.low_reward_amount_day, price_observation=price_observation)
    high_gross = _gross_value(strategy, strategy.uncertainty.high_reward_amount_day, price_observation=price_observation)
    costs = (
        decimal_from_text(strategy.costs.operating_cost_day_usd)
        + decimal_from_text(strategy.costs.transaction_cost_day_usd)
        + decimal_from_text(strategy.costs.other_cost_day_usd)
    )
    low_net = FINANCIAL_DECIMAL_CONTEXT.subtract(_realizable_value(strategy, low_gross), costs)
    high_net = FINANCIAL_DECIMAL_CONTEXT.subtract(_realizable_value(strategy, high_gross), costs)
    return (
        _derived(
            strategy,
            NET_EARNINGS_DAY_LOW_USD,
            low_net,
            active_time,
            source_locator="GamCryp scenario uncertainty calculation",
            input_observation_ids=input_observation_ids,
            note=strategy.uncertainty.description,
        ),
        _derived(
            strategy,
            NET_EARNINGS_DAY_HIGH_USD,
            high_net,
            active_time,
            source_locator="GamCryp scenario uncertainty calculation",
            input_observation_ids=input_observation_ids,
            note=strategy.uncertainty.description,
        ),
    )


def _gross_value(
    strategy: ScenarioYieldStrategyDefinition,
    amount_day: str,
    *,
    price_observation: Observation | None,
) -> Decimal:
    amount = decimal_from_text(amount_day)
    if amount < Decimal("0"):
        raise AdapterInputError(f"{strategy.strategy_id} reward amount must be non-negative")
    if strategy.reward.kind == "usd_day":
        return amount

    if price_observation is None or price_observation.value is None:
        raise AdapterInputError(f"{strategy.strategy_id} requires a live reward-token market price")
    if price_observation.value <= Decimal("0"):
        raise AdapterInputError(f"{strategy.strategy_id} reward-token market price must be strictly positive")
    return FINANCIAL_DECIMAL_CONTEXT.multiply(amount, price_observation.value)


def _realizable_value(strategy: ScenarioYieldStrategyDefinition, gross: Decimal) -> Decimal:
    cash_ratio = decimal_from_text(strategy.reward.cash_realization_ratio)
    haircut_bps = decimal_from_text(strategy.reward.realization_haircut_bps)
    if cash_ratio < Decimal("0") or cash_ratio > Decimal("1"):
        raise AdapterInputError(f"{strategy.strategy_id} cash realization ratio must be between 0 and 1")
    if haircut_bps < Decimal("0") or haircut_bps > Decimal("10000"):
        raise AdapterInputError(f"{strategy.strategy_id} realization haircut bps must be between 0 and 10000")
    haircut_ratio = FINANCIAL_DECIMAL_CONTEXT.divide(Decimal("10000") - haircut_bps, Decimal("10000"))
    return FINANCIAL_DECIMAL_CONTEXT.multiply(FINANCIAL_DECIMAL_CONTEXT.multiply(gross, cash_ratio), haircut_ratio)


def _support_observation(
    strategy: ScenarioYieldStrategyDefinition,
    metric: ScenarioSupportMetric,
    active_time: datetime,
) -> Observation:
    source_type = SourceType(metric.source_type)
    return Observation(
        observation_id=_observation_id(metric.source_provider, strategy.strategy_id, metric.key, active_time),
        entity_type="strategy",
        entity_id=strategy.strategy_id,
        metric=scenario_metric(strategy, f"source.{metric.key}"),
        value=decimal_from_text(metric.value),
        unit=metric.unit,
        quote_currency="USD" if metric.unit.upper() == "USD" else None,
        source_provider=metric.source_provider,
        source_type=source_type,
        source_locator=metric.source_locator,
        observed_at=active_time,
        retrieved_at=active_time,
        fresh_until=active_time + timedelta(days=365),
        status=ObservationStatus.FRESH,
        metadata={
            "classification": ValueClassification.CONFIG.value,
            "note": metric.note,
            "batch": "catalog-expansion-batch1",
        },
    )


def _assumption_observation(
    strategy: ScenarioYieldStrategyDefinition,
    key: str,
    value: object,
    active_time: datetime,
) -> Observation:
    return Observation(
        observation_id=_observation_id("gamcryp-config", strategy.strategy_id, key, active_time),
        entity_type="strategy",
        entity_id=strategy.strategy_id,
        metric=scenario_metric(strategy, f"assumption.{key}"),
        value=decimal_from_text(str(value)),
        unit=_assumption_unit(key),
        quote_currency="USD" if _assumption_unit(key) == "USD" else None,
        source_provider="gamcryp-config",
        source_type=SourceType.VERIFIED_CONFIG,
        source_locator="gamcryp_batch1_data_feasibility_handoff.json",
        observed_at=active_time,
        retrieved_at=active_time,
        fresh_until=active_time + timedelta(days=365),
        status=ObservationStatus.FRESH,
        metadata={
            "classification": ValueClassification.CONFIG.value,
            "note": "Explicit scenario assumption retained for confidence scoring and reproducibility.",
            "batch": "catalog-expansion-batch1",
        },
    )


def _assumption_unit(key: str) -> str:
    if "usd" in key:
        return "USD"
    if "bps" in key:
        return "basis_point"
    if "ratio" in key or "probability" in key:
        return "ratio"
    if key.endswith("_days"):
        return "day"
    return "count"

def _is_decimal_text(value: object) -> bool:
    try:
        decimal_from_text(str(value))
    except Exception:
        return False
    return True


def _fixture_price_observation(
    strategy: ScenarioYieldStrategyDefinition,
    active_time: datetime,
    price: Decimal,
) -> Observation:
    if price <= Decimal("0"):
        raise AdapterInputError(f"{strategy.strategy_id} fixture market price must be strictly positive")
    return live_observation(
        provider="fixture-market",
        entity_type="asset",
        entity_id=strategy.reward.reward_asset_id,
        metric=scenario_metric(strategy, REWARD_TOKEN_PRICE_USD),
        value=price,
        unit=strategy.reporting_currency,
        source_locator=f"fixture:coingecko:{strategy.reward.price_provider_asset_id}",
        source_type=SourceType.MARKET_API,
        retrieved_at=active_time,
        observed_at=active_time,
        freshness=timedelta(minutes=5),
        metadata={
            "provider_asset_id": strategy.reward.price_provider_asset_id,
            "batch": "catalog-expansion-batch1",
        },
    )


def _market_price_observation(
    strategy: ScenarioYieldStrategyDefinition,
    observation: Observation,
) -> Observation:
    metadata = {
        **dict(observation.metadata),
        "classification": ValueClassification.LIVE.value,
        "source_observation_id": observation.observation_id,
        "batch": "catalog-expansion-batch1",
    }
    return Observation(
        observation_id=_observation_id(
            observation.source_provider,
            strategy.strategy_id,
            REWARD_TOKEN_PRICE_USD,
            observation.observed_at or observation.retrieved_at,
        ),
        entity_type="asset",
        entity_id=strategy.reward.reward_asset_id,
        metric=scenario_metric(strategy, REWARD_TOKEN_PRICE_USD),
        value=observation.value,
        unit=observation.unit,
        quote_currency=observation.quote_currency,
        source_provider=observation.source_provider,
        source_type=observation.source_type,
        source_locator=observation.source_locator,
        observed_at=observation.observed_at,
        retrieved_at=observation.retrieved_at,
        fresh_until=observation.fresh_until,
        status=observation.status,
        metadata=metadata,
    )


def _derived(
    strategy: ScenarioYieldStrategyDefinition,
    suffix: str,
    value: Decimal,
    active_time: datetime,
    *,
    source_locator: str,
    input_observation_ids: tuple[str, ...],
    note: str,
) -> Observation:
    return derived_observation(
        provider="scenario-yield-derived",
        entity_type="strategy",
        entity_id=strategy.strategy_id,
        metric=scenario_metric(strategy, suffix),
        value=value,
        unit=strategy.reporting_currency,
        source_locator=source_locator,
        input_observation_ids=input_observation_ids,
        retrieved_at=active_time,
        metadata={
            "note": note,
            "batch": "catalog-expansion-batch1",
        },
    )


def _observation_id(provider: str, entity_id: str, metric: str, observed_at: datetime) -> str:
    observed_at = normalize_utc(observed_at)
    key = f"{provider}|{entity_id}|{metric}|{observed_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
