"""Live probe for the Farmers World Axe adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.adapters.farmers_world import (
    CYCLE_HOURS,
    CYCLES_PER_DAY,
    ENTRY_VALUE_USD,
    EXIT_VALUE_USD,
    FWF_INPUT_PER_CYCLE,
    FWF_OPERATING_COST_DAY_USD,
    FWG_INPUT_PER_CYCLE,
    FWG_OPERATING_COST_DAY_USD,
    FWW_OUTPUT_PER_CYCLE,
    FWW_REALIZABLE_VALUE_DAY_USD,
    FWW_REFERENCE_PRICE_USD,
    TOOL_COUNT,
    TRANSACTION_COST_DAY_USD,
    FarmersWorldAxeAdapter,
    calculate_axe_daily_quantities,
    derived_observation,
    verified_config_observation,
)
from app.config.settings import get_settings
from app.engine.calculator import calculate_strategy_roi
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_text
from app.sources.alcor import AlcorMarketDataSource, AlcorTickerRequest
from app.sources.amm import ConstantProductPool, quote_exact_input, quote_exact_output, spot_price
from app.sources.atomicassets import AtomicAssetsFloorRequest, AtomicAssetsMarketDataSource
from app.sources.coingecko import CoinGeckoMarketDataSource
from app.sources.market_data import TokenPriceRequest
from app.sources.observations import Observation, ObservationStatus
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1


def run_probe() -> dict[str, Any]:
    strategy = FARMERS_WORLD_AXE_WOOD_V1
    observations = load_live_observations()
    adapter_result = FarmersWorldAxeAdapter(strategy).build_engine_input(observations)
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
            "operating_cost_day_usd": str(roi.operating_cost_day.amount),
            "transaction_cost_day_usd": str(roi.transaction_cost_day.amount),
            "net_earnings_day_usd": str(roi.net_earnings_day.amount),
            "break_even_days": str(roi.break_even.days) if roi.break_even.days is not None else None,
            "roi_total_30d": str(roi.roi_total_30d.value) if roi.roi_total_30d.value is not None else None,
            "exit_adjusted_pnl_usd": str(roi.exit_adjusted_pnl.amount),
        },
    }


def load_live_observations(active_time: datetime | None = None) -> tuple[Observation, ...]:
    settings = get_settings()
    strategy = FARMERS_WORLD_AXE_WOOD_V1
    market_freshness = timedelta(seconds=settings.wax_market_observation_freshness_seconds)
    price_freshness = timedelta(seconds=settings.market_data_price_freshness_seconds)

    alcor = AlcorMarketDataSource(settings)
    atomicassets = AtomicAssetsMarketDataSource(settings)
    coingecko = CoinGeckoMarketDataSource(settings)
    try:
        fww_ticker = alcor.get_ticker(
            AlcorTickerRequest(ticker_id=strategy.fww_wax_ticker_id, freshness_window=market_freshness)
        )
        fwf_ticker = alcor.get_ticker(
            AlcorTickerRequest(ticker_id=strategy.fwf_wax_ticker_id, freshness_window=market_freshness)
        )
        fwg_ticker = alcor.get_ticker(
            AlcorTickerRequest(ticker_id=strategy.fwg_wax_ticker_id, freshness_window=market_freshness)
        )
        floor = atomicassets.get_floor_listing(
            AtomicAssetsFloorRequest(
                collection_name=strategy.tool_collection_name,
                schema_name=strategy.tool_schema_name,
                template_id=strategy.tool_template_id,
                listing_symbol=strategy.market_quote_token_symbol,
                freshness_window=market_freshness,
            )
        )
        wax_price = tuple(
            coingecko.get_token_prices(
                TokenPriceRequest(
                    provider_asset_ids=(strategy.wax_coingecko_asset_id,),
                    quote_currency=strategy.reporting_currency,
                    freshness_window=price_freshness,
                )
            )
        )

        observations = _build_probe_observations(
            strategy=strategy,
            fww_ticker=fww_ticker,
            fwf_ticker=fwf_ticker,
            fwg_ticker=fwg_ticker,
            floor=floor,
            wax_price=wax_price,
            retrieved_at=active_time,
        )
        return observations
    finally:
        alcor.close()
        atomicassets.close()
        coingecko.close()


def _build_probe_observations(
    *,
    strategy,
    fww_ticker: tuple[Observation, ...],
    fwf_ticker: tuple[Observation, ...],
    fwg_ticker: tuple[Observation, ...],
    floor: tuple[Observation, ...],
    wax_price: tuple[Observation, ...],
    retrieved_at: datetime | None = None,
) -> tuple[Observation, ...]:
    retrieved_at = datetime.now(UTC) if retrieved_at is None else retrieved_at.astimezone(UTC)
    _require_fresh_values((*fww_ticker, *fwf_ticker, *fwg_ticker, *floor, *wax_price), retrieved_at)
    _require_market_open(fww_ticker, strategy.fww_wax_ticker_id)
    _require_market_open(fwf_ticker, strategy.fwf_wax_ticker_id)
    _require_market_open(fwg_ticker, strategy.fwg_wax_ticker_id)

    tool_count = decimal_from_text(strategy.tool_count)
    cycles_per_day = decimal_from_text(strategy.cycles_per_day)
    daily = calculate_axe_daily_quantities(
        tool_count=tool_count,
        cycles_per_day=cycles_per_day,
        fww_output_per_cycle=decimal_from_text(strategy.fww_output_per_cycle),
        fwf_input_per_cycle=decimal_from_text(strategy.fwf_input_per_cycle),
        fwg_input_per_cycle=decimal_from_text(strategy.fwg_input_per_cycle),
    )

    fww_pool = _pool_from_ticker(fww_ticker)
    fwf_pool = _pool_from_ticker(fwf_ticker)
    fwg_pool = _pool_from_ticker(fwg_ticker)
    wax_usd = _require_metric(wax_price, "token.price").value
    if wax_usd is None:
        raise RuntimeError("WAX/USD price is missing")

    floor_wax = _require_metric(floor, "atomicassets.nft.floor_price").value
    market_fee_ratio = _require_metric(floor, "atomicassets.collection_market_fee_ratio").value
    if floor_wax is None or market_fee_ratio is None:
        raise RuntimeError("AtomicAssets floor or fee value is missing")

    fww_reference_price_wax = spot_price(fww_pool, base_token_id=strategy.reward_token_id)
    fww_reference_price_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(fww_reference_price_wax, wax_usd)
    fww_realizable_wax = quote_exact_input(
        fww_pool,
        input_token_id=strategy.reward_token_id,
        input_amount=daily.fww_output_day,
    )
    fww_realizable_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(fww_realizable_wax, wax_usd)
    fwf_cost_wax = quote_exact_output(
        fwf_pool,
        output_token_id=strategy.food_token_id,
        output_amount=daily.fwf_input_day,
    )
    fwg_cost_wax = quote_exact_output(
        fwg_pool,
        output_token_id=strategy.repair_token_id,
        output_amount=daily.fwg_input_day,
    )
    fwf_cost_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(fwf_cost_wax, wax_usd)
    fwg_cost_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(fwg_cost_wax, wax_usd)
    entry_value_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(floor_wax, wax_usd)
    exit_multiplier = FINANCIAL_DECIMAL_CONTEXT.subtract(Decimal("1"), market_fee_ratio)
    exit_value_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(
        FINANCIAL_DECIMAL_CONTEXT.multiply(floor_wax, exit_multiplier),
        wax_usd,
    )
    tx_cost_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(decimal_from_text(strategy.transaction_cost_wax_day), wax_usd)

    source_locator = f"farmers-world-strategy:{strategy.strategy_id}:{strategy.strategy_version}"
    config = (
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=TOOL_COUNT,
            value=strategy.tool_count,
            unit="tool",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=CYCLES_PER_DAY,
            value=strategy.cycles_per_day,
            unit="cycle/day",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=CYCLE_HOURS,
            value=strategy.cycle_hours,
            unit="hour",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=FWW_OUTPUT_PER_CYCLE,
            value=strategy.fww_output_per_cycle,
            unit=strategy.reward_token_symbol,
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=FWF_INPUT_PER_CYCLE,
            value=strategy.fwf_input_per_cycle,
            unit=strategy.food_token_symbol,
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=FWG_INPUT_PER_CYCLE,
            value=strategy.fwg_input_per_cycle,
            unit=strategy.repair_token_symbol,
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
    )
    derived = (
        derived_observation(
            provider="farmers-world-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=ENTRY_VALUE_USD,
            value=entry_value_usd,
            unit="USD",
            source_locator="atomicassets floor * CoinGecko WAX/USD",
            input_observation_ids=(_require_metric(floor, "atomicassets.nft.floor_price").observation_id, wax_price[0].observation_id),
            retrieved_at=retrieved_at,
        ),
        derived_observation(
            provider="farmers-world-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=EXIT_VALUE_USD,
            value=exit_value_usd,
            unit="USD",
            source_locator="AtomicAssets floor net marketplace fee * CoinGecko WAX/USD",
            input_observation_ids=(
                _require_metric(floor, "atomicassets.nft.floor_price").observation_id,
                _require_metric(floor, "atomicassets.collection_market_fee_ratio").observation_id,
                wax_price[0].observation_id,
            ),
            retrieved_at=retrieved_at,
        ),
        derived_observation(
            provider="farmers-world-derived",
            entity_type="asset",
            entity_id=strategy.reward_token_id,
            metric=FWW_REFERENCE_PRICE_USD,
            value=fww_reference_price_usd,
            unit="USD",
            source_locator="Alcor FWW/WAX spot * CoinGecko WAX/USD",
            input_observation_ids=tuple(observation.observation_id for observation in fww_ticker) + (wax_price[0].observation_id,),
            retrieved_at=retrieved_at,
        ),
        derived_observation(
            provider="farmers-world-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=FWW_REALIZABLE_VALUE_DAY_USD,
            value=fww_realizable_usd,
            unit="USD",
            source_locator="Alcor FWW/WAX quote_exact_input * CoinGecko WAX/USD",
            input_observation_ids=tuple(observation.observation_id for observation in fww_ticker) + (wax_price[0].observation_id,),
            retrieved_at=retrieved_at,
            metadata={"input_fww": str(daily.fww_output_day), "output_wax": str(fww_realizable_wax)},
        ),
        derived_observation(
            provider="farmers-world-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=FWF_OPERATING_COST_DAY_USD,
            value=fwf_cost_usd,
            unit="USD",
            source_locator="Alcor FWF/WAX quote_exact_output * CoinGecko WAX/USD",
            input_observation_ids=tuple(observation.observation_id for observation in fwf_ticker) + (wax_price[0].observation_id,),
            retrieved_at=retrieved_at,
            metadata={"output_fwf": str(daily.fwf_input_day), "input_wax": str(fwf_cost_wax)},
        ),
        derived_observation(
            provider="farmers-world-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=FWG_OPERATING_COST_DAY_USD,
            value=fwg_cost_usd,
            unit="USD",
            source_locator="Alcor FWG/WAX quote_exact_output * CoinGecko WAX/USD",
            input_observation_ids=tuple(observation.observation_id for observation in fwg_ticker) + (wax_price[0].observation_id,),
            retrieved_at=retrieved_at,
            metadata={"output_fwg": str(daily.fwg_input_day), "input_wax": str(fwg_cost_wax)},
        ),
        derived_observation(
            provider="farmers-world-derived",
            entity_type="strategy",
            entity_id=strategy.strategy_id,
            metric=TRANSACTION_COST_DAY_USD,
            value=tx_cost_usd,
            unit="USD",
            source_locator="configured WAX transaction/resource assumption * CoinGecko WAX/USD",
            input_observation_ids=(wax_price[0].observation_id,),
            retrieved_at=retrieved_at,
            metadata={"transaction_cost_wax_day": strategy.transaction_cost_wax_day},
        ),
    )

    return (*fww_ticker, *fwf_ticker, *fwg_ticker, *floor, *wax_price, *config, *derived)


def _pool_from_ticker(observations: tuple[Observation, ...]) -> ConstantProductPool:
    base_reserve = _require_metric(observations, "alcor.market.base_amm_liquidity")
    target_reserve = _require_metric(observations, "alcor.market.target_amm_liquidity")
    fee_bps = _require_metric(observations, "alcor.market.fee_bps")
    if base_reserve.value is None or target_reserve.value is None or fee_bps.value is None:
        raise RuntimeError("Alcor pool observations must carry values")
    return ConstantProductPool(
        token0_id=base_reserve.unit,
        token1_id=target_reserve.unit,
        reserve0=base_reserve.value,
        reserve1=target_reserve.value,
        fee_bps=int(fee_bps.value),
    )


def _require_fresh_values(observations: tuple[Observation, ...], active_time: datetime) -> None:
    for observation in observations:
        if observation.status_at(active_time) != ObservationStatus.FRESH:
            raise RuntimeError(f"Required live observation is not fresh: {observation.metric}")
        if observation.value is None:
            raise RuntimeError(f"Required live observation has no value: {observation.metric}")


def _require_market_open(observations: tuple[Observation, ...], ticker_id: str) -> None:
    frozen = _require_metric(observations, "alcor.market.frozen")
    if frozen.value != Decimal("0"):
        raise RuntimeError(f"Alcor market is frozen: {ticker_id}")


def _require_metric(observations: tuple[Observation, ...], metric: str) -> Observation:
    for observation in observations:
        if observation.metric == metric:
            return observation
    raise RuntimeError(f"Missing observation metric: {metric}")


def _observation_payload(observation: Observation) -> dict[str, Any]:
    return {
        "entity_id": observation.entity_id,
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
