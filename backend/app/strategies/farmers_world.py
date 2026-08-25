"""Versioned Farmers World strategy definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FarmersWorldAxeStrategyDefinition:
    strategy_id: str
    strategy_version: str
    game_id: str
    name: str
    chain: str
    reporting_currency: str
    tool_collection_name: str
    tool_schema_name: str
    tool_template_id: str
    tool_name: str
    reward_token_id: str
    reward_token_symbol: str
    food_token_id: str
    food_token_symbol: str
    repair_token_id: str
    repair_token_symbol: str
    market_quote_token_id: str
    market_quote_token_symbol: str
    fww_wax_ticker_id: str
    fwf_wax_ticker_id: str
    fwg_wax_ticker_id: str
    wax_coingecko_asset_id: str
    tool_count: str
    cycles_per_day: str
    cycle_hours: str
    fww_output_per_cycle: str
    fwf_input_per_cycle: str
    fwg_input_per_cycle: str
    transaction_cost_wax_day: str
    break_even_basis: str


FARMERS_WORLD_AXE_WOOD_V1 = FarmersWorldAxeStrategyDefinition(
    strategy_id="farmers-world-axe-wood-production",
    strategy_version="v1",
    game_id="farmers-world",
    name="Farmers World Axe Wood Production",
    chain="wax",
    reporting_currency="USD",
    tool_collection_name="farmersworld",
    tool_schema_name="tools",
    tool_template_id="203881",
    tool_name="Axe",
    reward_token_id="wax:fww-farmerstoken",
    reward_token_symbol="FWW",
    food_token_id="wax:fwf-farmerstoken",
    food_token_symbol="FWF",
    repair_token_id="wax:fwg-farmerstoken",
    repair_token_symbol="FWG",
    market_quote_token_id="wax:wax-eosio.token",
    market_quote_token_symbol="WAX",
    fww_wax_ticker_id="fww-farmerstoken_wax-eosio.token",
    fwf_wax_ticker_id="fwf-farmerstoken_wax-eosio.token",
    fwg_wax_ticker_id="fwg-farmerstoken_wax-eosio.token",
    wax_coingecko_asset_id="wax",
    tool_count="1",
    cycles_per_day="12",
    cycle_hours="1",
    fww_output_per_cycle="5",
    fwf_input_per_cycle="2",
    fwg_input_per_cycle="1",
    transaction_cost_wax_day="0",
    break_even_basis="total_capital",
)


FARMERS_WORLD_AXE_WOOD_3X_V1 = replace(
    FARMERS_WORLD_AXE_WOOD_V1,
    strategy_id="farmers-world-axe-wood-production-3x",
    name="Farmers World Axe Wood Production 3 Axes",
    tool_count="3",
)


FARMERS_WORLD_AXE_WOOD_10X_V1 = replace(
    FARMERS_WORLD_AXE_WOOD_V1,
    strategy_id="farmers-world-axe-wood-production-10x",
    name="Farmers World Axe Wood Production 10 Axes",
    tool_count="10",
)


FARMERS_WORLD_AXE_STRATEGIES: tuple[FarmersWorldAxeStrategyDefinition, ...] = (
    FARMERS_WORLD_AXE_WOOD_V1,
    FARMERS_WORLD_AXE_WOOD_3X_V1,
    FARMERS_WORLD_AXE_WOOD_10X_V1,
)
