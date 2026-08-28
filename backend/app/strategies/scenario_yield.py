"""Versioned scenario-yield strategy definitions for post-V1 catalog expansion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ScenarioRewardKind = Literal["usd_day", "token_day"]


@dataclass(frozen=True)
class ScenarioSourceReference:
    label: str
    url: str


@dataclass(frozen=True)
class ScenarioSupportMetric:
    key: str
    value: str
    unit: str
    source_provider: str
    source_type: str
    source_locator: str
    note: str


@dataclass(frozen=True)
class ScenarioCapitalDefinition:
    sunk_cost_usd: str
    recoverable_entry_cost_usd: str
    current_recoverable_value_usd: str
    initial_operating_reserve_usd: str
    capital_at_risk_usd: str
    source_locator: str
    note: str


@dataclass(frozen=True)
class ScenarioRewardDefinition:
    kind: ScenarioRewardKind
    reward_asset_id: str
    reward_asset_symbol: str
    amount_day: str
    amount_unit: str
    cash_realization_ratio: str
    realization_haircut_bps: str
    source_locator: str
    note: str
    price_provider_asset_id: str | None = None
    fixture_reward_token_price_usd: str | None = None


@dataclass(frozen=True)
class ScenarioCostDefinition:
    operating_cost_day_usd: str
    transaction_cost_day_usd: str
    other_cost_day_usd: str
    source_locator: str
    note: str


@dataclass(frozen=True)
class ScenarioRangeDefinition:
    low_reward_amount_day: str
    high_reward_amount_day: str
    description: str


@dataclass(frozen=True)
class ScenarioWarningDefinition:
    code: str
    message: str
    severity: str = "warning"


@dataclass(frozen=True)
class ScenarioYieldStrategyDefinition:
    strategy_id: str
    strategy_version: str
    opportunity_id: str
    opportunity_type: str
    game_id_alias: str
    opportunity_name: str
    name: str
    chain: str
    economy_type: str
    description: str
    reporting_currency: str
    metric_prefix: str
    break_even_basis: str
    capital: ScenarioCapitalDefinition
    reward: ScenarioRewardDefinition
    costs: ScenarioCostDefinition
    assumptions: tuple[tuple[str, str], ...]
    support_metrics: tuple[ScenarioSupportMetric, ...]
    warnings: tuple[ScenarioWarningDefinition, ...]
    source_references: tuple[ScenarioSourceReference, ...]
    hardware_requirements: tuple[str, ...]
    geography_dependency: str
    platforms: tuple[str, ...]
    uncertainty: ScenarioRangeDefinition | None = None


def scenario_metric(strategy: ScenarioYieldStrategyDefinition, suffix: str) -> str:
    return f"{strategy.metric_prefix}.{suffix}"


STORJ_EXISTING_HARDWARE_V1 = ScenarioYieldStrategyDefinition(
    strategy_id="storj-existing-hardware-storage-node",
    strategy_version="v1",
    opportunity_id="storj-storage-node",
    opportunity_type="DEPIN_NODE",
    game_id_alias="storj-storage-node",
    opportunity_name="Storj Storage Node",
    name="Storj Storage Node With Existing Hardware",
    chain="ethereum",
    economy_type="storage-node",
    description=(
        "Existing always-on device scenario using official Storj payout rates, configured storage/egress "
        "utilization, early-node held-back cash realization, and incremental operating costs."
    ),
    reporting_currency="USD",
    metric_prefix="storj.storage_node.existing_hardware",
    break_even_basis="capital_at_risk",
    capital=ScenarioCapitalDefinition(
        sunk_cost_usd="0",
        recoverable_entry_cost_usd="0",
        current_recoverable_value_usd="0",
        initial_operating_reserve_usd="1.00",
        capital_at_risk_usd="1.00",
        source_locator="https://storj.dev/node/concepts",
        note="No Storj token stake is required; model uses an explicit incremental operating reserve.",
    ),
    reward=ScenarioRewardDefinition(
        kind="usd_day",
        reward_asset_id="storj:node:payout",
        reward_asset_symbol="STORJ payout value",
        amount_day="0.02833333333333333333333333333",
        amount_unit="USD/day",
        cash_realization_ratio="0.25",
        realization_haircut_bps="0",
        source_locator="https://storj.dev/node/payouts",
        note=(
            "Gross daily value = (0.50 TB-month * $1.50 + 0.05 TB egress * $2.00) / 30; "
            "cash realization applies the official 75% held-back period for months 1-3."
        ),
    ),
    costs=ScenarioCostDefinition(
        operating_cost_day_usd="0.018",
        transaction_cost_day_usd="0.001",
        other_cost_day_usd="0",
        source_locator="https://storj.dev/node/payouts",
        note="Power allocation uses 5 W at $0.15/kWh; payout fee is a configured amortized micro-reserve.",
    ),
    assumptions=(
        ("storage_tb_month", "0.50"),
        ("egress_tb_month", "0.05"),
        ("storage_payout_usd_per_tb_month", "1.50"),
        ("egress_payout_usd_per_tb", "2.00"),
        ("cash_realization_ratio", "0.25"),
        ("power_watts_allocated", "5"),
        ("electricity_cost_usd_per_kwh", "0.15"),
    ),
    support_metrics=(
        ScenarioSupportMetric(
            "minimum_shared_storage",
            "500",
            "GB",
            "storj-docs",
            "official_docs",
            "https://storj.dev/node/concepts",
            "Official minimum shared storage requirement.",
        ),
        ScenarioSupportMetric(
            "storage_payout_rate",
            "1.5",
            "USD/TB-month",
            "storj-docs",
            "official_docs",
            "https://storj.dev/node/payouts",
            "Official storage payout rate.",
        ),
        ScenarioSupportMetric(
            "egress_payout_rate",
            "2",
            "USD/TB",
            "storj-docs",
            "official_docs",
            "https://storj.dev/node/payouts",
            "Official egress payout rate.",
        ),
        ScenarioSupportMetric(
            "held_back_cash_ratio_months_1_3",
            "0.25",
            "ratio",
            "storj-docs",
            "official_docs",
            "https://storj.dev/node/faq/held-back-amount",
            "Official months 1-3 held-back schedule leaves 25% currently payable.",
        ),
    ),
    warnings=(
        ScenarioWarningDefinition(
            "demand_dependent_utilization",
            "Storage fill and egress are demand-driven; this is a configured scenario, not a universal node income.",
        ),
        ScenarioWarningDefinition(
            "held_back_payout",
            "Storj held-back amounts reduce early cash realization and depend on graceful-exit rules.",
        ),
        ScenarioWarningDefinition(
            "existing_hardware_only",
            "This strategy excludes new disk, NAS, server, and replacement-reserve capital.",
            "info",
        ),
    ),
    source_references=(
        ScenarioSourceReference("Node overview", "https://storj.dev/node"),
        ScenarioSourceReference("Payouts", "https://storj.dev/node/payouts"),
        ScenarioSourceReference("Held-back amount", "https://storj.dev/node/faq/held-back-amount"),
        ScenarioSourceReference("Node concepts", "https://storj.dev/node/concepts"),
    ),
    hardware_requirements=("Always-on device", "Unused disk", "Port forwarding", "Wallet"),
    geography_dependency="Storage and egress depend on network demand, uptime, and network placement.",
    platforms=("desktop", "server"),
    uncertainty=ScenarioRangeDefinition(
        low_reward_amount_day="0.01316666666666666666666666667",
        high_reward_amount_day="0.07266666666666666666666666667",
        description="Configured low/base/high storage and egress utilization range.",
    ),
)


GEODNET_EMPTY_HEX_TRIPLE_BAND_V1 = ScenarioYieldStrategyDefinition(
    strategy_id="geodnet-empty-hex-triple-band-base-station",
    strategy_version="v1",
    opportunity_id="geodnet",
    opportunity_type="DEPIN_NODE",
    game_id_alias="geodnet",
    opportunity_name="GEODNET",
    name="GEODNET Empty Hex Triple-Band Base Station",
    chain="polygon",
    economy_type="geospatial-node",
    description=(
        "Triple-band base-station scenario using official hardware price, documented 2025/2026 maximum "
        "daily GEOD reward, and explicit high-quality empty-hex assumptions."
    ),
    reporting_currency="USD",
    metric_prefix="geodnet.empty_hex.triple_band",
    break_even_basis="capital_at_risk",
    capital=ScenarioCapitalDefinition(
        sunk_cost_usd="695",
        recoverable_entry_cost_usd="0",
        current_recoverable_value_usd="0",
        initial_operating_reserve_usd="0",
        capital_at_risk_usd="695",
        source_locator="https://geodnet.com/store",
        note="MobileCM triple-band hardware is treated as sunk because no executable resale exit is modeled.",
    ),
    reward=ScenarioRewardDefinition(
        kind="token_day",
        reward_asset_id="polygon:geodnet:GEOD",
        reward_asset_symbol="GEOD",
        amount_day="12",
        amount_unit="GEOD/day",
        cash_realization_ratio="1",
        realization_haircut_bps="500",
        price_provider_asset_id="geodnet",
        fixture_reward_token_price_usd="0.25",
        source_locator="https://docs.geodnet.com/docs/geodnet-token-metrics",
        note="Official 2025/2026 maximum reward is 12 GEOD/day; 5% exit haircut reflects non-executable market valuation.",
    ),
    costs=ScenarioCostDefinition(
        operating_cost_day_usd="0.0072",
        transaction_cost_day_usd="0.02",
        other_cost_day_usd="0",
        source_locator="https://docs.geodnet.com/docs/geodnet-base-station-setup-guide",
        note="Power uses documented sub-2W hardware at $0.15/kWh; claim/transaction cost is an explicit estimate.",
    ),
    assumptions=(
        ("max_daily_geod", "12"),
        ("reward_quality_ratio", "1"),
        ("realization_haircut_bps", "500"),
        ("hardware_power_watts", "2"),
        ("electricity_cost_usd_per_kwh", "0.15"),
    ),
    support_metrics=(
        ScenarioSupportMetric(
            "mobilecm_price",
            "695",
            "USD",
            "geodnet-store",
            "official_docs",
            "https://geodnet.com/store",
            "Official MobileCM triple-band base-station listing.",
        ),
        ScenarioSupportMetric(
            "max_daily_reward_2025_2026",
            "12",
            "GEOD/day",
            "geodnet-docs",
            "official_docs",
            "https://docs.geodnet.com/docs/geodnet-token-metrics",
            "Official maximum daily reward for 2025/2026 before annual halving.",
        ),
        ScenarioSupportMetric(
            "minimum_effective_satellites_full_reward",
            "29",
            "satellites",
            "geodnet-docs",
            "official_docs",
            "https://docs.geodnet.com/docs/geodnet-quality-of-data-requirements",
            "Performance threshold for full reward under the documented rules.",
        ),
        ScenarioSupportMetric(
            "claim_threshold",
            "10",
            "GEOD",
            "geodnet-docs",
            "official_docs",
            "https://docs.geodnet.com/docs/geodnet-token-metrics",
            "Documented minimum threshold before distribution.",
        ),
    ),
    warnings=(
        ScenarioWarningDefinition(
            "maximum_reward_scenario",
            "This is a maximum-reward empty-hex scenario; occupied hexes, low satellites, or multipath issues can reduce rewards to zero.",
        ),
        ScenarioWarningDefinition(
            "geography_dependent",
            "GEODNET rewards depend on location, hex occupancy, device placement, and signal quality.",
        ),
        ScenarioWarningDefinition(
            "halving_schedule",
            "The documented reward schedule includes annual halving after June 30.",
        ),
        ScenarioWarningDefinition(
            "non_executable_exit",
            "Reward valuation uses a market price plus haircut, not an executable quote.",
        ),
    ),
    source_references=(
        ScenarioSourceReference("Official store", "https://geodnet.com/store"),
        ScenarioSourceReference("Token metrics", "https://docs.geodnet.com/docs/geodnet-token-metrics"),
        ScenarioSourceReference("Quality requirements", "https://docs.geodnet.com/docs/geodnet-quality-of-data-requirements"),
        ScenarioSourceReference("CoinGecko GEOD", "https://www.coingecko.com/en/coins/geodnet"),
    ),
    hardware_requirements=("Triple-band GNSS base station", "Clear sky placement", "Power", "Internet"),
    geography_dependency="Location, hex occupancy, satellites, and multipath directly affect reward eligibility.",
    platforms=("hardware-node",),
    uncertainty=ScenarioRangeDefinition(
        low_reward_amount_day="0",
        high_reward_amount_day="12",
        description="Zero-to-maximum reward range captures location and quality dependency.",
    ),
)


WEATHERXM_D1_WIFI_V1 = ScenarioYieldStrategyDefinition(
    strategy_id="weatherxm-d1-wifi-station",
    strategy_version="v1",
    opportunity_id="weatherxm",
    opportunity_type="DEPIN_NODE",
    game_id_alias="weatherxm",
    opportunity_name="WeatherXM",
    name="WeatherXM D1 WiFi Station",
    chain="arbitrum",
    economy_type="weather-station",
    description=(
        "D1 WiFi weather-station scenario using official hardware price, station reward allocation evidence, "
        "and an explicit network-average reward assumption until cell-level API observations are configured."
    ),
    reporting_currency="USD",
    metric_prefix="weatherxm.d1_wifi.station",
    break_even_basis="capital_at_risk",
    capital=ScenarioCapitalDefinition(
        sunk_cost_usd="139",
        recoverable_entry_cost_usd="0",
        current_recoverable_value_usd="0",
        initial_operating_reserve_usd="0",
        capital_at_risk_usd="139",
        source_locator="https://weatherxm.com/",
        note="D1 WiFi promo hardware price is treated as sunk because no executable resale exit is modeled.",
    ),
    reward=ScenarioRewardDefinition(
        kind="token_day",
        reward_asset_id="arbitrum:weatherxm:WXM",
        reward_asset_symbol="WXM",
        amount_day="1.8",
        amount_unit="WXM/day",
        cash_realization_ratio="1",
        realization_haircut_bps="1000",
        price_provider_asset_id="weatherxm",
        fixture_reward_token_price_usd="0.10",
        source_locator="https://docs.weatherxm.com/rewards/rewards-mechanism",
        note=(
            "Reward amount is a configured network-average proxy derived from the official station reward "
            "allocation and public station-count context; target-cell rewards require API data."
        ),
    ),
    costs=ScenarioCostDefinition(
        operating_cost_day_usd="0.005",
        transaction_cost_day_usd="0.01",
        other_cost_day_usd="0",
        source_locator="https://docs.weatherxm.com/rewards/claim-rewards",
        note="WiFi/power cost and Arbitrum claim cost are explicit configured assumptions.",
    ),
    assumptions=(
        ("station_reward_wxm_day", "1.8"),
        ("realization_haircut_bps", "1000"),
        ("hardware_price_usd", "139"),
        ("claim_chain", "arbitrum"),
    ),
    support_metrics=(
        ScenarioSupportMetric(
            "d1_wifi_station_price",
            "139",
            "USD",
            "weatherxm-site",
            "official_docs",
            "https://weatherxm.com/",
            "Official D1 WiFi promo hardware price observed in the handoff.",
        ),
        ScenarioSupportMetric(
            "station_reward_allocation",
            "55000000",
            "WXM",
            "weatherxm-docs",
            "official_docs",
            "https://docs.weatherxm.com/tokenomics/allocation",
            "Official WXM station reward allocation.",
        ),
        ScenarioSupportMetric(
            "public_station_count_context",
            "9500",
            "station",
            "weatherxm-site",
            "official_docs",
            "https://weatherxm.com/",
            "Public network station-count context from the official site.",
        ),
        ScenarioSupportMetric(
            "pro_api_rewards_available",
            "1",
            "boolean",
            "weatherxm-docs",
            "official_docs",
            "https://docs.weatherxm.com/pro-api",
            "Official API surface includes station rewards and cell data, but production access needs an API key.",
        ),
    ),
    warnings=(
        ScenarioWarningDefinition(
            "cell_level_rewards_required",
            "This uses a configured network-average reward proxy; station quality and cell-level rewards can differ materially.",
        ),
        ScenarioWarningDefinition(
            "api_key_required",
            "Live target-cell reward observations require WeatherXM Pro API configuration.",
            "info",
        ),
        ScenarioWarningDefinition(
            "non_executable_exit",
            "WXM valuation uses market price plus haircut, not an executable quote.",
        ),
    ),
    source_references=(
        ScenarioSourceReference("Official site", "https://weatherxm.com/"),
        ScenarioSourceReference("Rewards mechanism", "https://docs.weatherxm.com/rewards/rewards-mechanism"),
        ScenarioSourceReference("Claim rewards", "https://docs.weatherxm.com/rewards/claim-rewards"),
        ScenarioSourceReference("CoinGecko WXM", "https://www.coingecko.com/en/coins/weatherxm"),
    ),
    hardware_requirements=("D1 WiFi weather station", "Outdoor installation", "WiFi", "Arbitrum wallet"),
    geography_dependency="Station quality, local weather-cell density, and cell allocation affect rewards.",
    platforms=("hardware-node",),
    uncertainty=ScenarioRangeDefinition(
        low_reward_amount_day="0.75",
        high_reward_amount_day="3.0",
        description="Configured station reward range until station/cell API history is available.",
    ),
)


DIMO_SOFTWARE_ONLY_V1 = ScenarioYieldStrategyDefinition(
    strategy_id="dimo-software-only-compatible-car",
    strategy_version="v1",
    opportunity_id="dimo",
    opportunity_type="DEPIN_NODE",
    game_id_alias="dimo",
    opportunity_name="DIMO",
    name="DIMO Software-Only Compatible Car",
    chain="polygon",
    economy_type="vehicle-data",
    description=(
        "Software-only compatible-car scenario using official DIMO reward points logic, weekly issuance, "
        "Pro subscription cost, and a configured network-point denominator."
    ),
    reporting_currency="USD",
    metric_prefix="dimo.software_only.compatible_car",
    break_even_basis="capital_at_risk",
    capital=ScenarioCapitalDefinition(
        sunk_cost_usd="0",
        recoverable_entry_cost_usd="0",
        current_recoverable_value_usd="0",
        initial_operating_reserve_usd="8.99",
        capital_at_risk_usd="8.99",
        source_locator="https://support.dimo.org/",
        note="Software connection has no hardware purchase; one month of Pro subscription is the modeled initial reserve.",
    ),
    reward=ScenarioRewardDefinition(
        kind="token_day",
        reward_asset_id="polygon:dimo:DIMO",
        reward_asset_symbol="DIMO",
        amount_day="0.3157142857142857142857142857",
        amount_unit="DIMO/day",
        cash_realization_ratio="1",
        realization_haircut_bps="500",
        price_provider_asset_id="dimo",
        fixture_reward_token_price_usd="0.08",
        source_locator="https://github.com/DIMO-Network/user-rewards-api",
        note=(
            "Token/day is GamCryp-derived from official weekly baseline and Smartcar points divided by a "
            "configured total-network-points denominator."
        ),
    ),
    costs=ScenarioCostDefinition(
        operating_cost_day_usd="0.2996666666666666666666666667",
        transaction_cost_day_usd="0.002",
        other_cost_day_usd="0",
        source_locator="https://support.dimo.org/",
        note="Operating cost amortizes a $8.99/month Pro subscription over 30 days; transaction cost is a micro-reserve.",
    ),
    assumptions=(
        ("weekly_baseline_dimo", "1105000"),
        ("smartcar_points", "1000"),
        ("configured_total_network_points", "500000000"),
        ("pro_subscription_usd_month", "8.99"),
        ("realization_haircut_bps", "500"),
    ),
    support_metrics=(
        ScenarioSupportMetric(
            "software_connection_price",
            "0",
            "USD",
            "dimo-docs",
            "official_docs",
            "https://support.dimo.org/",
            "Officially documented software connection path has no device purchase.",
        ),
        ScenarioSupportMetric(
            "r1_price_reference",
            "99.99",
            "USD",
            "dimo-store",
            "official_docs",
            "https://shop.dimo.org/",
            "Official R1 hardware reference price, not used in this software-only strategy capital.",
        ),
        ScenarioSupportMetric(
            "weekly_baseline_dimo",
            "1105000",
            "DIMO/week",
            "dimo-rewards",
            "official_docs",
            "https://github.com/DIMO-Network/user-rewards-api",
            "Official first-year weekly baseline referenced by the open rewards implementation.",
        ),
        ScenarioSupportMetric(
            "smartcar_points",
            "1000",
            "point",
            "dimo-rewards",
            "official_docs",
            "https://github.com/DIMO-Network/user-rewards-api",
            "Official Smartcar connection points.",
        ),
    ),
    warnings=(
        ScenarioWarningDefinition(
            "configured_network_points",
            "DIMO rewards depend on total network points; this model uses an explicit configured denominator.",
        ),
        ScenarioWarningDefinition(
            "vehicle_eligibility",
            "Vehicle compatibility, region, subscription state, and connection quality are user-specific.",
        ),
        ScenarioWarningDefinition(
            "negative_subscription_case",
            "Under the current fixture price and configured denominator, subscription cost exceeds modeled rewards.",
        ),
        ScenarioWarningDefinition(
            "non_executable_exit",
            "DIMO valuation uses market price plus haircut, not an executable quote.",
        ),
    ),
    source_references=(
        ScenarioSourceReference("DIMO support", "https://support.dimo.org/"),
        ScenarioSourceReference("User rewards API", "https://github.com/DIMO-Network/user-rewards-api"),
        ScenarioSourceReference("DIMO shop", "https://shop.dimo.org/"),
        ScenarioSourceReference("CoinGecko DIMO", "https://www.coingecko.com/en/coins/dimo"),
    ),
    hardware_requirements=("Compatible connected vehicle", "DIMO account", "Software connection or supported app path"),
    geography_dependency="Vehicle compatibility and subscription availability depend on region and supported car data integrations.",
    platforms=("mobile", "web"),
    uncertainty=ScenarioRangeDefinition(
        low_reward_amount_day="0.1578571428571428571428571429",
        high_reward_amount_day="0.6314285714285714285714285714",
        description="Configured low/base/high reward range for network-points denominator and streak sensitivity.",
    ),
)


MYSTERIUM_B2B_EXISTING_DEVICE_V1 = ScenarioYieldStrategyDefinition(
    strategy_id="mysterium-b2b-existing-device",
    strategy_version="v1",
    opportunity_id="mysterium-network-node",
    opportunity_type="DEPIN_NODE",
    game_id_alias="mysterium-network-node",
    opportunity_name="Mysterium Network Node",
    name="Mysterium B2B Existing Device Node",
    chain="ethereum",
    economy_type="bandwidth-node",
    description=(
        "Existing-device B2B-only Mysterium node scenario using official network fee, settlement threshold, "
        "market price, and a configured observed-earnings proxy."
    ),
    reporting_currency="USD",
    metric_prefix="mysterium.b2b.existing_device",
    break_even_basis="capital_at_risk",
    capital=ScenarioCapitalDefinition(
        sunk_cost_usd="0",
        recoverable_entry_cost_usd="0",
        current_recoverable_value_usd="0",
        initial_operating_reserve_usd="2.00",
        capital_at_risk_usd="2.00",
        source_locator="https://docs.mysterium.network/faq",
        note="Existing-device scenario uses an explicit reserve for electricity/withdrawal handling and excludes hardware purchase.",
    ),
    reward=ScenarioRewardDefinition(
        kind="token_day",
        reward_asset_id="ethereum:mysterium:MYST",
        reward_asset_symbol="MYST",
        amount_day="0.1",
        amount_unit="MYST/day",
        cash_realization_ratio="0.8",
        realization_haircut_bps="0",
        price_provider_asset_id="mysterium",
        fixture_reward_token_price_usd="0.20",
        source_locator="https://docs.mysterium.network/faq",
        note="Gross MYST/day is a configured comparable-node scenario; 20% official network fee is modeled as cash realization.",
    ),
    costs=ScenarioCostDefinition(
        operating_cost_day_usd="0.012",
        transaction_cost_day_usd="0.003",
        other_cost_day_usd="0",
        source_locator="https://docs.mysterium.network/faq",
        note="Operating and withdrawal costs are explicit low-power existing-device assumptions.",
    ),
    assumptions=(
        ("gross_myst_month", "3.0"),
        ("network_fee_percent", "20"),
        ("cash_realization_ratio", "0.8"),
        ("settlement_threshold_myst", "5"),
        ("traffic_mode", "B2B-only"),
    ),
    support_metrics=(
        ScenarioSupportMetric(
            "network_fee",
            "20",
            "percent",
            "mysterium-docs",
            "official_docs",
            "https://docs.mysterium.network/faq",
            "Official network fee.",
        ),
        ScenarioSupportMetric(
            "settlement_threshold",
            "5",
            "MYST",
            "mysterium-docs",
            "official_docs",
            "https://docs.mysterium.network/faq",
            "Official settlement threshold.",
        ),
        ScenarioSupportMetric(
            "supported_devices",
            "1",
            "boolean",
            "mysterium-docs",
            "official_docs",
            "https://docs.mysterium.network/faq",
            "Official docs list Mac, Linux, Windows, DAppNode, AVADO, and Raspberry Pi options.",
        ),
    ),
    warnings=(
        ScenarioWarningDefinition(
            "configured_node_earnings",
            "Node earnings are region, IP-quality, uptime, and demand dependent; this model uses a configured observed-earnings proxy.",
        ),
        ScenarioWarningDefinition(
            "public_vpn_traffic_restricted",
            "Public VPN traffic may be restricted or legally sensitive in some countries; this strategy assumes B2B-only traffic.",
        ),
        ScenarioWarningDefinition(
            "settlement_threshold",
            "A 5 MYST settlement threshold can delay cash realization for low-earning nodes.",
        ),
    ),
    source_references=(
        ScenarioSourceReference("Mysterium FAQ", "https://docs.mysterium.network/faq"),
        ScenarioSourceReference("Mystnodes", "https://mystnodes.com/"),
        ScenarioSourceReference("CoinGecko MYST", "https://www.coingecko.com/en/coins/mysterium"),
    ),
    hardware_requirements=("Existing always-on Mac, Linux, or Windows device", "Internet connection", "MYST wallet"),
    geography_dependency="Region, residential status, node quality, and local legal treatment materially affect demand and risk.",
    platforms=("desktop",),
    uncertainty=ScenarioRangeDefinition(
        low_reward_amount_day="0.02",
        high_reward_amount_day="0.30",
        description="Configured low/base/high node demand range before market conversion.",
    ),
)


SCENARIO_YIELD_STRATEGIES: tuple[ScenarioYieldStrategyDefinition, ...] = (
    STORJ_EXISTING_HARDWARE_V1,
    GEODNET_EMPTY_HEX_TRIPLE_BAND_V1,
    WEATHERXM_D1_WIFI_V1,
    DIMO_SOFTWARE_ONLY_V1,
    MYSTERIUM_B2B_EXISTING_DEVICE_V1,
)
