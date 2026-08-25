"""Live probe for the DeFi Kingdoms Jeweler adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.adapters.defi_kingdoms_jeweler import (
    CLAIM_TRANSACTION_COST_USD,
    EMERGENCY_EXIT_VALUE_USD,
    ENTRY_VALUE_USD,
    JEWEL_REFERENCE_PRICE_USD,
    LOCK_DAYS,
    LOCKED_JEWEL_AMOUNT,
    MAX_LOCK_DAYS,
    REWARD_REALIZABLE_VALUE_USD,
    YESTERDAY_CJEWEL_BALANCE,
    YESTERDAY_REWARD_JEWEL,
    ValueClassification,
    calculate_jeweler_reward_projection,
    derived_observation,
    verified_config_observation,
    DfkJewelerAdapter,
)
from app.config.settings import get_settings
from app.engine.calculator import calculate_strategy_roi
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_int, decimal_from_text
from app.sources.amm import ConstantProductPool, quote_exact_input, spot_price
from app.sources.evm import ContractCallObservationRequest, ContractCallOutput, EvmJsonRpcSource, decode_address_word
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1, DfkJewelerStrategyDefinition

GET_YESTERDAY_APR_DATA = "0x16886540"
GET_RESERVES = "0x0902f1ac"
TOKEN0 = "0x0dfe1681"
TOKEN1 = "0xd21220a7"
WEI_PER_TOKEN = Decimal("1000000000000000000")


def run_probe(strategy: DfkJewelerStrategyDefinition = DFK_CJEWEL_MAX_LOCK_V1) -> dict[str, Any]:
    observations = load_live_observations(strategy=strategy)
    adapter_result = DfkJewelerAdapter(strategy).build_engine_input(observations)
    roi = calculate_strategy_roi(adapter_result.economics_input)
    return {
        "status": "ok",
        "strategy_id": strategy.strategy_id,
        "strategy_version": strategy.strategy_version,
        "observations": [_observation_payload(observation) for observation in observations],
        "classifications": {key: value.value for key, value in adapter_result.classifications.items()},
        "derived_values": {key: str(value) for key, value in adapter_result.derived_values.items()},
        "roi": {
            "total_capital_usd": str(roi.total_capital.amount),
            "recoverable_capital_usd": str(roi.recoverable_capital.amount),
            "gross_nominal_earnings_day_usd": str(roi.gross_nominal_earnings_day.amount),
            "realizable_earnings_day_usd": str(roi.realizable_earnings_day.amount),
            "transaction_cost_day_usd": str(roi.transaction_cost_day.amount),
            "net_earnings_day_usd": str(roi.net_earnings_day.amount),
            "break_even_days": str(roi.break_even.days) if roi.break_even.days is not None else None,
            "roi_total_30d": str(roi.roi_total_30d.value) if roi.roi_total_30d.value is not None else None,
            "exit_adjusted_pnl_usd": str(roi.exit_adjusted_pnl.amount),
        },
    }


def load_live_observations(
    active_time: datetime | None = None,
    *,
    strategy: DfkJewelerStrategyDefinition = DFK_CJEWEL_MAX_LOCK_V1,
) -> tuple[Observation, ...]:
    settings = get_settings()
    freshness_window = timedelta(seconds=settings.dfk_chain_observation_freshness_seconds)
    source = EvmJsonRpcSource(
        provider_name="dfk-chain-rpc",
        rpc_url=settings.dfk_chain_rpc_url,
        timeout_seconds=settings.market_data_http_timeout_seconds,
        max_retries=settings.market_data_http_max_retries,
    )
    try:
        chain_id = source.observe_chain_id(freshness_window)
        if chain_id.value != Decimal(strategy.chain_id):
            raise RuntimeError(f"DFK Chain RPC returned chain id {chain_id.value}; expected {strategy.chain_id}")

        gas_price = source.observe_gas_price_wei(freshness_window)
        raw_apr = source.observe_contract_call_words(
            ContractCallObservationRequest(
                to_address=strategy.c_jewel_contract,
                data=GET_YESTERDAY_APR_DATA,
                block_tag="latest",
                operation="dfk_jeweler_get_yesterday_apr_data",
                freshness_window=freshness_window,
                outputs=(
                    ContractCallOutput(
                        entity_type="strategy",
                        entity_id=strategy.strategy_id,
                        metric="dfk.jeweler.yesterday_cjewel_balance_wei",
                        unit="wei",
                        word_index=0,
                    ),
                    ContractCallOutput(
                        entity_type="strategy",
                        entity_id=strategy.strategy_id,
                        metric="dfk.jeweler.yesterday_reward_jewel_wei",
                        unit="wei",
                        word_index=1,
                    ),
                ),
            )
        )

        pair_state = source.observe_contract_call_words(
            ContractCallObservationRequest(
                to_address=strategy.jewel_usdc_pair,
                data=GET_RESERVES,
                block_tag="latest",
                operation="dfk_pair_get_reserves",
                freshness_window=freshness_window,
                outputs=(
                    ContractCallOutput(
                        entity_type="liquidity_pool",
                        entity_id=strategy.jewel_usdc_pair,
                        metric="amm.reserve0_wei",
                        unit="wei",
                        word_index=0,
                    ),
                    ContractCallOutput(
                        entity_type="liquidity_pool",
                        entity_id=strategy.jewel_usdc_pair,
                        metric="amm.reserve1_wei",
                        unit="wei",
                        word_index=1,
                    ),
                ),
            )
        )

        token0 = decode_address_word(
            source.call(
                "eth_call",
                [{"to": strategy.jewel_usdc_pair, "data": TOKEN0}, "latest"],
                operation="dfk_pair_token0",
            ),
            provider="dfk-chain-rpc",
            operation="dfk_pair_token0",
        )
        token1 = decode_address_word(
            source.call(
                "eth_call",
                [{"to": strategy.jewel_usdc_pair, "data": TOKEN1}, "latest"],
                operation="dfk_pair_token1",
            ),
            provider="dfk-chain-rpc",
            operation="dfk_pair_token1",
        )
        if token0.lower() != strategy.usdc_contract.lower() or token1.lower() != strategy.wjewel_contract.lower():
            raise RuntimeError(f"Unexpected DFK pair tokens: token0={token0}, token1={token1}")

        observations = _build_probe_observations(
            strategy=strategy,
            chain_id=chain_id,
            gas_price=gas_price,
            raw_apr=raw_apr,
            pair_state=pair_state,
            retrieved_at=active_time,
        )
        return observations
    finally:
        source.close()


def _build_probe_observations(
    *,
    strategy,
    chain_id: Observation,
    gas_price: Observation,
    raw_apr: tuple[Observation, ...],
    pair_state: tuple[Observation, ...],
    retrieved_at: datetime | None = None,
) -> tuple[Observation, ...]:
    retrieved_at = datetime.now(UTC) if retrieved_at is None else retrieved_at.astimezone(UTC)
    locked_jewel = decimal_from_text(strategy.locked_jewel_amount)
    lock_days = Decimal(strategy.lock_days)
    max_lock_days = Decimal(strategy.max_lock_days)
    daily_balance = _wei_to_token(raw_apr[0].value)
    daily_reward = _wei_to_token(raw_apr[1].value)
    reward_projection = calculate_jeweler_reward_projection(
        locked_jewel=locked_jewel,
        lock_days=lock_days,
        max_lock_days=max_lock_days,
        yesterday_cjewel_balance=daily_balance,
        yesterday_reward_jewel=daily_reward,
    )

    reserve0 = _wei_to_token(pair_state[0].value)
    reserve1 = _wei_to_token(pair_state[1].value)
    pool = ConstantProductPool(
        token0_id=strategy.usdc_contract.lower(),
        token1_id=strategy.wjewel_contract.lower(),
        reserve0=reserve0,
        reserve1=reserve1,
        fee_bps=strategy.dex_fee_bps,
    )
    price = spot_price(pool, base_token_id=strategy.wjewel_contract.lower())
    entry_value = FINANCIAL_DECIMAL_CONTEXT.multiply(locked_jewel, price)
    emergency_exit_amount = FINANCIAL_DECIMAL_CONTEXT.multiply(
        locked_jewel,
        FINANCIAL_DECIMAL_CONTEXT.divide(
            decimal_from_int(10_000 - strategy.emergency_withdrawal_penalty_bps),
            decimal_from_int(10_000),
        ),
    )
    emergency_exit_value = quote_exact_input(
        pool,
        input_token_id=strategy.wjewel_contract.lower(),
        input_amount=emergency_exit_amount,
    )
    reward_realizable_value = quote_exact_input(
        pool,
        input_token_id=strategy.wjewel_contract.lower(),
        input_amount=reward_projection.reward_jewel_day,
    )
    claim_cost_jewel = FINANCIAL_DECIMAL_CONTEXT.divide(
        FINANCIAL_DECIMAL_CONTEXT.multiply(_require_decimal_value(gas_price), Decimal(strategy.claim_reward_gas_units)),
        WEI_PER_TOKEN,
    )
    claim_cost_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(claim_cost_jewel, price)
    source_locator = f"dfk-jeweler-strategy:{strategy.strategy_id}:{strategy.strategy_version}"

    config_observations = (
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=LOCKED_JEWEL_AMOUNT,
            value=strategy.locked_jewel_amount,
            unit="JEWEL",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=LOCK_DAYS,
            value=str(strategy.lock_days),
            unit="day",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=MAX_LOCK_DAYS,
            value=str(strategy.max_lock_days),
            unit="day",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
    )
    normalized_live = (
        _live_observation(
            entity_id=strategy.strategy_id,
            metric=YESTERDAY_CJEWEL_BALANCE,
            value=daily_balance,
            unit="cJEWEL",
            source_locator=raw_apr[0].source_locator,
            input_observation_ids=(raw_apr[0].observation_id,),
            retrieved_at=retrieved_at,
        ),
        _live_observation(
            entity_id=strategy.strategy_id,
            metric=YESTERDAY_REWARD_JEWEL,
            value=daily_reward,
            unit="JEWEL",
            source_locator=raw_apr[1].source_locator,
            input_observation_ids=(raw_apr[1].observation_id,),
            retrieved_at=retrieved_at,
        ),
    )
    derived = (
        derived_observation(
            provider="dfk-amm-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=ENTRY_VALUE_USD,
            value=entry_value,
            unit="USD",
            source_locator="amm:dfk-wjewel-usdc:spot",
            input_observation_ids=(pair_state[0].observation_id, pair_state[1].observation_id),
            retrieved_at=retrieved_at,
            metadata={"locked_jewel": str(locked_jewel)},
        ),
        derived_observation(
            provider="dfk-amm-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=EMERGENCY_EXIT_VALUE_USD,
            value=emergency_exit_value,
            unit="USD",
            source_locator="amm:dfk-wjewel-usdc:quote_exact_input",
            input_observation_ids=(pair_state[0].observation_id, pair_state[1].observation_id),
            retrieved_at=retrieved_at,
            metadata={"input_jewel": str(emergency_exit_amount)},
        ),
        derived_observation(
            provider="dfk-amm-derived",
            entity_type="asset",
            entity_id=strategy.reward_token_id,
            metric=JEWEL_REFERENCE_PRICE_USD,
            value=price,
            unit="USD",
            source_locator="amm:dfk-wjewel-usdc:spot",
            input_observation_ids=(pair_state[0].observation_id, pair_state[1].observation_id),
            retrieved_at=retrieved_at,
        ),
        derived_observation(
            provider="dfk-amm-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=REWARD_REALIZABLE_VALUE_USD,
            value=reward_realizable_value,
            unit="USD",
            source_locator="amm:dfk-wjewel-usdc:quote_exact_input",
            input_observation_ids=(pair_state[0].observation_id, pair_state[1].observation_id),
            retrieved_at=retrieved_at,
            metadata={"input_jewel": str(reward_projection.reward_jewel_day)},
        ),
        derived_observation(
            provider="dfk-amm-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=CLAIM_TRANSACTION_COST_USD,
            value=claim_cost_usd,
            unit="USD",
            source_locator="dfk-chain-rpc:eth_gasPrice + configured gas units",
            input_observation_ids=(gas_price.observation_id,),
            retrieved_at=retrieved_at,
            metadata={"gas_units": strategy.claim_reward_gas_units, "gas_cost_jewel": str(claim_cost_jewel)},
        ),
    )
    return (
        chain_id,
        gas_price,
        *raw_apr,
        *pair_state,
        *config_observations,
        *normalized_live,
        *derived,
    )


def _live_observation(
    *,
    entity_id: str,
    metric: str,
    value: Decimal,
    unit: str,
    source_locator: str,
    input_observation_ids: tuple[str, ...],
    retrieved_at: datetime,
) -> Observation:
    return Observation(
        observation_id=_observation_id("dfk-chain-rpc-normalized", entity_id, metric, retrieved_at),
        entity_type="strategy",
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency=None,
        source_provider="dfk-chain-rpc",
        source_type=SourceType.ONCHAIN,
        source_locator=source_locator,
        observed_at=retrieved_at,
        retrieved_at=retrieved_at,
        fresh_until=retrieved_at + timedelta(minutes=5),
        status=ObservationStatus.FRESH,
        metadata={"classification": ValueClassification.LIVE.value, "input_observation_ids": input_observation_ids},
    )


def _wei_to_token(value: Decimal | None) -> Decimal:
    if value is None:
        raise RuntimeError("Expected on-chain wei observation value")
    return FINANCIAL_DECIMAL_CONTEXT.divide(value, WEI_PER_TOKEN)


def _require_decimal_value(observation: Observation) -> Decimal:
    if observation.value is None:
        raise RuntimeError(f"Expected observation value for {observation.metric}")
    return observation.value


def _observation_id(provider: str, entity_id: str, metric: str, observed_at: datetime) -> str:
    key = f"{provider}|{entity_id}|{metric}|{observed_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))


def _observation_payload(observation: Observation) -> dict[str, Any]:
    return {
        "metric": observation.metric,
        "value": str(observation.value) if observation.value is not None else None,
        "unit": observation.unit,
        "classification": observation.metadata.get("classification"),
        "source_provider": observation.source_provider,
        "source_type": observation.source_type.value,
        "status": observation.status.value,
        "retrieved_at": observation.retrieved_at.isoformat(),
        "fresh_until": observation.fresh_until.isoformat(),
    }


def main() -> int:
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
