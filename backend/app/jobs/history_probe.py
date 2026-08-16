"""Local deterministic probe for the G8 history pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.adapters.contract import derived_observation, live_observation, unix_seconds, verified_config_observation
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
    DfkJewelerAdapter,
)
from app.adapters.farmers_world import (
    CYCLE_HOURS,
    CYCLES_PER_DAY,
    ENTRY_VALUE_USD as FARMERS_ENTRY_VALUE_USD,
    EXIT_VALUE_USD as FARMERS_EXIT_VALUE_USD,
    FWF_INPUT_PER_CYCLE,
    FWF_OPERATING_COST_DAY_USD,
    FWG_INPUT_PER_CYCLE,
    FWG_OPERATING_COST_DAY_USD,
    FWW_OUTPUT_PER_CYCLE,
    FWW_REALIZABLE_VALUE_DAY_USD,
    FWW_REFERENCE_PRICE_USD,
    TOOL_COUNT,
    TRANSACTION_COST_DAY_USD as FARMERS_TRANSACTION_COST_DAY_USD,
    FarmersWorldAxeAdapter,
)
from app.adapters.splinterlands import (
    BATTLES_PER_DAY,
    CARD_RENTAL_COST_DAY_USD,
    ENERGY_MAX,
    ENERGY_REGEN_PER_HOUR,
    REALIZATION_HAIRCUT_BPS,
    SEASON_END_UNIX,
    SEASON_ID,
    SPELLBOOK_COST_USD,
    SPS_REFERENCE_PRICE_USD,
    SPS_REWARD_PER_WIN,
    TRANSACTION_COST_DAY_USD as SPLINTERLANDS_TRANSACTION_COST_DAY_USD,
    WIN_PROBABILITY,
    WIN_PROBABILITY_HIGH,
    WIN_PROBABILITY_LOW,
    SplinterlandsModernRankedAdapter,
)
from app.jobs.recalculation import ScheduledRecalculator, StrategyCalculationTask, hourly_window
from app.sources.observations import Observation, SourceType
from app.storage.database import create_database_engine
from app.storage.history import HistoryRepository
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1


def build_history_probe_tasks() -> tuple[StrategyCalculationTask, ...]:
    return (
        StrategyCalculationTask(
            strategy_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
            strategy_version=DFK_CJEWEL_MAX_LOCK_V1.strategy_version,
            adapter=DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1),
            load_observations=_dfk_observations,
        ),
        StrategyCalculationTask(
            strategy_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
            strategy_version=FARMERS_WORLD_AXE_WOOD_V1.strategy_version,
            adapter=FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1),
            load_observations=_farmers_world_observations,
        ),
        StrategyCalculationTask(
            strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
            strategy_version=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_version,
            adapter=SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1),
            load_observations=_splinterlands_observations,
        ),
    )


def main() -> int:
    engine = create_database_engine()
    try:
        repository = HistoryRepository(engine)
        calculated_at = datetime.now(UTC)
        result = ScheduledRecalculator(repository).run_once(
            build_history_probe_tasks(),
            intended_window=hourly_window(calculated_at),
            calculated_at=calculated_at,
        )
    finally:
        engine.dispose()

    print(
        "history probe "
        f"calculated_at={result.calculated_at.isoformat()} "
        f"snapshots={len(result.snapshots)} "
        f"failures={len(result.failures)}"
    )
    for snapshot in result.snapshots:
        print(f"[SNAPSHOT] {snapshot.strategy_id}@{snapshot.strategy_version} {snapshot.snapshot_id}")
    for failure in result.failures:
        print(f"[FAILURE] {failure.strategy_id}@{failure.strategy_version} {failure.error_type}: {failure.error_message}")
    return 0 if not result.failures else 1


def _dfk_observations(active_time: datetime) -> tuple[Observation, ...]:
    strategy_id = DFK_CJEWEL_MAX_LOCK_V1.strategy_id
    configs = (
        _config(strategy_id, LOCKED_JEWEL_AMOUNT, DFK_CJEWEL_MAX_LOCK_V1.locked_jewel_amount, "JEWEL", active_time),
        _config(strategy_id, LOCK_DAYS, str(DFK_CJEWEL_MAX_LOCK_V1.lock_days), "day", active_time),
        _config(strategy_id, MAX_LOCK_DAYS, str(DFK_CJEWEL_MAX_LOCK_V1.max_lock_days), "day", active_time),
    )
    live = (
        _live(YESTERDAY_CJEWEL_BALANCE, "250000", "cJEWEL", active_time, SourceType.ONCHAIN, "dfk-chain"),
        _live(YESTERDAY_REWARD_JEWEL, "500", "JEWEL", active_time, SourceType.ONCHAIN, "dfk-chain"),
    )
    derived = (
        _derived(strategy_id, ENTRY_VALUE_USD, "250.00", active_time, source_locator="amm:dfk-wjewel-usdc:spot"),
        _derived(
            strategy_id,
            EMERGENCY_EXIT_VALUE_USD,
            "125.00",
            active_time,
            source_locator="amm:dfk-wjewel-usdc:quote_exact_input",
        ),
        _derived(
            strategy_id,
            JEWEL_REFERENCE_PRICE_USD,
            "0.25",
            active_time,
            source_locator="amm:dfk-wjewel-usdc:spot",
        ),
        _derived(
            strategy_id,
            REWARD_REALIZABLE_VALUE_USD,
            "0.4985",
            active_time,
            source_locator="amm:dfk-wjewel-usdc:quote_exact_input",
        ),
        _derived(
            strategy_id,
            CLAIM_TRANSACTION_COST_USD,
            "0.01",
            active_time,
            source_locator="dfk-chain-rpc:eth_gasPrice + configured gas units",
        ),
    )
    return (*configs, *live, *derived)


def _farmers_world_observations(active_time: datetime) -> tuple[Observation, ...]:
    strategy_id = FARMERS_WORLD_AXE_WOOD_V1.strategy_id
    configs = (
        _config(strategy_id, TOOL_COUNT, FARMERS_WORLD_AXE_WOOD_V1.tool_count, "tool", active_time),
        _config(strategy_id, CYCLES_PER_DAY, FARMERS_WORLD_AXE_WOOD_V1.cycles_per_day, "cycle/day", active_time),
        _config(strategy_id, CYCLE_HOURS, FARMERS_WORLD_AXE_WOOD_V1.cycle_hours, "hour", active_time),
        _config(strategy_id, FWW_OUTPUT_PER_CYCLE, FARMERS_WORLD_AXE_WOOD_V1.fww_output_per_cycle, "FWW", active_time),
        _config(strategy_id, FWF_INPUT_PER_CYCLE, FARMERS_WORLD_AXE_WOOD_V1.fwf_input_per_cycle, "FWF", active_time),
        _config(strategy_id, FWG_INPUT_PER_CYCLE, FARMERS_WORLD_AXE_WOOD_V1.fwg_input_per_cycle, "FWG", active_time),
    )
    derived = (
        _derived(strategy_id, FARMERS_ENTRY_VALUE_USD, "1.80", active_time, source_locator="atomicassets floor * WAX/USD"),
        _derived(
            strategy_id,
            FARMERS_EXIT_VALUE_USD,
            "1.70",
            active_time,
            source_locator="AtomicAssets floor net marketplace fee * WAX/USD",
        ),
        _derived(
            strategy_id,
            FWW_REFERENCE_PRICE_USD,
            "0.001",
            active_time,
            source_locator="Alcor FWW/WAX spot * WAX/USD",
        ),
        _derived(
            strategy_id,
            FWW_REALIZABLE_VALUE_DAY_USD,
            "0.0594",
            active_time,
            source_locator="Alcor FWW/WAX quote_exact_input * WAX/USD",
        ),
        _derived(
            strategy_id,
            FWF_OPERATING_COST_DAY_USD,
            "0.006",
            active_time,
            source_locator="Alcor FWF/WAX quote_exact_output * WAX/USD",
        ),
        _derived(
            strategy_id,
            FWG_OPERATING_COST_DAY_USD,
            "0.003",
            active_time,
            source_locator="Alcor FWG/WAX quote_exact_output * WAX/USD",
        ),
        _derived(
            strategy_id,
            FARMERS_TRANSACTION_COST_DAY_USD,
            "0",
            active_time,
            source_locator="configured WAX transaction/resource assumption * WAX/USD",
        ),
    )
    return (*configs, *derived)


def _splinterlands_observations(active_time: datetime) -> tuple[Observation, ...]:
    strategy_id = SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id
    season_end = active_time + timedelta(days=14)
    live = (
        _live(SPELLBOOK_COST_USD, "10.00", "USD", active_time, SourceType.OFFICIAL_API, "splinterlands"),
        _live(SEASON_ID, "189", "season", active_time, SourceType.OFFICIAL_API, "splinterlands:season:189"),
        _live(
            SEASON_END_UNIX,
            str(unix_seconds(season_end)),
            "unix_second",
            active_time,
            SourceType.OFFICIAL_API,
            "splinterlands:season:189",
        ),
        _live(ENERGY_MAX, "50", "energy", active_time, SourceType.OFFICIAL_API, "splinterlands"),
        _live(ENERGY_REGEN_PER_HOUR, "1", "energy/hour", active_time, SourceType.OFFICIAL_API, "splinterlands"),
        _live(SPS_REFERENCE_PRICE_USD, "0.01", "USD", active_time, SourceType.MARKET_API, "splinterlands:sps"),
    )
    configs = (
        _config(strategy_id, BATTLES_PER_DAY, SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.battles_per_day, "battle/day", active_time),
        _config(strategy_id, WIN_PROBABILITY, SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.win_probability, "probability", active_time),
        _config(
            strategy_id,
            WIN_PROBABILITY_LOW,
            SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.win_probability_low,
            "probability",
            active_time,
        ),
        _config(
            strategy_id,
            WIN_PROBABILITY_HIGH,
            SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.win_probability_high,
            "probability",
            active_time,
        ),
        _config(
            strategy_id,
            SPS_REWARD_PER_WIN,
            SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.expected_sps_reward_per_win,
            "SPS",
            active_time,
        ),
        _config(
            strategy_id,
            REALIZATION_HAIRCUT_BPS,
            SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.realization_haircut_bps,
            "basis_point",
            active_time,
        ),
        _config(
            strategy_id,
            CARD_RENTAL_COST_DAY_USD,
            SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.card_rental_cost_day_usd,
            "USD",
            active_time,
        ),
        _config(
            strategy_id,
            SPLINTERLANDS_TRANSACTION_COST_DAY_USD,
            SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.transaction_cost_day_usd,
            "USD",
            active_time,
        ),
    )
    return (*live, *configs)


def _config(strategy_id: str, metric: str, value: str, unit: str, active_time: datetime) -> Observation:
    return verified_config_observation(
        strategy_id=strategy_id,
        metric=metric,
        value=value,
        unit=unit,
        source_locator="probe:history",
        retrieved_at=active_time,
    )


def _live(
    metric: str,
    value: str,
    unit: str,
    active_time: datetime,
    source_type: SourceType,
    entity_id: str,
) -> Observation:
    return live_observation(
        provider="probe",
        entity_type="strategy",
        entity_id=entity_id,
        metric=metric,
        value=Decimal(value),
        unit=unit,
        source_locator="probe:history",
        source_type=source_type,
        retrieved_at=active_time,
        observed_at=active_time,
        freshness=timedelta(minutes=5),
    )


def _derived(
    strategy_id: str,
    metric: str,
    value: str,
    active_time: datetime,
    *,
    source_locator: str,
) -> Observation:
    return derived_observation(
        provider="probe-derived",
        entity_type="strategy",
        entity_id=strategy_id,
        metric=metric,
        value=Decimal(value),
        unit="USD",
        source_locator=source_locator,
        input_observation_ids=("probe-input",),
        retrieved_at=active_time,
    )


if __name__ == "__main__":
    raise SystemExit(main())
