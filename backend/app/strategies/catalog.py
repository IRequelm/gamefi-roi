"""Static catalog for modeled games and versioned strategies."""

from __future__ import annotations

from dataclasses import dataclass

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1


@dataclass(frozen=True)
class GameCatalogEntry:
    game_id: str
    name: str
    chains: tuple[str, ...]
    economy_types: tuple[str, ...]
    status: str
    strategy_ids: tuple[str, ...]


@dataclass(frozen=True)
class StrategyCatalogEntry:
    strategy_id: str
    strategy_version: str
    game_id: str
    game_name: str
    name: str
    chain: str
    economy_type: str
    description: str


DFK_STRATEGY_CATALOG = StrategyCatalogEntry(
    strategy_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
    strategy_version=DFK_CJEWEL_MAX_LOCK_V1.strategy_version,
    game_id=DFK_CJEWEL_MAX_LOCK_V1.game_id,
    game_name="DeFi Kingdoms",
    name=DFK_CJEWEL_MAX_LOCK_V1.name,
    chain="dfk-chain",
    economy_type="locked-yield-reward",
    description="cJEWEL max-lock strategy with claimable JEWEL rewards and emergency-exit valuation.",
)

FARMERS_WORLD_STRATEGY_CATALOG = StrategyCatalogEntry(
    strategy_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
    strategy_version=FARMERS_WORLD_AXE_WOOD_V1.strategy_version,
    game_id=FARMERS_WORLD_AXE_WOOD_V1.game_id,
    game_name="Farmers World",
    name=FARMERS_WORLD_AXE_WOOD_V1.name,
    chain=FARMERS_WORLD_AXE_WOOD_V1.chain,
    economy_type="resource-production",
    description="Axe wood production strategy with resource input costs and player-market exit value.",
)

SPLINTERLANDS_STRATEGY_CATALOG = StrategyCatalogEntry(
    strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
    strategy_version=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_version,
    game_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.game_id,
    game_name="Splinterlands",
    name=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.name,
    chain=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.chain,
    economy_type="probabilistic-performance",
    description="Modern Ranked SPS expected-value strategy with explicit win-rate uncertainty.",
)

STRATEGIES = (
    DFK_STRATEGY_CATALOG,
    FARMERS_WORLD_STRATEGY_CATALOG,
    SPLINTERLANDS_STRATEGY_CATALOG,
)

GAMES = (
    GameCatalogEntry(
        game_id="defi-kingdoms",
        name="DeFi Kingdoms",
        chains=("dfk-chain",),
        economy_types=("locked-yield-reward",),
        status="active",
        strategy_ids=(DFK_CJEWEL_MAX_LOCK_V1.strategy_id,),
    ),
    GameCatalogEntry(
        game_id="farmers-world",
        name="Farmers World",
        chains=("wax",),
        economy_types=("resource-production",),
        status="active",
        strategy_ids=(FARMERS_WORLD_AXE_WOOD_V1.strategy_id,),
    ),
    GameCatalogEntry(
        game_id="splinterlands",
        name="Splinterlands",
        chains=("hive",),
        economy_types=("probabilistic-performance",),
        status="active",
        strategy_ids=(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,),
    ),
)


def list_games() -> tuple[GameCatalogEntry, ...]:
    return tuple(sorted(GAMES, key=lambda game: game.game_id))


def get_game(game_id: str) -> GameCatalogEntry | None:
    return next((game for game in GAMES if game.game_id == game_id), None)


def list_strategies() -> tuple[StrategyCatalogEntry, ...]:
    return tuple(sorted(STRATEGIES, key=lambda strategy: strategy.strategy_id))


def get_strategy(strategy_id: str) -> StrategyCatalogEntry | None:
    return next((strategy for strategy in STRATEGIES if strategy.strategy_id == strategy_id), None)
