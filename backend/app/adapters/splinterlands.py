"""Splinterlands Modern Ranked SPS expected-value adapter."""

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
from app.sources.splinterlands import (
    SETTINGS_ENERGY_MAX,
    SETTINGS_ENERGY_REGEN_PER_HOUR,
    SETTINGS_SEASON_END_UNIX,
    SETTINGS_SEASON_ID,
    SETTINGS_STARTER_PACK_PRICE_USD,
)
from app.strategies.splinterlands import SplinterlandsModernRankedStrategyDefinition


class ValueClassification(StrEnum):
    LIVE = "LIVE"
    DERIVED = "DERIVED"
    CONFIG = "CONFIG"


class AdapterInputError(ValueError):
    """Raised when Splinterlands adapter inputs cannot safely produce ROI inputs."""


@dataclass(frozen=True)
class SplinterlandsAdapterResult:
    economics_input: StrategyEconomicsInput
    classifications: MappingProxyType[str, ValueClassification]
    derived_values: MappingProxyType[str, Decimal]


SPELLBOOK_COST_USD = SETTINGS_STARTER_PACK_PRICE_USD
SEASON_ID = SETTINGS_SEASON_ID
SEASON_END_UNIX = SETTINGS_SEASON_END_UNIX
ENERGY_MAX = SETTINGS_ENERGY_MAX
ENERGY_REGEN_PER_HOUR = SETTINGS_ENERGY_REGEN_PER_HOUR
BATTLES_PER_DAY = "splinterlands.modern_ranked.battles_per_day"
WIN_PROBABILITY = "splinterlands.modern_ranked.win_probability"
WIN_PROBABILITY_LOW = "splinterlands.modern_ranked.win_probability_low"
WIN_PROBABILITY_HIGH = "splinterlands.modern_ranked.win_probability_high"
SPS_REWARD_PER_WIN = "splinterlands.modern_ranked.sps_reward_per_win"
SPS_REFERENCE_PRICE_USD = "splinterlands.modern_ranked.sps_reference_price_usd"
REALIZATION_HAIRCUT_BPS = "splinterlands.modern_ranked.realization_haircut_bps"
CARD_RENTAL_COST_DAY_USD = "splinterlands.modern_ranked.card_rental_cost_day_usd"
TRANSACTION_COST_DAY_USD = "splinterlands.modern_ranked.transaction_cost_day_usd"

REQUIRED_METRICS = (
    SPELLBOOK_COST_USD,
    SEASON_ID,
    SEASON_END_UNIX,
    ENERGY_MAX,
    ENERGY_REGEN_PER_HOUR,
    BATTLES_PER_DAY,
    WIN_PROBABILITY,
    WIN_PROBABILITY_LOW,
    WIN_PROBABILITY_HIGH,
    SPS_REWARD_PER_WIN,
    SPS_REFERENCE_PRICE_USD,
    REALIZATION_HAIRCUT_BPS,
    CARD_RENTAL_COST_DAY_USD,
    TRANSACTION_COST_DAY_USD,
)


