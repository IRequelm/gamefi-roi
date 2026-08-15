"""Versioned Splinterlands strategy definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SplinterlandsModernRankedStrategyDefinition:
    strategy_id: str
    strategy_version: str
    game_id: str
    name: str
    chain: str
    reporting_currency: str
    battle_format: str
    reward_token_id: str
    reward_token_symbol: str
    reward_coingecko_asset_id: str
    battles_per_day: str
    win_probability: str
    win_probability_low: str
    win_probability_high: str
    expected_sps_reward_per_win: str
    card_rental_cost_day_usd: str
    transaction_cost_day_usd: str
    realization_haircut_bps: str
    break_even_basis: str


SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1 = SplinterlandsModernRankedStrategyDefinition(
    strategy_id="splinterlands-modern-ranked-sps-ev",
    strategy_version="v1",
    game_id="splinterlands",
    name="Splinterlands Modern Ranked SPS Expected Value",
    chain="hive",
    reporting_currency="USD",
    battle_format="modern",
    reward_token_id="splinterlands:sps",
    reward_token_symbol="SPS",
    reward_coingecko_asset_id="splinterlands",
    battles_per_day="20",
    win_probability="0.55",
    win_probability_low="0.45",
    win_probability_high="0.65",
    expected_sps_reward_per_win="0.25",
    card_rental_cost_day_usd="0.01",
    transaction_cost_day_usd="0",
    realization_haircut_bps="100",
    break_even_basis="total_capital",
)
