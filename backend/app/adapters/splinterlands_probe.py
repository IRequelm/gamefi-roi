"""Live probe for the Splinterlands Modern Ranked SPS adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.adapters.splinterlands import (
    BATTLES_PER_DAY,
    CARD_RENTAL_COST_DAY_USD,
    REALIZATION_HAIRCUT_BPS,
    SPS_REFERENCE_PRICE_USD,
    SPS_REWARD_PER_WIN,
    TRANSACTION_COST_DAY_USD,
    WIN_PROBABILITY,
    WIN_PROBABILITY_HIGH,
    WIN_PROBABILITY_LOW,
    SplinterlandsModernRankedAdapter,
    live_observation,
    verified_config_observation,
)
from app.config.settings import get_settings
from app.engine.calculator import calculate_strategy_roi
from app.sources.coingecko import CoinGeckoMarketDataSource
from app.sources.market_data import TokenPriceRequest
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.sources.splinterlands import (
    SEASON_ID,
    SETTINGS_SEASON_ID,
    SplinterlandsGameDataSource,
    SplinterlandsSeasonRequest,
    SplinterlandsSettingsRequest,
)
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1, SplinterlandsModernRankedStrategyDefinition


def run_probe(strategy: SplinterlandsModernRankedStrategyDefinition = SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1) -> dict[str, Any]:
    observations, season_observations = load_live_observations_with_season_probe(strategy=strategy)
    adapter_result = SplinterlandsModernRankedAdapter(strategy).build_engine_input(observations)
    roi = calculate_strategy_roi(adapter_result.economics_input)
    return {
        "status": "ok",
        "strategy_id": strategy.strategy_id,
        "strategy_version": strategy.strategy_version,
        "observations": [_observation_payload(observation) for observation in observations],
        "classifications": {key: value.value for key, value in adapter_result.classifications.items()},
        "derived_values": {key: str(value) for key, value in adapter_result.derived_values.items()},
        "season_probe": [_observation_payload(observation) for observation in season_observations],
        "roi": {
            "total_capital_usd": str(roi.total_capital.amount),
            "sunk_cost_usd": str(roi.sunk_cost.amount),
            "recoverable_capital_usd": str(roi.recoverable_capital.amount),
            "capital_at_risk_usd": str(roi.capital_at_risk.amount),
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


def load_live_observations(
    active_time: datetime | None = None,
    *,
    strategy: SplinterlandsModernRankedStrategyDefinition = SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1,
) -> tuple[Observation, ...]:
    observations, _season_observations = load_live_observations_with_season_probe(active_time, strategy=strategy)
    return observations


def load_live_observations_with_season_probe(
    active_time: datetime | None = None,
    *,
    strategy: SplinterlandsModernRankedStrategyDefinition = SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1,
) -> tuple[tuple[Observation, ...], tuple[Observation, ...]]:
    settings = get_settings()
    game_freshness = timedelta(seconds=settings.splinterlands_observation_freshness_seconds)
    price_freshness = timedelta(seconds=settings.market_data_price_freshness_seconds)

    splinterlands = SplinterlandsGameDataSource(settings)
    coingecko = CoinGeckoMarketDataSource(settings)
    try:
        settings_observations = splinterlands.get_settings(SplinterlandsSettingsRequest(freshness_window=game_freshness))
        season_id = _require_metric(settings_observations, SETTINGS_SEASON_ID)
        if season_id.value is None:
            raise RuntimeError("Splinterlands settings did not return a season id")
        season_observations = splinterlands.get_season(
            SplinterlandsSeasonRequest(season_id=str(season_id.value), freshness_window=game_freshness)
        )
        sps_price = tuple(
            coingecko.get_token_prices(
                TokenPriceRequest(
                    provider_asset_ids=(strategy.reward_coingecko_asset_id,),
                    quote_currency=strategy.reporting_currency,
                    freshness_window=price_freshness,
                )
            )
        )

        observations = _build_probe_observations(
            strategy=strategy,
            settings_observations=settings_observations,
            season_observations=season_observations,
            sps_price=sps_price,
            retrieved_at=active_time,
        )
        return observations, season_observations
    finally:
        splinterlands.close()
        coingecko.close()


def _build_probe_observations(
    *,
    strategy,
    settings_observations: tuple[Observation, ...],
    season_observations: tuple[Observation, ...],
    sps_price: tuple[Observation, ...],
    retrieved_at: datetime | None = None,
) -> tuple[Observation, ...]:
    retrieved_at = datetime.now(UTC) if retrieved_at is None else retrieved_at.astimezone(UTC)
    _require_fresh_values((*settings_observations, *season_observations, *sps_price))
    _require_metric(season_observations, SEASON_ID)
    price = _require_metric(sps_price, "token.price")
    if price.value is None:
        raise RuntimeError("CoinGecko SPS/USD price is missing")

    sps_reference_price = live_observation(
        provider=price.source_provider,
        entity_type="asset",
        entity_id=strategy.reward_token_id,
        metric=SPS_REFERENCE_PRICE_USD,
        value=price.value,
        unit="USD",
        source_locator=price.source_locator,
        source_type=SourceType.MARKET_API,
        retrieved_at=price.retrieved_at,
        observed_at=price.observed_at,
        freshness=price.fresh_until - price.retrieved_at,
        metadata={
            "provider_asset_id": strategy.reward_coingecko_asset_id,
            "input_observation_id": price.observation_id,
        },
    )
    source_locator = f"splinterlands-strategy:{strategy.strategy_id}:{strategy.strategy_version}"
    config = (
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=BATTLES_PER_DAY,
            value=strategy.battles_per_day,
            unit="battle/day",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=WIN_PROBABILITY,
            value=strategy.win_probability,
            unit="probability",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=WIN_PROBABILITY_LOW,
            value=strategy.win_probability_low,
            unit="probability",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=WIN_PROBABILITY_HIGH,
            value=strategy.win_probability_high,
            unit="probability",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=SPS_REWARD_PER_WIN,
            value=strategy.expected_sps_reward_per_win,
            unit=strategy.reward_token_symbol,
            source_locator=source_locator,
            retrieved_at=retrieved_at,
            metadata={"basis": "representative observed ranked SPS reward per win"},
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=REALIZATION_HAIRCUT_BPS,
            value=strategy.realization_haircut_bps,
            unit="basis_point",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=CARD_RENTAL_COST_DAY_USD,
            value=strategy.card_rental_cost_day_usd,
            unit="USD",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
            metadata={"basis": "minimum viable daily real-card rental operating assumption"},
        ),
        verified_config_observation(
            strategy_id=strategy.strategy_id,
            metric=TRANSACTION_COST_DAY_USD,
            value=strategy.transaction_cost_day_usd,
            unit="USD",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
            metadata={"basis": "SPS reward realization modeled off-platform; no claim gas in baseline"},
        ),
    )
    return (*settings_observations, sps_reference_price, *config)


def _require_fresh_values(observations: tuple[Observation, ...]) -> None:
    for observation in observations:
        if observation.status_at(observation.retrieved_at) != ObservationStatus.FRESH:
            raise RuntimeError(f"Required live observation is not fresh: {observation.metric}")
        if observation.value is None:
            raise RuntimeError(f"Required live observation has no value: {observation.metric}")


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