class SplinterlandsModernRankedAdapter:
    def __init__(self, strategy: SplinterlandsModernRankedStrategyDefinition) -> None:
        self.strategy = strategy

    def build_engine_input(
        self,
        observations: tuple[Observation, ...],
        *,
        calculated_at: datetime | None = None,
    ) -> SplinterlandsAdapterResult:
        active_time = _utc_now() if calculated_at is None else _normalize_utc(calculated_at)
        by_metric = _index_required_observations(observations, active_time)

        spellbook_cost_usd = _value(by_metric[SPELLBOOK_COST_USD])
        season_end_unix = _value(by_metric[SEASON_END_UNIX])
        energy_max = _value(by_metric[ENERGY_MAX])
        energy_regen_per_hour = _value(by_metric[ENERGY_REGEN_PER_HOUR])
        battles_per_day = _value(by_metric[BATTLES_PER_DAY])
        win_probability = _value(by_metric[WIN_PROBABILITY])
        win_probability_low = _value(by_metric[WIN_PROBABILITY_LOW])
        win_probability_high = _value(by_metric[WIN_PROBABILITY_HIGH])
        sps_reward_per_win = _value(by_metric[SPS_REWARD_PER_WIN])
        sps_reference_price_usd = _value(by_metric[SPS_REFERENCE_PRICE_USD])
        realization_haircut_bps = _value(by_metric[REALIZATION_HAIRCUT_BPS])
        card_rental_cost_day_usd = _value(by_metric[CARD_RENTAL_COST_DAY_USD])
        transaction_cost_day_usd = _value(by_metric[TRANSACTION_COST_DAY_USD])

        _require_positive(spellbook_cost_usd, SPELLBOOK_COST_USD)
        _require_positive(energy_max, ENERGY_MAX)
        _require_positive(energy_regen_per_hour, ENERGY_REGEN_PER_HOUR)
        _require_positive(battles_per_day, BATTLES_PER_DAY)
        _require_probability(win_probability, WIN_PROBABILITY)
        _require_probability(win_probability_low, WIN_PROBABILITY_LOW)
        _require_probability(win_probability_high, WIN_PROBABILITY_HIGH)
        if not win_probability_low <= win_probability <= win_probability_high:
            raise AdapterInputError("Win probability must be inside the configured low/high range")
        _require_positive(sps_reward_per_win, SPS_REWARD_PER_WIN)
        _require_positive(sps_reference_price_usd, SPS_REFERENCE_PRICE_USD)
        _require_bps(realization_haircut_bps, REALIZATION_HAIRCUT_BPS)
        _require_non_negative(card_rental_cost_day_usd, CARD_RENTAL_COST_DAY_USD)
        _require_non_negative(transaction_cost_day_usd, TRANSACTION_COST_DAY_USD)
        _require_active_season(season_end_unix, active_time)

        sustainable_energy_day = FINANCIAL_DECIMAL_CONTEXT.multiply(energy_regen_per_hour, decimal_from_int(24))
        if battles_per_day > sustainable_energy_day:
            raise AdapterInputError(
                f"{BATTLES_PER_DAY} exceeds sustainable daily regenerated energy from Splinterlands settings"
            )
        if battles_per_day > energy_max:
            raise AdapterInputError(f"{BATTLES_PER_DAY} exceeds max energy from Splinterlands settings")

        expected = calculate_modern_ranked_expected_values(
            battles_per_day=battles_per_day,
            win_probability=win_probability,
            win_probability_low=win_probability_low,
            win_probability_high=win_probability_high,
            sps_reward_per_win=sps_reward_per_win,
            sps_reference_price_usd=sps_reference_price_usd,
            realization_haircut_bps=realization_haircut_bps,
            card_rental_cost_day_usd=card_rental_cost_day_usd,
            transaction_cost_day_usd=transaction_cost_day_usd,
        )

        economics_input = StrategyEconomicsInput(
            strategy_id=self.strategy.strategy_id,
            strategy_version=self.strategy.strategy_version,
            model_version=MODEL_VERSION,
            reporting_currency=self.strategy.reporting_currency,
            capital=CapitalInput(
                sunk_cost=Money(spellbook_cost_usd, self.strategy.reporting_currency),
                recoverable_entry_cost=Money.zero(self.strategy.reporting_currency),
                current_recoverable_value=Money.zero(self.strategy.reporting_currency),
                initial_operating_reserve=Money.zero(self.strategy.reporting_currency),
                capital_at_risk=Money(spellbook_cost_usd, self.strategy.reporting_currency),
            ),
            rewards=RewardInput(
                gross_nominal_value_day=Money(expected.gross_nominal_value_day_usd, self.strategy.reporting_currency),
                realizable_value_day=Money(expected.realizable_value_day_usd, self.strategy.reporting_currency),
            ),
            costs=CostInput(
                operating_cost_day=Money(card_rental_cost_day_usd, self.strategy.reporting_currency),
                transaction_cost_day=Money(transaction_cost_day_usd, self.strategy.reporting_currency),
                other_cost_day=Money.zero(self.strategy.reporting_currency),
            ),
            cumulative_net_cash_earnings=Money.zero(self.strategy.reporting_currency),
            total_cash_invested_to_date=Money(spellbook_cost_usd, self.strategy.reporting_currency),
            break_even_basis=BreakEvenBasis(self.strategy.break_even_basis),
            input_observation_ids=tuple(by_metric[metric].observation_id for metric in REQUIRED_METRICS),
            assumptions=MappingProxyType(
                {
                    "battle_format": self.strategy.battle_format,
                    "expected_value_only": "Expected SPS rewards are not guaranteed outcomes.",
                    "probability_basis": "configured player-performance win-rate range",
                    "reward_per_win_basis": "configured representative SPS reward from observed ranked win evidence",
                    "reward_asset": self.strategy.reward_token_symbol,
                    "exit_route_basis": "SPS market price with configured realization haircut",
                    "sustainable_energy_day": str(sustainable_energy_day),
                }
            ),
        )

        return SplinterlandsAdapterResult(
            economics_input=economics_input,
            classifications=MappingProxyType(
                {metric: _classification(by_metric[metric]) for metric in REQUIRED_METRICS}
                | {
                    "splinterlands.modern_ranked.expected_wins_day": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.expected_wins_day_low": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.expected_wins_day_high": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.expected_sps_day": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.expected_sps_day_low": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.expected_sps_day_high": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.gross_nominal_value_day_usd": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.realizable_value_day_usd": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.realizable_value_day_usd_low": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.realizable_value_day_usd_high": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.net_earnings_day_usd_low": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.net_earnings_day_usd_high": ValueClassification.DERIVED,
                    "splinterlands.modern_ranked.sustainable_energy_day": ValueClassification.DERIVED,
                }
            ),
            derived_values=MappingProxyType(
                {
                    "splinterlands.modern_ranked.expected_wins_day": expected.expected_wins_day,
                    "splinterlands.modern_ranked.expected_wins_day_low": expected.expected_wins_day_low,
                    "splinterlands.modern_ranked.expected_wins_day_high": expected.expected_wins_day_high,
                    "splinterlands.modern_ranked.expected_sps_day": expected.expected_sps_day,
                    "splinterlands.modern_ranked.expected_sps_day_low": expected.expected_sps_day_low,
                    "splinterlands.modern_ranked.expected_sps_day_high": expected.expected_sps_day_high,
                    "splinterlands.modern_ranked.gross_nominal_value_day_usd": expected.gross_nominal_value_day_usd,
                    "splinterlands.modern_ranked.realizable_value_day_usd": expected.realizable_value_day_usd,
                    "splinterlands.modern_ranked.realizable_value_day_usd_low": expected.realizable_value_day_usd_low,
                    "splinterlands.modern_ranked.realizable_value_day_usd_high": expected.realizable_value_day_usd_high,
                    "splinterlands.modern_ranked.net_earnings_day_usd_low": expected.net_earnings_day_usd_low,
                    "splinterlands.modern_ranked.net_earnings_day_usd_high": expected.net_earnings_day_usd_high,
                    "splinterlands.modern_ranked.sustainable_energy_day": sustainable_energy_day,
                }
            ),
        )


