"""Versioned DeFi Kingdoms strategy definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class DfkJewelerStrategyDefinition:
    strategy_id: str
    strategy_version: str
    game_id: str
    name: str
    chain_id: int
    reward_token_id: str
    report_token_id: str
    c_jewel_contract: str
    jewel_usdc_pair: str
    wjewel_contract: str
    usdc_contract: str
    lock_days: int
    max_lock_days: int
    locked_jewel_amount: str
    claim_interval_days: int
    claim_reward_gas_units: int
    emergency_withdrawal_penalty_bps: int
    dex_fee_bps: int
    break_even_basis: str


DFK_CJEWEL_MAX_LOCK_V1 = DfkJewelerStrategyDefinition(
    strategy_id="dfk-crystalvale-jeweler-cjewel-max-lock",
    strategy_version="v1",
    game_id="defi-kingdoms",
    name="DeFi Kingdoms Crystalvale Jeweler cJEWEL Max Lock",
    chain_id=53935,
    reward_token_id="dfk-chain:native:JEWEL",
    report_token_id="dfk-chain:synapse:USDC",
    c_jewel_contract="0x9ed2c155632C042CB8bC20634571fF1CA26f5742",
    jewel_usdc_pair="0xCF329b34049033dE26e4449aeBCb41f1992724D3",
    wjewel_contract="0xCCb93dABD71c8Dad03Fc4CE5559dC3D89F67a260",
    usdc_contract="0x3AD9DFE640E1A9Cc1D9B0948620820D975c3803a",
    lock_days=1095,
    max_lock_days=1095,
    locked_jewel_amount="1000",
    claim_interval_days=1,
    claim_reward_gas_units=180_000,
    emergency_withdrawal_penalty_bps=5_000,
    dex_fee_bps=30,
    break_even_basis="total_capital",
)


DFK_CJEWEL_100_MAX_LOCK_V1 = replace(
    DFK_CJEWEL_MAX_LOCK_V1,
    strategy_id="dfk-crystalvale-jeweler-cjewel-100-max-lock",
    name="DeFi Kingdoms Crystalvale Jeweler 100 JEWEL Max Lock",
    locked_jewel_amount="100",
)


DFK_CJEWEL_5000_MAX_LOCK_V1 = replace(
    DFK_CJEWEL_MAX_LOCK_V1,
    strategy_id="dfk-crystalvale-jeweler-cjewel-5000-max-lock",
    name="DeFi Kingdoms Crystalvale Jeweler 5000 JEWEL Max Lock",
    locked_jewel_amount="5000",
)


DFK_JEWELER_STRATEGIES: tuple[DfkJewelerStrategyDefinition, ...] = (
    DFK_CJEWEL_MAX_LOCK_V1,
    DFK_CJEWEL_100_MAX_LOCK_V1,
    DFK_CJEWEL_5000_MAX_LOCK_V1,
)