@dataclass(frozen=True)
class SplinterlandsExpectedValues:
    expected_wins_day: Decimal
    expected_wins_day_low: Decimal
    expected_wins_day_high: Decimal
    expected_sps_day: Decimal
    expected_sps_day_low: Decimal
    expected_sps_day_high: Decimal
    gross_nominal_value_day_usd: Decimal
    realizable_value_day_usd: Decimal
    realizable_value_day_usd_low: Decimal
    realizable_value_day_usd_high: Decimal
    net_earnings_day_usd_low: Decimal
    net_earnings_day_usd_high: Decimal


def calculate_modern_ranked_expected_values(
    *,
    battles_per_day: Decimal,
    win_probability: Decimal,
    win_probability_low: Decimal,
    win_probability_high: Decimal,
    sps_reward_per_win: Decimal,
    sps_reference_price_usd: Decimal,
    realization_haircut_bps: Decimal,
    card_rental_cost_day_usd: Decimal,
    transaction_cost_day_usd: Decimal,
) -> SplinterlandsExpectedValues:
    expected_wins_day = FINANCIAL_DECIMAL_CONTEXT.multiply(battles_per_day, win_probability)
    expected_wins_day_low = FINANCIAL_DECIMAL_CONTEXT.multiply(battles_per_day, win_probability_low)
    expected_wins_day_high = FINANCIAL_DECIMAL_CONTEXT.multiply(battles_per_day, win_probability_high)
    expected_sps_day = FINANCIAL_DECIMAL_CONTEXT.multiply(expected_wins_day, sps_reward_per_win)
    expected_sps_day_low = FINANCIAL_DECIMAL_CONTEXT.multiply(expected_wins_day_low, sps_reward_per_win)
    expected_sps_day_high = FINANCIAL_DECIMAL_CONTEXT.multiply(expected_wins_day_high, sps_reward_per_win)
    gross_nominal_value_day_usd = FINANCIAL_DECIMAL_CONTEXT.multiply(expected_sps_day, sps_reference_price_usd)
    realization_multiplier = FINANCIAL_DECIMAL_CONTEXT.subtract(
        Decimal("1"),
        FINANCIAL_DECIMAL_CONTEXT.divide(realization_haircut_bps, decimal_from_int(10_000)),
    )
    realizable_value_day_usd = _realizable(expected_sps_day, sps_reference_price_usd, realization_multiplier)
    realizable_value_day_usd_low = _realizable(expected_sps_day_low, sps_reference_price_usd, realization_multiplier)
    realizable_value_day_usd_high = _realizable(expected_sps_day_high, sps_reference_price_usd, realization_multiplier)
    daily_cost = FINANCIAL_DECIMAL_CONTEXT.add(card_rental_cost_day_usd, transaction_cost_day_usd)

    return SplinterlandsExpectedValues(
        expected_wins_day=expected_wins_day,
        expected_wins_day_low=expected_wins_day_low,
        expected_wins_day_high=expected_wins_day_high,
        expected_sps_day=expected_sps_day,
        expected_sps_day_low=expected_sps_day_low,
        expected_sps_day_high=expected_sps_day_high,
        gross_nominal_value_day_usd=gross_nominal_value_day_usd,
        realizable_value_day_usd=realizable_value_day_usd,
        realizable_value_day_usd_low=realizable_value_day_usd_low,
        realizable_value_day_usd_high=realizable_value_day_usd_high,
        net_earnings_day_usd_low=FINANCIAL_DECIMAL_CONTEXT.subtract(realizable_value_day_usd_low, daily_cost),
        net_earnings_day_usd_high=FINANCIAL_DECIMAL_CONTEXT.subtract(realizable_value_day_usd_high, daily_cost),
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


def live_observation(
    *,
    provider: str,
    entity_type: str,
    entity_id: str,
    metric: str,
    value: Decimal,
    unit: str,
    source_locator: str,
    source_type: SourceType,
    retrieved_at: datetime | None = None,
    observed_at: datetime | None = None,
    freshness: timedelta = timedelta(minutes=5),
    metadata: dict[str, Any] | None = None,
) -> Observation:
    active_time = _utc_now() if retrieved_at is None else _normalize_utc(retrieved_at)
    observed_time = active_time if observed_at is None else _normalize_utc(observed_at)
    return Observation(
        observation_id=_observation_id(provider, entity_id, metric, observed_time),
        entity_type=entity_type,
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency="USD" if unit.upper() == "USD" else None,
        source_provider=provider,
        source_type=source_type,
        source_locator=source_locator,
        observed_at=observed_time,
        retrieved_at=active_time,
        fresh_until=active_time + freshness,
        status=ObservationStatus.FRESH,
        metadata={"classification": ValueClassification.LIVE.value, **(metadata or {})},
    )


def _realizable(expected_sps: Decimal, price_usd: Decimal, multiplier: Decimal) -> Decimal:
    return FINANCIAL_DECIMAL_CONTEXT.multiply(
        FINANCIAL_DECIMAL_CONTEXT.multiply(expected_sps, price_usd),
        multiplier,
    )


def _index_required_observations(observations: tuple[Observation, ...], active_time: datetime) -> dict[str, Observation]:
    by_metric = {observation.metric: observation for observation in observations}
    missing = [metric for metric in REQUIRED_METRICS if metric not in by_metric]
    if missing:
        raise AdapterInputError(f"Missing required Splinterlands observations: {', '.join(missing)}")
    for metric in REQUIRED_METRICS:
        observation = by_metric[metric]
        if observation.status_at(active_time) != ObservationStatus.FRESH:
            raise AdapterInputError(f"Required Splinterlands observation is not fresh: {metric}")
        if observation.value is None:
            raise AdapterInputError(f"Required Splinterlands observation has no value: {metric}")
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


def _require_active_season(season_end_unix: Decimal, active_time: datetime) -> None:
    if season_end_unix <= decimal_from_int(_unix_seconds(active_time)):
        raise AdapterInputError("Splinterlands season end is not in the future for the calculation timestamp")


def _require_probability(value: Decimal, field_name: str) -> None:
    if value < Decimal("0") or value > Decimal("1"):
        raise AdapterInputError(f"{field_name} must be between 0 and 1")


def _require_positive(value: Decimal, field_name: str) -> None:
    if value <= Decimal("0"):
        raise AdapterInputError(f"{field_name} must be positive")


def _require_non_negative(value: Decimal, field_name: str) -> None:
    if value < Decimal("0"):
        raise AdapterInputError(f"{field_name} must be non-negative")


def _require_bps(value: Decimal, field_name: str) -> None:
    if value < Decimal("0") or value > decimal_from_int(10_000):
        raise AdapterInputError(f"{field_name} must be between 0 and 10000")


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdapterInputError("Adapter timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _unix_seconds(value: datetime) -> int:
    return int(value.timestamp())


def _observation_id(provider: str, entity_id: str, metric: str, observed_at: datetime) -> str:
    key = f"{provider}|{entity_id}|{metric}|{observed_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
