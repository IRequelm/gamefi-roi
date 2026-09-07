"""Static catalog for opportunities, modeled games, and versioned strategies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1, DFK_JEWELER_STRATEGIES
from app.strategies.farmers_world import FARMERS_WORLD_AXE_STRATEGIES, FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.scenario_yield import SCENARIO_YIELD_STRATEGIES
from app.strategies.splinterlands import (
    SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1,
    SPLINTERLANDS_MODERN_RANKED_STRATEGIES,
)

G14_REVIEWED_AT = datetime(2026, 8, 23, tzinfo=UTC)
G18_REVIEWED_AT = datetime(2026, 8, 24, tzinfo=UTC)
CATALOG_REVIEWED_AT = G18_REVIEWED_AT


@dataclass(frozen=True)
class SourceReference:
    label: str
    url: str
    source_role: str = "OFFICIAL_PROJECT"


@dataclass(frozen=True)
class OpportunityGuidance:
    how_to_start: tuple[str, ...] | None = None
    what_you_need: tuple[str, ...] | None = None
    how_you_earn: tuple[str, ...] | None = None
    how_to_exit_or_claim: tuple[str, ...] | None = None


@dataclass(frozen=True)
class RoiUnavailableExplanation:
    reason: str
    missing_evidence: tuple[str, ...] | None = None
    modeling_requirements: tuple[str, ...] | None = None


@dataclass(frozen=True)
class OutboundDestination:
    destination_id: str
    destination_slug: str
    opportunity_id: str
    opportunity_type: str
    game_id: str | None
    strategy_id: str | None
    destination_type: str
    label: str
    official_url: str
    referral_url: str | None
    referral_code: str | None
    affiliate_program: str | None
    status: str
    is_affiliate: bool
    commercial_relationship: str
    disclosure_text: str
    source_reference: SourceReference
    reviewed_at: datetime
    verification_status: str
    allowed_surfaces: tuple[str, ...]
    referral_status: str = "NONE"
    expires_at: datetime | None = None

    @property
    def target_url(self) -> str:
        return self.referral_url if self.target_url_kind == "referral" else self.official_url

    @property
    def target_url_kind(self) -> str:
        return "referral" if self.referral_url and self.referral_status == "ACTIVE" else "official"

    def is_active(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return (
            self.status == "active"
            and self.verification_status == "verified"
            and (self.expires_at is None or self.expires_at > current)
        )


@dataclass(frozen=True)
class OpportunityCatalogEntry:
    opportunity_id: str
    opportunity_type: str
    name: str
    status: str
    platforms: tuple[str, ...]
    chains: tuple[str, ...]
    economy_types: tuple[str, ...]
    reward_asset_or_points_type: tuple[str, ...]
    value_realization_status: str
    official_source_references: tuple[SourceReference, ...]
    data_feasibility_status: str
    feasibility_summary: str
    strategy_ids: tuple[str, ...]
    outbound_destination_slugs: tuple[str, ...]
    legacy_game_id: str | None = None
    guidance: OpportunityGuidance | None = None
    roi_unavailable: RoiUnavailableExplanation | None = None
    logo_asset: str | None = None
    logo_alt: str | None = None
    logo_source_reference: SourceReference | None = None

    @property
    def admission_mode(self) -> str:
        return "MODELED" if self.strategy_ids else "GUIDE_ONLY"


@dataclass(frozen=True)
class GameCatalogEntry:
    game_id: str
    opportunity_id: str
    opportunity_type: str
    name: str
    chains: tuple[str, ...]
    economy_types: tuple[str, ...]
    status: str
    strategy_ids: tuple[str, ...]
    outbound_destination_slugs: tuple[str, ...]


@dataclass(frozen=True)
class StrategyCatalogEntry:
    strategy_id: str
    strategy_version: str
    opportunity_id: str
    opportunity_type: str
    game_id: str
    game_name: str
    name: str
    chain: str
    economy_type: str
    description: str
    outbound_destination_slugs: tuple[str, ...]


def _sources(items: Iterable[tuple[str, str]]) -> tuple[SourceReference, ...]:
    return tuple(SourceReference(label, url) for label, url in items)


def _strategy_ids(strategies: Iterable[object]) -> tuple[str, ...]:
    return tuple(str(strategy.strategy_id) for strategy in strategies)


def _strategy_catalogs(
    strategies: Iterable[object],
    *,
    opportunity_id: str,
    game_name: str,
    chain: str,
    economy_type: str,
    description: str,
    outbound_destination_slug: str,
) -> tuple[StrategyCatalogEntry, ...]:
    return tuple(
        StrategyCatalogEntry(
            strategy_id=str(strategy.strategy_id),
            strategy_version=str(strategy.strategy_version),
            opportunity_id=opportunity_id,
            opportunity_type="GAME",
            game_id=str(strategy.game_id),
            game_name=game_name,
            name=str(strategy.name),
            chain=chain,
            economy_type=economy_type,
            description=description,
            outbound_destination_slugs=(outbound_destination_slug,),
        )
        for strategy in strategies
    )


def _scenario_strategy_catalogs(strategies: Iterable[object]) -> tuple[StrategyCatalogEntry, ...]:
    return tuple(
        StrategyCatalogEntry(
            strategy_id=str(strategy.strategy_id),
            strategy_version=str(strategy.strategy_version),
            opportunity_id=str(strategy.opportunity_id),
            opportunity_type=str(strategy.opportunity_type),
            game_id=str(strategy.game_id_alias),
            game_name=str(strategy.opportunity_name),
            name=str(strategy.name),
            chain=str(strategy.chain),
            economy_type=str(strategy.economy_type),
            description=str(strategy.description),
            outbound_destination_slugs=(f"{strategy.opportunity_id}-official",),
        )
        for strategy in strategies
    )


def _opportunity(
    *,
    opportunity_id: str,
    opportunity_type: str,
    name: str,
    status: str,
    platforms: tuple[str, ...],
    chains: tuple[str, ...],
    economy_types: tuple[str, ...],
    reward_asset_or_points_type: tuple[str, ...],
    value_realization_status: str,
    source_references: tuple[tuple[str, str], ...],
    data_feasibility_status: str,
    feasibility_summary: str,
    outbound_destination_slug: str,
    strategy_ids: tuple[str, ...] = (),
    legacy_game_id: str | None = None,
    guidance: OpportunityGuidance | None = None,
    roi_unavailable: RoiUnavailableExplanation | None = None,
    logo_asset: str | None = None,
    logo_alt: str | None = None,
    logo_source_reference: tuple[str, str] | None = None,
) -> OpportunityCatalogEntry:
    return OpportunityCatalogEntry(
        opportunity_id=opportunity_id,
        opportunity_type=opportunity_type,
        name=name,
        status=status,
        platforms=platforms,
        chains=chains,
        economy_types=economy_types,
        reward_asset_or_points_type=reward_asset_or_points_type,
        value_realization_status=value_realization_status,
        official_source_references=_sources(source_references),
        data_feasibility_status=data_feasibility_status,
        feasibility_summary=feasibility_summary,
        strategy_ids=strategy_ids,
        outbound_destination_slugs=(outbound_destination_slug,),
        legacy_game_id=legacy_game_id,
        guidance=guidance,
        roi_unavailable=roi_unavailable,
        logo_asset=logo_asset,
        logo_alt=logo_alt,
        logo_source_reference=SourceReference(*logo_source_reference) if logo_source_reference else None,
    )


def _destination(
    *,
    opportunity_id: str,
    opportunity_type: str,
    slug: str,
    label: str,
    official_url: str,
    game_id: str | None = None,
    destination_type: str = "official_site",
) -> OutboundDestination:
    return OutboundDestination(
        destination_id=f"dest-{slug}-v1",
        destination_slug=slug,
        opportunity_id=opportunity_id,
        opportunity_type=opportunity_type,
        game_id=game_id,
        strategy_id=None,
        destination_type=destination_type,
        label=label,
        official_url=official_url,
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", official_url),
        reviewed_at=G18_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    )


DFK_STRATEGY_CATALOGS = _strategy_catalogs(
    DFK_JEWELER_STRATEGIES,
    opportunity_id="defi-kingdoms",
    game_name="DeFi Kingdoms",
    chain="dfk-chain",
    economy_type="locked-yield-reward",
    description="cJEWEL max-lock strategy with claimable JEWEL rewards and emergency-exit valuation.",
    outbound_destination_slug="defi-kingdoms-play",
)
FARMERS_WORLD_STRATEGY_CATALOGS = _strategy_catalogs(
    FARMERS_WORLD_AXE_STRATEGIES,
    opportunity_id="farmers-world",
    game_name="Farmers World",
    chain="wax",
    economy_type="resource-production",
    description="Axe wood production strategy with resource input costs and player-market exit value.",
    outbound_destination_slug="farmers-world-play",
)
SPLINTERLANDS_STRATEGY_CATALOGS = _strategy_catalogs(
    SPLINTERLANDS_MODERN_RANKED_STRATEGIES,
    opportunity_id="splinterlands",
    game_name="Splinterlands",
    chain="hive",
    economy_type="probabilistic-performance",
    description="Modern Ranked SPS expected-value strategy with explicit win-rate uncertainty.",
    outbound_destination_slug="splinterlands-play",
)
SCENARIO_YIELD_STRATEGY_CATALOGS = _scenario_strategy_catalogs(SCENARIO_YIELD_STRATEGIES)

DFK_STRATEGY_CATALOG = next(
    strategy for strategy in DFK_STRATEGY_CATALOGS if strategy.strategy_id == DFK_CJEWEL_MAX_LOCK_V1.strategy_id
)
FARMERS_WORLD_STRATEGY_CATALOG = next(
    strategy
    for strategy in FARMERS_WORLD_STRATEGY_CATALOGS
    if strategy.strategy_id == FARMERS_WORLD_AXE_WOOD_V1.strategy_id
)
SPLINTERLANDS_STRATEGY_CATALOG = next(
    strategy
    for strategy in SPLINTERLANDS_STRATEGY_CATALOGS
    if strategy.strategy_id == SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id
)

STRATEGIES = (
    *DFK_STRATEGY_CATALOGS,
    *FARMERS_WORLD_STRATEGY_CATALOGS,
    *SPLINTERLANDS_STRATEGY_CATALOGS,
    *SCENARIO_YIELD_STRATEGY_CATALOGS,
)

OPPORTUNITIES = (
    _opportunity(
        opportunity_id="defi-kingdoms",
        opportunity_type="GAME",
        name="DeFi Kingdoms",
        status="active",
        platforms=("web",),
        chains=("dfk-chain",),
        economy_types=("locked-yield-reward",),
        reward_asset_or_points_type=("JEWEL", "cJEWEL"),
        value_realization_status="realizable",
        source_references=(("Official site", "https://defikingdoms.com/"),),
        data_feasibility_status="GO",
        feasibility_summary="Existing G4 adapter has current entry, reward, and emergency-exit inputs.",
        strategy_ids=_strategy_ids(DFK_JEWELER_STRATEGIES),
        outbound_destination_slug="defi-kingdoms-play",
        legacy_game_id="defi-kingdoms",
        guidance=OpportunityGuidance(
            how_to_start=("Open DeFi Kingdoms on DFK Chain.",),
            what_you_need=("The modeled Jeweler strategy uses a JEWEL/cJEWEL position.",),
            how_you_earn=("Jeweler rewards are modeled from locked JEWEL/cJEWEL reward inputs.",),
            how_to_exit_or_claim=("The modeled exit uses the DFK Chain route; emergency withdrawal has a documented 50% penalty.",),
        ),
    ),
    _opportunity(
        opportunity_id="farmers-world",
        opportunity_type="GAME",
        name="Farmers World",
        status="active",
        platforms=("web",),
        chains=("wax",),
        economy_types=("resource-production",),
        reward_asset_or_points_type=("FWW", "FWF", "FWG"),
        value_realization_status="realizable",
        source_references=(("Official site", "https://farmersworld.io/"),),
        data_feasibility_status="GO",
        feasibility_summary="Existing G5 adapter has deterministic production economics and marketplace realization.",
        strategy_ids=_strategy_ids(FARMERS_WORLD_AXE_STRATEGIES),
        outbound_destination_slug="farmers-world-play",
        legacy_game_id="farmers-world",
    ),
    _opportunity(
        opportunity_id="splinterlands",
        opportunity_type="GAME",
        name="Splinterlands",
        status="active",
        platforms=("web",),
        chains=("hive",),
        economy_types=("probabilistic-performance",),
        reward_asset_or_points_type=("SPS",),
        value_realization_status="realizable",
        source_references=(("Official site", "https://splinterlands.com/"),),
        data_feasibility_status="GO",
        feasibility_summary="Existing G6 adapter models SPS expected value with explicit uncertainty.",
        strategy_ids=_strategy_ids(SPLINTERLANDS_MODERN_RANKED_STRATEGIES),
        outbound_destination_slug="splinterlands-play",
        legacy_game_id="splinterlands",
    ),
    _opportunity(
        opportunity_id="storj-storage-node",
        opportunity_type="DEPIN_NODE",
        name="Storj Storage Node",
        status="active",
        platforms=("desktop", "server"),
        chains=("ethereum",),
        economy_types=("storage-node",),
        reward_asset_or_points_type=("STORJ payout value",),
        value_realization_status="realizable",
        source_references=(
            ("Node overview", "https://storj.dev/node"),
            ("Payouts", "https://storj.dev/node/payouts"),
            ("Held-back amount", "https://storj.dev/node/faq/held-back-amount"),
        ),
        data_feasibility_status="GO",
        feasibility_summary="Official payout rates, minimum node requirements, dashboard fields, and held-back schedule support an existing-hardware storage-node scenario with explicit utilization assumptions.",
        strategy_ids=("storj-existing-hardware-storage-node",),
        outbound_destination_slug="storj-storage-node-official",
        guidance=OpportunityGuidance(
            how_to_start=("Follow Storj's official node overview to set up a storage node.",),
            what_you_need=("The reviewed scenario uses existing desktop or server hardware.",),
            how_you_earn=("Storj publishes node payout rates and dashboard-based payout information.",),
            how_to_exit_or_claim=("Review the official payouts guide and held-back amount schedule for payout timing.",),
        ),
    ),
    _opportunity(
        opportunity_id="geodnet",
        opportunity_type="DEPIN_NODE",
        name="GEODNET",
        status="active",
        platforms=("hardware-node",),
        chains=("polygon",),
        economy_types=("geospatial-node",),
        reward_asset_or_points_type=("GEOD",),
        value_realization_status="realizable",
        source_references=(
            ("Official store", "https://geodnet.com/store"),
            ("Token metrics", "https://docs.geodnet.com/docs/geodnet-token-metrics"),
            ("Quality requirements", "https://docs.geodnet.com/docs/geodnet-quality-of-data-requirements"),
        ),
        data_feasibility_status="GO",
        feasibility_summary="Official hardware price, daily reward schedule, performance thresholds, and GEOD market pricing support a location-sensitive triple-band station scenario.",
        strategy_ids=("geodnet-empty-hex-triple-band-base-station",),
        outbound_destination_slug="geodnet-official",
        logo_asset="/assets/logos/geodnet.ico",
        logo_alt="GEODNET logo",
        logo_source_reference=("GEODNET official website", "https://geodnet.com/"),
    ),
    _opportunity(
        opportunity_id="weatherxm",
        opportunity_type="DEPIN_NODE",
        name="WeatherXM",
        status="active",
        platforms=("hardware-node",),
        chains=("arbitrum",),
        economy_types=("weather-station",),
        reward_asset_or_points_type=("WXM",),
        value_realization_status="realizable",
        source_references=(
            ("Official site", "https://weatherxm.com/"),
            ("Rewards mechanism", "https://docs.weatherxm.com/rewards/rewards-mechanism"),
            ("Claim rewards", "https://docs.weatherxm.com/rewards/claim-rewards"),
        ),
        data_feasibility_status="GO",
        feasibility_summary="Official hardware price, reward mechanism, claim path, WXM market pricing, and API availability support a station scenario with visible cell-level limitations.",
        strategy_ids=("weatherxm-d1-wifi-station",),
        outbound_destination_slug="weatherxm-official",
        logo_asset="/assets/logos/weatherxm.png",
        logo_alt="WeatherXM logo",
        logo_source_reference=("WeatherXM official website", "https://weatherxm.com/"),
    ),
    _opportunity(
        opportunity_id="dimo",
        opportunity_type="DEPIN_NODE",
        name="DIMO",
        status="active",
        platforms=("mobile", "web"),
        chains=("polygon",),
        economy_types=("vehicle-data",),
        reward_asset_or_points_type=("DIMO",),
        value_realization_status="realizable",
        source_references=(
            ("DIMO support", "https://support.dimo.org/"),
            ("User rewards API", "https://github.com/DIMO-Network/user-rewards-api"),
            ("DIMO shop", "https://shop.dimo.org/"),
        ),
        data_feasibility_status="GO",
        feasibility_summary="Official reward logic, vehicle requirements, subscription costs, and DIMO market pricing support a narrow software-only compatible-car strategy with explicit network-share assumptions.",
        strategy_ids=("dimo-software-only-compatible-car",),
        outbound_destination_slug="dimo-official",
        logo_asset="/assets/logos/dimo.svg",
        logo_alt="DIMO logo",
        logo_source_reference=("DIMO official website", "https://drivedimo.com/"),
    ),
    _opportunity(
        opportunity_id="mysterium-network-node",
        opportunity_type="DEPIN_NODE",
        name="Mysterium Network Node",
        status="active",
        platforms=("desktop",),
        chains=("ethereum",),
        economy_types=("bandwidth-node",),
        reward_asset_or_points_type=("MYST",),
        value_realization_status="realizable",
        source_references=(
            ("Mysterium FAQ", "https://docs.mysterium.network/faq"),
            ("Node setup guide", "https://docs.mysterium.network/content-page"),
            ("Supported platforms", "https://docs.mysterium.network/supported-platforms"),
            ("Node overview", "https://docs.mysterium.network/about-mysterium"),
            ("Mystnodes", "https://mystnodes.com/"),
        ),
        data_feasibility_status="GO",
        feasibility_summary="Official device support, network fee, settlement threshold, and dashboard availability support a B2B-only existing-device strategy with explicit demand assumptions.",
        strategy_ids=("mysterium-b2b-existing-device",),
        outbound_destination_slug="mysterium-network-node-official",
        guidance=OpportunityGuidance(
            how_to_start=(
                "Install Mysterium Node using the official setup guide for a supported platform, then register and configure the node in NodeUI.",
                "Prefer the documented B2B traffic mode unless you have reviewed the legal and privacy implications of accepting public traffic in your country.",
            ),
            what_you_need=(
                "A supported desktop, server, Docker, Raspberry Pi, or other documented platform with a stable internet connection is required.",
                "The node uses more bandwidth and availability than CPU; configure the node wallet and keep the service reachable through the documented network setup.",
            ),
            how_you_earn=(
                "A node earns MYST when eligible users consume the service through it; demand, region, IP quality, configuration, and uptime affect realized usage.",
                "The network charges a 20% service fee, and running continuously can improve availability but does not guarantee traffic or earnings.",
            ),
            how_to_exit_or_claim=(
                "Check earnings and withdrawable balance in NodeUI at the documented local node address, typically http://[ip-of-your-node]:4449.",
                "Unsettled earnings are automatically settled at 5 MYST or can be manually settled to the configured external wallet; blockchain fees still apply.",
            ),
        ),
    ),
    _opportunity(
        opportunity_id="star-atlas-sage-labs",
        opportunity_type="GAME",
        name="Star Atlas SAGE Labs",
        status="candidate",
        platforms=("web",),
        chains=("solana",),
        economy_types=("strategy-game", "crafting", "player-market"),
        reward_asset_or_points_type=("ATLAS", "resources", "FIC"),
        value_realization_status="unknown",
        source_references=(
            ("How to earn", "https://support.staratlas.com/hc/en-us/articles/47061460246163-How-to-Earn-ATLAS-in-Star-Atlas"),
            ("How to start SAGE", "https://support.staratlas.com/hc/en-us/articles/47053533098387-How-to-start-playing-SAGE"),
            ("APIs and data", "https://build.staratlas.com/dev-resources/apis-and-data"),
        ),
        data_feasibility_status="PARKED",
        feasibility_summary="Official APIs and economy mechanics exist, but the handoff lacks a narrow starter fleet/activity loop and reproducible FIC or crafting production rate, so no financial strategy is modeled yet.",
        outbound_destination_slug="star-atlas-sage-labs-official",
    ),
    _opportunity(
        opportunity_id="aavegotchi",
        opportunity_type="GAME",
        name="Aavegotchi",
        status="candidate",
        platforms=("web",),
        chains=("base", "polygon"),
        economy_types=("resource-farming", "seasonal-rewards"),
        reward_asset_or_points_type=("GHST", "Alchemica"),
        value_realization_status="realizable",
        source_references=(
            ("Alchemica docs", "https://docs.aavegotchi.com/own/tokens/gotchus-alchemica"),
            ("Rarity farming docs", "https://docs.aavegotchi.com/own/earning-in-aavegotchi/rarity-farming"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Rewards are documented, but strategy production and current execution need a narrow adapter.",
        outbound_destination_slug="aavegotchi-official",
        logo_asset="/assets/logos/aavegotchi.png",
        logo_alt="Aavegotchi logo",
        logo_source_reference=("Aavegotchi official website", "https://aavegotchi.com/"),
    ),
    _opportunity(
        opportunity_id="alien-worlds",
        opportunity_type="GAME",
        name="Alien Worlds",
        status="candidate",
        platforms=("web",),
        chains=("wax", "bnb", "ethereum"),
        economy_types=("mining", "missions"),
        reward_asset_or_points_type=("TLM",),
        value_realization_status="realizable",
        source_references=(("Getting started guide", "https://support.alienworlds.io/help-center/articles/game/guides/getting-started-in-alien-worlds"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="TLM rewards are public, but tool/land production probabilities need machine-readable evidence.",
        outbound_destination_slug="alien-worlds-official",
    ),
    _opportunity(
        opportunity_id="axie-infinity",
        opportunity_type="GAME",
        name="Axie Infinity",
        status="candidate",
        platforms=("web", "mobile"),
        chains=("ronin",),
        economy_types=("seasonal-leaderboard", "combat"),
        reward_asset_or_points_type=("AXS", "SLP"),
        value_realization_status="realizable",
        source_references=(("Leaderboard guide", "https://support.axieinfinity.com/hc/en-us/articles/37434875503771-Guide-to-Axie-Leaderboards-Classic-Origins-Homeland"),),
        data_feasibility_status="PARKED",
        feasibility_summary="Current season distribution, placement probability, and entry composition remain unresolved.",
        outbound_destination_slug="axie-infinity-official",
    ),
    _opportunity(
        opportunity_id="big-time",
        opportunity_type="GAME",
        name="Big Time",
        status="candidate",
        platforms=("pc",),
        chains=("ethereum",),
        economy_types=("loot-drop", "time-crystal"),
        reward_asset_or_points_type=("BIGTIME",),
        value_realization_status="realizable",
        source_references=(("BIGTIME economy docs", "https://wiki.bigtime.gg/big-time-economy/economy-components/resources/usdtime-tokens"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="BIGTIME rewards are documented, but drop rates and Hourglass constraints need live evidence.",
        outbound_destination_slug="big-time-official",
        logo_asset="/assets/logos/big-time.png",
        logo_alt="Big Time logo",
        logo_source_reference=("Big Time official website", "https://bigtime.gg/"),
    ),
    _opportunity(
        opportunity_id="bless",
        opportunity_type="DEPIN_NODE",
        name="Bless Network",
        status="candidate",
        platforms=("browser-extension", "docker-node"),
        chains=("blessnet",),
        economy_types=("compute-contribution", "points-program"),
        reward_asset_or_points_type=("Bless rewards", "BLESS"),
        value_realization_status="unknown",
        source_references=(
            ("Run a node introduction", "https://docs.bless.network/run-a-node/introduction"),
            ("Official site", "https://bless.network/about"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Participation is documented, but reward formula and realizable value are insufficient.",
        outbound_destination_slug="bless-official",
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because the reward formula and realizable value are insufficiently documented.",
            missing_evidence=("A reproducible current reward-rate formula.", "A lawful, sourceable reward-to-cash route."),
            modeling_requirements=("Published earning rules with current rates.", "A reproducible market or settlement value for rewards."),
        ),
    ),
    _opportunity(
        opportunity_id="blockmesh",
        opportunity_type="DEPIN_NODE",
        name="BlockMesh",
        status="candidate",
        platforms=("browser-extension",),
        chains=(),
        economy_types=("bandwidth-contribution", "points-program"),
        reward_asset_or_points_type=("BlockMesh Points", "BlockMesh Tokens"),
        value_realization_status="future_airdrop_claim",
        source_references=(("BlockMesh FAQ", "https://block-mesh.github.io/docs/faq/faq.html"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Points determine eligibility, but exact formula and current realizable value are absent.",
        outbound_destination_slug="blockmesh-official",
    ),
    _opportunity(
        opportunity_id="datagram",
        opportunity_type="DEPIN_NODE",
        name="Datagram",
        status="candidate",
        platforms=("desktop-node",),
        chains=(),
        economy_types=("bandwidth-contribution", "uptime-points"),
        reward_asset_or_points_type=("Datagram Points",),
        value_realization_status="future_airdrop_claim",
        source_references=(
            ("Alpha rewards", "https://doc.datagram.network/rewards/datagram-points-alpha-testnet-rewards"),
            ("Rewards system", "https://doc.datagram.network/rewards/datagram-rewards-system"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Point rates and caps are documented, but financial conversion and account data are unresolved.",
        outbound_destination_slug="datagram-official",
    ),
    _opportunity(
        opportunity_id="dawn",
        opportunity_type="DEPIN_NODE",
        name="DAWN",
        status="candidate",
        platforms=("browser-extension",),
        chains=(),
        economy_types=("bandwidth-validation", "points-program"),
        reward_asset_or_points_type=("Rewards Points",),
        value_realization_status="non_transferable_points",
        source_references=(("DAWN terms", "https://www.dawninternet.com/terms"),),
        data_feasibility_status="REJECTED",
        feasibility_summary="Official terms reject monetary value, transferability, or redemption for current rewards.",
        outbound_destination_slug="dawn-official",
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because current rewards are not treated as monetary value and are not transferable or redeemable under the reviewed terms.",
            missing_evidence=("A lawful transferable or redeemable reward route.", "A reproducible monetary value for current rewards."),
            modeling_requirements=("Terms permitting monetary redemption or transfer.", "A sourceable claim route and settlement value."),
        ),
    ),
    _opportunity(
        opportunity_id="galxe",
        opportunity_type="POINTS",
        name="Galxe",
        status="candidate",
        platforms=("web",),
        chains=("multi-chain",),
        economy_types=("quest-rewards", "points-program"),
        reward_asset_or_points_type=("GG", "XP", "campaign rewards"),
        value_realization_status="non_transferable_points",
        source_references=(
            ("Rewards hub", "https://help.galxe.com/en/articles/10373007-introducing-galxe-rewards-hub"),
            ("Terms", "https://docs.galxe.com/about/legal/terms-of-service"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Quest rewards are visible, but GG/XP do not provide a general realizable ROI route.",
        outbound_destination_slug="galxe-official",
        logo_asset="/assets/logos/galxe.png",
        logo_alt="Galxe logo",
        logo_source_reference=("Galxe official website", "https://www.galxe.com/"),
    ),
    _opportunity(
        opportunity_id="gods-unchained",
        opportunity_type="GAME",
        name="Gods Unchained",
        status="candidate",
        platforms=("pc", "mobile"),
        chains=("immutable",),
        economy_types=("ranked-play", "card-market"),
        reward_asset_or_points_type=("GODS", "cards", "packs"),
        value_realization_status="realizable",
        source_references=(("Official API", "https://github.com/immutable/gods-unchained-api"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official API and assets exist, but reward EV and pack/card realization need a narrow model.",
        outbound_destination_slug="gods-unchained-official",
        logo_asset="/assets/logos/gods-unchained.ico",
        logo_alt="Gods Unchained logo",
        logo_source_reference=("Gods Unchained official website", "https://godsunchained.com/"),
    ),
    _opportunity(
        opportunity_id="grass",
        opportunity_type="DEPIN_NODE",
        name="Grass",
        status="candidate",
        platforms=("browser-extension", "desktop"),
        chains=("solana",),
        economy_types=("bandwidth-contribution", "points-program"),
        reward_asset_or_points_type=("Grass Points", "GRASS"),
        value_realization_status="non_transferable_points",
        source_references=(
            ("Grass terms", "https://www.grass.io/terms-and-conditions/"),
            ("Grass points guide", "https://www.grass.io/learn/unlock-rewards-with-grass-points-earn-refer-and-grow-your-network/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Points exist, but current monetary redemption and authorized account data are unavailable.",
        outbound_destination_slug="grass-official",
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because points do not currently have a reproducible monetary redemption route.",
            missing_evidence=("A lawful transferable reward or cash-conversion route.", "Authorized account-level earning and eligibility data."),
            modeling_requirements=("A documented claim route with reproducible value.", "Sourceable earning and eligibility inputs."),
        ),
        logo_asset="/assets/logos/grass.png",
        logo_alt="Grass logo",
        logo_source_reference=("Grass official media kit", "https://www.grass.io/media-kit/"),
    ),
    _opportunity(
        opportunity_id="illuvium",
        opportunity_type="GAME",
        name="Illuvium",
        status="candidate",
        platforms=("pc",),
        chains=("immutable",),
        economy_types=("seasonal-leaderboard", "combat", "collection"),
        reward_asset_or_points_type=("ILV", "Fuel", "leaderboard rewards"),
        value_realization_status="realizable",
        source_references=(("Rewards V2", "https://portal.illuvium.io/news/rewards-v2-devblog"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Reward pools are public, but player-performance distribution is not reproducible enough.",
        outbound_destination_slug="illuvium-official",
    ),
    _opportunity(
        opportunity_id="kaisar-network",
        opportunity_type="DEPIN_NODE",
        name="Kaisar Network",
        status="candidate",
        platforms=("node", "browser-extension"),
        chains=(),
        economy_types=("checker-node", "points-program"),
        reward_asset_or_points_type=("Kaisar rewards", "points"),
        value_realization_status="future_airdrop_claim",
        source_references=(("Checker node rewards", "https://docs.kaisar.io/kaisar-network/kaisar-rewards-mechanism/rewards-for-kaisar-checkers-node"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Reward formula is documented, but scores, epoch totals, and value route are unresolved.",
        outbound_destination_slug="kaisar-network-official",
    ),
    _opportunity(
        opportunity_id="kaito-yaps",
        opportunity_type="POINTS",
        name="Kaito Yaps",
        status="candidate",
        platforms=("web", "x"),
        chains=(),
        economy_types=("attention-points", "social-signal"),
        reward_asset_or_points_type=("Yaps",),
        value_realization_status="non_transferable_points",
        source_references=(("Yaps open protocol", "https://docs.kaito.ai/kaito-yaps-tokenized-attention/yaps-open-protocol"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Yaps scores are API-visible, but they are not an executable financial reward.",
        outbound_destination_slug="kaito-yaps-official",
    ),
    _opportunity(
        opportunity_id="layer3",
        opportunity_type="POINTS",
        name="Layer3",
        status="candidate",
        platforms=("web",),
        chains=("multi-chain",),
        economy_types=("quest-rewards", "staking", "points-program"),
        reward_asset_or_points_type=("L3", "XP", "quests"),
        value_realization_status="realizable",
        source_references=(
            ("Layer3 docs", "https://docs.layer3foundation.org/"),
            ("Tokenomics", "https://docs.layer3foundation.org/tokenomics"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="L3 exists, but generalized quest reward EV and costs vary by campaign.",
        outbound_destination_slug="layer3-official",
    ),
    _opportunity(
        opportunity_id="nexus",
        opportunity_type="DEPIN_NODE",
        name="Nexus",
        status="candidate",
        platforms=("cli", "web"),
        chains=(),
        economy_types=("compute-proving", "testnet-points"),
        reward_asset_or_points_type=("NEX Testnet Points", "NEX Testnet Tokens"),
        value_realization_status="future_airdrop_claim",
        source_references=(("Layer 1 proving FAQ", "https://docs.nexus.xyz/network/proving-on-the-layer-1/faq"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Proving participation is public, but conversion and market value are not current inputs.",
        outbound_destination_slug="nexus-official",
    ),
    _opportunity(
        opportunity_id="nifty-island",
        opportunity_type="GAME",
        name="Nifty Island",
        status="candidate",
        platforms=("web",),
        chains=("ethereum", "base"),
        economy_types=("creator-economy", "play-to-earn-cycle"),
        reward_asset_or_points_type=("ISLAND", "Blooms"),
        value_realization_status="realizable",
        source_references=(
            ("How to earn", "https://guide.niftyisland.com/how-to-earn"),
            ("Play-to-earn system", "https://guide.niftyisland.com/island-token/allocation-and-distribution/play-to-earn-p2e-system"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Cycle formula is documented, but account Blooms, caps, and eligibility are account-scoped.",
        outbound_destination_slug="nifty-island-official",
    ),
    _opportunity(
        opportunity_id="nodepay",
        opportunity_type="POINTS",
        name="Nodepay",
        status="candidate",
        platforms=("web", "extension"),
        chains=("solana",),
        economy_types=("human-signal-contribution", "points-program"),
        reward_asset_or_points_type=("Signal Points", "Node Points", "NC"),
        value_realization_status="future_airdrop_claim",
        source_references=(
            ("Rewards system", "https://docs.nodepay.ai/user-participation-and-rewards/rewards-system"),
            ("Nodecoin utility", "https://docs.nodepay.ai/nodecoin-usdnc/utility-of-usdnc"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Point aggregation is public, but pool share, eligibility, and account data are insufficient.",
        outbound_destination_slug="nodepay-official",
    ),
    _opportunity(
        opportunity_id="pirate-nation",
        opportunity_type="GAME",
        name="Pirate Nation",
        status="candidate",
        platforms=("web",),
        chains=("proof-of-play", "arbitrum"),
        economy_types=("questing", "crafting", "player-market"),
        reward_asset_or_points_type=("PIRATE", "items"),
        value_realization_status="realizable",
        source_references=(("Bounties docs", "https://docs.piratenation.game/learn/the-game/bounties"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Bounty mechanics exist, but current task EV, item costs, and sell route need an adapter.",
        outbound_destination_slug="pirate-nation-official",
    ),
    _opportunity(
        opportunity_id="pixels",
        opportunity_type="GAME",
        name="Pixels",
        status="candidate",
        platforms=("web",),
        chains=("ronin",),
        economy_types=("task-board", "resource-production"),
        reward_asset_or_points_type=("PIXEL",),
        value_realization_status="realizable",
        source_references=(
            ("PIXEL token docs", "https://docs.pixels.xyz/economics/tokens/usdpixel"),
            ("Task board guide", "https://help.pixels.xyz/en/articles/9165794-what-is-the-task-board"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Daily issuance is documented, but individual task allocation and sell route need an adapter.",
        outbound_destination_slug="pixels-official",
    ),
    _opportunity(
        opportunity_id="teneo",
        opportunity_type="DEPIN_NODE",
        name="Teneo",
        status="candidate",
        platforms=("browser-extension",),
        chains=(),
        economy_types=("data-signal-contribution", "points-program"),
        reward_asset_or_points_type=("Teneo Points",),
        value_realization_status="non_transferable_points",
        source_references=(
            ("Rewards and tokenomics", "https://teneo.gitbook.io/teneo-docs/rewards-and-tokenomics"),
            ("Official site", "https://teneo.pro/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Point rates are documented, but beta points are not financial products and data is account-scoped.",
        outbound_destination_slug="teneo-official",
    ),
    _opportunity(
        opportunity_id="wild-forest",
        opportunity_type="GAME",
        name="Wild Forest",
        status="candidate",
        platforms=("mobile", "web"),
        chains=("ronin",),
        economy_types=("strategy-combat", "leaderboard", "revenue-share"),
        reward_asset_or_points_type=("WF", "NFT rewards"),
        value_realization_status="realizable",
        source_references=(
            ("Official site", "https://playwildforest.io/"),
            ("Token share program", "https://wildforest.gitbook.io/whitepaper/wild-forest-tokenomics/token-share-program"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Reward mechanics are public, but performance distribution and allocation are not model-ready.",
        outbound_destination_slug="wild-forest-official",
    ),
    _opportunity(
        opportunity_id="aro-network",
        opportunity_type="DEPIN_NODE",
        name="ARO Network",
        status="candidate",
        platforms=("desktop", "mobile", "extension", "hardware-node"),
        chains=(),
        economy_types=("edge-resource-contribution", "points-program"),
        reward_asset_or_points_type=("Jade", "Badge", "ARO"),
        value_realization_status="future_airdrop_claim",
        source_references=(
            ("ARO docs", "https://docs.aro.network/"),
            ("Testnet S2", "https://docs.aro.network/campaign-hub/testnet-s2/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Jade emissions are documented, but individual share and realizable value are not sourceable.",
        outbound_destination_slug="aro-network-official",
    ),
    _opportunity(
        opportunity_id="hivemapper",
        opportunity_type="DEPIN_NODE",
        name="Hivemapper",
        status="candidate",
        platforms=("hardware-node", "mobile"),
        chains=("solana",),
        economy_types=("mapping-contribution", "token-reward"),
        reward_asset_or_points_type=("HONEY",),
        value_realization_status="unknown",
        source_references=(
            ("Official reward types", "https://docs.hivemapper.com/honey-token/earning-honey/reward-types/"),
            ("Official driving guide", "https://docs.hivemapper.com/contribute/driving/"),
            ("Official terms", "https://www.hivemapper.com/tos"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Driving and reward categories are documented, but device cost, region-specific demand, and reproducible earning rates are not established for financial ROI.",
        outbound_destination_slug="hivemapper-official",
        logo_asset="/assets/logos/hivemapper.ico",
        logo_alt="Hivemapper logo",
        logo_source_reference=("Hivemapper official website", "https://www.hivemapper.com/"),
        guidance=OpportunityGuidance(
            how_to_start=("Review the official contributor and driving requirements.",),
            what_you_need=("A supported mapping device and a compatible mobile setup are described by the project.",),
            how_you_earn=("Contributors earn HONEY for eligible mapping contributions under the project reward rules.",),
            how_to_exit_or_claim=("Review the project wallet and token instructions before treating rewards as realizable.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because device cost, location-dependent demand, and reproducible reward rates are not established from the reviewed evidence.",
            missing_evidence=("A reproducible device entry cost and operating-cost basis.", "Current region-specific earning rates and demand."),
            modeling_requirements=("Sourceable contribution-rate data by location and device.", "A reproducible HONEY claim and executable market route."),
        ),
    ),
    _opportunity(
        opportunity_id="honeygain",
        opportunity_type="DEPIN_NODE",
        name="Honeygain",
        status="candidate",
        platforms=("desktop", "mobile"),
        chains=("bsc",),
        economy_types=("bandwidth-contribution", "token-payout"),
        reward_asset_or_points_type=("Honeygain credits", "JMPT"),
        value_realization_status="partially_realizable",
        source_references=(
            ("Official traffic-rate help", "https://support.honeygain.com/hc/en-us/articles/360013231420-What-is-the-current-payout-rate"),
            ("Official payout methods", "https://support.honeygain.com/hc/en-us/articles/4412730790674-What-are-the-payout-methods"),
            ("Official payout request guide", "https://support.honeygain.com/hc/en-us/articles/4412735374226-How-to-request-a-payout"),
            ("Official payout fees", "https://support.honeygain.com/hc/en-us/articles/4412743372690-What-are-the-payout-fees"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official payout paths and connection requirements are documented, but traffic demand varies by location and no fixed earning rate supports reproducible ROI.",
        outbound_destination_slug="honeygain-official",
        guidance=OpportunityGuidance(
            how_to_start=("Install Honeygain and review whether sharing your connection is permitted by your network terms.",),
            what_you_need=("An eligible internet connection and a supported device are required.",),
            how_you_earn=("Honeygain credits depend on partner traffic demand and location; no fixed traffic rate is promised.",),
            how_to_exit_or_claim=("The official help center documents PayPal and JumpTokens payout paths and thresholds.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because partner traffic demand and location-dependent utilization do not produce a reproducible earning rate.",
            missing_evidence=("Current account- and location-level traffic utilization.", "A complete operating-cost basis for the user's connection and device."),
            modeling_requirements=("Authorized earning observations over a defined period.", "A reproducible payout and fee model for the selected payout route."),
        ),
    ),
    _opportunity(
        opportunity_id="earnapp",
        opportunity_type="DEPIN_NODE",
        name="EarnApp",
        status="candidate",
        platforms=("desktop", "mobile"),
        chains=(),
        economy_types=("bandwidth-contribution", "cash-payout"),
        reward_asset_or_points_type=("USD earnings",),
        value_realization_status="realizable",
        source_references=(
            ("Official rate help", "https://help.earnapp.com/hc/en-us/articles/38191916327441--What-are-the-EarnApp-rates-How-are-they-calculated"),
            ("Official redemption methods", "https://help.earnapp.com/hc/en-us/articles/10147246886801--What-are-the-available-payment-methods-and-processing-time"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official maximum rates and redemption rules are published, but actual use depends on demand, location, connection quality, and device operation.",
        outbound_destination_slug="earnapp-official",
        guidance=OpportunityGuidance(
            how_to_start=("Install EarnApp and review the supported device, connection, and region requirements.",),
            what_you_need=("A supported device with an eligible internet connection is required.",),
            how_you_earn=("Earnings are based on actual active traffic use, not simply time connected; published rates are maximums.",),
            how_to_exit_or_claim=("The official help center documents PayPal, Wise, and Amazon gift-card redemption thresholds.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because actual traffic utilization varies by location, demand, speed, and device use despite published maximum rates.",
            missing_evidence=("Account-level active-use observations and demand utilization.", "A complete device, connection, and payout-fee cost basis."),
            modeling_requirements=("Authorized usage observations over a defined period.", "A reproducible net payout model including applicable redemption costs."),
        ),
    ),
    _opportunity(
        opportunity_id="akash-provider",
        opportunity_type="DEPIN_NODE",
        name="Akash Provider",
        status="active",
        platforms=("server", "cloud-provider"),
        chains=("akash",),
        economy_types=("compute-provider", "tenant-leases"),
        reward_asset_or_points_type=("AKT",),
        value_realization_status="realizable",
        source_references=(
            ("Provider overview", "https://akash.network/providers/"),
            ("Providers and leases", "https://akash.network/docs/learn/core-concepts/providers-leases/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official provider setup, lease, escrow, and payment documentation exists, but utilization, hardware cost, and realized lease rates are operator- and market-dependent.",
        outbound_destination_slug="akash-provider-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the Akash Provider Console requirements and provider setup documentation.",),
            what_you_need=("A supported compute provider, network connectivity, Kubernetes-based provider setup, and AKT for required escrow are described by Akash.",),
            how_you_earn=("Providers offer CPU, GPU, memory, storage, and networking resources and earn when tenants create leases.",),
            how_to_exit_or_claim=("Provider earnings and wallet operations are handled through the Akash provider and chain tooling; verify current network instructions before operating.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because tenant utilization, realized lease prices, hardware costs, and operating costs are not reproducible from public catalog evidence alone.",
            missing_evidence=("A current utilization series for the selected hardware and region.", "A complete hardware, power, bandwidth, and escrow cost basis."),
            modeling_requirements=("Authorized provider utilization and lease observations.", "A reproducible net payout model using current realized lease data."),
        ),
    ),
    _opportunity(
        opportunity_id="golem-provider",
        opportunity_type="DEPIN_NODE",
        name="Golem Provider",
        status="active",
        platforms=("desktop", "server", "linux"),
        chains=("polygon", "ethereum"),
        economy_types=("compute-provider", "resource-marketplace"),
        reward_asset_or_points_type=("GLM",),
        value_realization_status="realizable",
        source_references=(
            ("Golem overview", "https://docs.golem.network/docs/golem/overview"),
            ("Provider installation", "https://docs.golem.network/docs/providers/provider-installation"),
            ("Token and payments", "https://docs.golem.network/docs/golem/overview/golem-token"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official provider installation, configurable pricing, payment networks, and GLM settlement are documented, but demand and realized utilization vary by hardware and price.",
        outbound_destination_slug="golem-provider-official",
        guidance=OpportunityGuidance(
            how_to_start=("Install the Golem provider using the official provider guide and select a production payment network.",),
            what_you_need=("A supported x86-64 Linux host, Docker or the direct provider installation, storage, and network access are required.",),
            how_you_earn=("Providers share unused compute resources and bill requestors in GLM according to configured prices and actual usage.",),
            how_to_exit_or_claim=("GLM is paid to the configured provider wallet on the selected payment network; confirm wallet and network settings before shutdown.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because provider demand, utilization, hardware cost, and operating costs are not fixed by the public provider documentation.",
            missing_evidence=("Current utilization and realized task volume for the selected host.", "A complete cost basis for hardware, electricity, bandwidth, and maintenance."),
            modeling_requirements=("Authorized provider usage observations.", "A reproducible net GLM payout and cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="helium-iot-hotspot",
        opportunity_type="DEPIN_NODE",
        name="Helium IoT Hotspot",
        status="active",
        platforms=("hardware-node", "gateway"),
        chains=("solana",),
        economy_types=("wireless-coverage", "data-transfer"),
        reward_asset_or_points_type=("HNT", "Data Credits"),
        value_realization_status="realizable",
        source_references=(
            ("Hotspot onboarding", "https://docs.helium.com/iot/onboard-a-hotspot/"),
            ("Rewardable entities", "https://docs.helium.com/network-data/solana/rewardable-entities/"),
            ("HNT token", "https://docs.helium.com/tokens/hnt-token"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official onboarding, data-transfer rewards, claim mechanics, and HNT/Data Credit documentation exist, but location, coverage quality, and traffic determine realized outcomes.",
        outbound_destination_slug="helium-iot-hotspot-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the official Helium IoT Hotspot onboarding guide and supported gateway hardware options.",),
            what_you_need=("A compatible LoRaWAN gateway, a Helium wallet, location assertion, and onboarding Data Credits are required.",),
            how_you_earn=("Hotspots can earn HNT for eligible device data carried by the network; coverage and data transfer affect rewards.",),
            how_to_exit_or_claim=("The rewardable entity claim flow updates on-chain state before issuing the claimable difference to the owner.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because local demand, coverage quality, hardware cost, connectivity, and realized data transfer are location-dependent.",
            missing_evidence=("A current location-specific traffic and reward observation series.", "A complete hardware, connectivity, power, and onboarding cost basis."),
            modeling_requirements=("Authorized hotspot reward observations.", "A reproducible net HNT and operating-cost model by location."),
        ),
    ),
    _opportunity(
        opportunity_id="theta-edge-node",
        opportunity_type="DEPIN_NODE",
        name="Theta Edge Node",
        status="active",
        platforms=("desktop", "edge-node"),
        chains=("theta",),
        economy_types=("edge-compute", "content-relay"),
        reward_asset_or_points_type=("TFUEL",),
        value_realization_status="realizable",
        source_references=(
            ("Theta Edge Node documentation", "https://docs.thetatoken.org/docs/setup-theta-edge-node"),
            ("Theta white paper", "https://assets.thetatoken.org/Theta-white-paper-3-0-latest.pdf"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Theta materials describe edge-node roles and TFUEL reward mechanisms, but eligibility, stake requirements, task demand, and device utilization require current operator verification.",
        outbound_destination_slug="theta-edge-node-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the current official Theta Edge Node documentation and download the supported node software from Theta.",),
            what_you_need=("A supported desktop or server, network availability, and any current eligibility or stake requirements are needed.",),
            how_you_earn=("Edge nodes may earn TFUEL through eligible relay, compute, or network participation mechanisms described by Theta.",),
            how_to_exit_or_claim=("Use the official Theta wallet and node instructions to review and claim available TFUEL before stopping the node.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because current task demand, node eligibility, stake requirements, and device utilization are not reproducible from the reviewed public evidence.",
            missing_evidence=("Current node-level workload and reward observations.", "A complete hardware, bandwidth, power, and any stake cost basis."),
            modeling_requirements=("Authorized node reward observations.", "A current reproducible TFUEL and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="render-node-operator",
        opportunity_type="DEPIN_NODE",
        name="Render Network Node Operator",
        status="active",
        platforms=("gpu-node", "desktop", "server"),
        chains=("solana",),
        economy_types=("gpu-rendering", "compute-marketplace"),
        reward_asset_or_points_type=("RENDER",),
        value_realization_status="realizable",
        source_references=(
            ("Node operator role", "https://know.rendernetwork.com/general-render-network/what-role-am-i"),
            ("Node operator participation", "https://rendernetwork.com/participate-node-operators"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Render materials describe GPU node operators and token payment for completed rendering work, but onboarding availability, tier requirements, utilization, and costs vary.",
        outbound_destination_slug="render-node-operator-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the official Render node-operator participation requirements and current onboarding status.",),
            what_you_need=("A supported GPU, compatible node software, reliable connectivity, and the required operator account setup are needed.",),
            how_you_earn=("Node operators make available GPU capacity for rendering jobs and receive RENDER for completed work.",),
            how_to_exit_or_claim=("Follow Render's current operator payout and wallet instructions to review completed-job balances and settlement.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because node admission, job utilization, GPU tier, energy cost, and realized job pricing are not fixed by public documentation.",
            missing_evidence=("Current operator admission and utilization data for the selected GPU.", "A complete GPU, power, bandwidth, and maintenance cost basis."),
            modeling_requirements=("Authorized node utilization and payout observations.", "A reproducible net RENDER and cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="filecoin-storage-provider",
        opportunity_type="DEPIN_NODE",
        name="Filecoin Storage Provider",
        status="active",
        platforms=("server", "storage-node"),
        chains=("filecoin",),
        economy_types=("decentralized-storage", "storage-deals"),
        reward_asset_or_points_type=("FIL",),
        value_realization_status="realizable",
        source_references=(
            ("Provide storage", "https://www.filecoin.io/provide-storage"),
            ("Storage provider economics", "https://github.com/filecoin-project/filecoin-docs/tree/main/storage-providers/filecoin-economics"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Filecoin materials document storage-provider roles, PDP onboarding, collateral, rewards, and penalties, but provider scale, deals, collateral, and operating costs require a specific deployment model.",
        outbound_destination_slug="filecoin-storage-provider-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review Filecoin's current storage-provider and PDP onboarding documentation before selecting an architecture.",),
            what_you_need=("Reliable storage infrastructure, compute, network capacity, provider software, and any required collateral or operational funds are needed.",),
            how_you_earn=("Storage providers earn through eligible storage services, storage deals, and protocol mechanisms subject to proof and penalty rules.",),
            how_to_exit_or_claim=("Use the official provider tooling and wallet procedures to manage collateral, deal proceeds, and FIL withdrawals.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because deployment scale, client deals, collateral, proof performance, hardware, and operating costs vary materially by provider architecture.",
            missing_evidence=("A specific provider deployment and current deal-utilization data.", "A complete collateral, hardware, power, bandwidth, and penalty basis."),
            modeling_requirements=("Authorized provider and deal observations.", "A reproducible net FIL model including collateral and failure costs."),
        ),
    ),
    _opportunity(
        opportunity_id="nosana-gpu-host",
        opportunity_type="DEPIN_NODE",
        name="Nosana GPU Host",
        status="active",
        platforms=("gpu-node", "desktop", "server", "wsl2"),
        chains=("solana",),
        economy_types=("gpu-compute", "ai-workloads"),
        reward_asset_or_points_type=("NOS",),
        value_realization_status="realizable",
        source_references=(
            ("GPU host overview", "https://nosana.com/hosts/"),
            ("Host requirements", "https://learn.nosana.com/about/getting-started"),
            ("Job execution and rewards", "https://learn.nosana.com/deployments/jobs/job_execution_flow"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Nosana materials document GPU host setup, hardware requirements, workload execution, and NOS rewards, but demand, queue position, utilization, and operating costs remain variable.",
        outbound_destination_slug="nosana-gpu-host-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the official Nosana host requirements and host setup guide before registering a GPU.",),
            what_you_need=("A compatible NVIDIA GPU, at least 12 GB RAM, 256 GB or more of SSD storage, and a suitable network connection are documented requirements.",),
            how_you_earn=("Hosts provide GPU resources for scheduled workloads and may earn NOS when jobs complete.",),
            how_to_exit_or_claim=("Review host dashboard balances and the official Solana wallet instructions before stopping or removing a host.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because GPU queue demand, utilization, hardware cost, power, and network payout conditions are not fixed by public documentation.",
            missing_evidence=("Current host utilization and realized workload observations.", "A complete GPU, power, bandwidth, and maintenance cost basis."),
            modeling_requirements=("Authorized host performance and payout observations.", "A reproducible net NOS and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="livepeer-orchestrator",
        opportunity_type="DEPIN_NODE",
        name="Livepeer Orchestrator",
        status="active",
        platforms=("gpu-node", "server"),
        chains=("ethereum",),
        economy_types=("video-transcoding", "compute-provider"),
        reward_asset_or_points_type=("ETH", "LPT"),
        value_realization_status="realizable",
        source_references=(
            ("Livepeer documentation", "https://docs.livepeer.org/v2"),
            ("Orchestrator incentive model", "https://docs.livepeer.org/v2/concepts/orchestrator-incentive-model"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Livepeer documentation covers orchestrator roles, transcoding work, staking, and rewards, but delegation, demand, hardware utilization, and operating costs require a specific node setup.",
        outbound_destination_slug="livepeer-orchestrator-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review Livepeer's current orchestrator prerequisites, software, and network documentation.",),
            what_you_need=("A suitable transcoding server or GPU, reliable bandwidth, node software, and any required stake or delegation setup are needed.",),
            how_you_earn=("Orchestrators provide video-processing capacity and participate in Livepeer's fee and incentive mechanisms described in the official docs.",),
            how_to_exit_or_claim=("Use the official Livepeer node, wallet, and staking instructions to manage rewards, delegation, and withdrawal operations.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because workload demand, orchestrator utilization, delegation, stake, hardware, and operating costs are not reproducible from public catalog evidence alone.",
            missing_evidence=("Current orchestrator workload and reward observations.", "A complete hardware, power, bandwidth, stake, and delegation cost basis."),
            modeling_requirements=("Authorized node performance and payout observations.", "A reproducible net reward and cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="aethir-checker-node",
        opportunity_type="DEPIN_NODE",
        name="Aethir Checker Node",
        status="active",
        platforms=("desktop", "server"),
        chains=("arbitrum",),
        economy_types=("cloud-quality-checking", "checker-node"),
        reward_asset_or_points_type=("ATH", "vATH"),
        value_realization_status="realizable",
        source_references=(
            ("Checker node operation", "https://docs.aethir.com/checker-guide/what-is-the-checker-node/how-do-checker-nodes-work"),
            ("Claim and withdraw", "https://docs.aethir.com/checker-guide/how-to-manage-checker-nodes/claim-and-withdraw"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Aethir documentation describes checker work, reward distribution, claim vesting, fees, and KYC, but license availability and operator economics require current verification.",
        outbound_destination_slug="aethir-checker-node-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the official Aethir Checker Node requirements, eligibility, and owner portal documentation.",),
            what_you_need=("A supported checker license, wallet, eligible jurisdiction, KYC, and reliable online operation are required.",),
            how_you_earn=("Checkers perform liveness, capacity, and quality checks and receive ATH or vATH rewards under the published rules.",),
            how_to_exit_or_claim=("The official claim flow starts vesting; completed ATH can later be withdrawn on Arbitrum after fees and applicable restrictions.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because license acquisition, task assignment, reward realization, vesting, jurisdiction, and operating costs require current account-specific evidence.",
            missing_evidence=("Current license availability and operator task observations.", "A complete acquisition, fee, vesting, and operating-cost basis."),
            modeling_requirements=("Authorized checker reward and task observations.", "A current net ATH model including vesting and claim constraints."),
        ),
    ),
    _opportunity(
        opportunity_id="io-net-worker",
        opportunity_type="DEPIN_NODE",
        name="io.net Worker",
        status="active",
        platforms=("gpu-node", "server"),
        chains=("solana",),
        economy_types=("gpu-compute", "ai-workloads"),
        reward_asset_or_points_type=("IO",),
        value_realization_status="realizable",
        source_references=(
            ("Worker earnings", "https://io.net/docs/guides/workers/earnings-rewards"),
            ("Usage and billing", "https://io.net/docs/guides/id/usage-and-billing"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official io.net documentation exposes worker jobs, block rewards, earnings, slashing, and withdrawals, but worker admission, utilization, GPU demand, and costs vary.",
        outbound_destination_slug="io-net-worker-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the official io.net Worker binary, hardware, cluster, and account requirements.",),
            what_you_need=("A supported CPU or GPU worker, reliable connectivity, compatible software, and an eligible account are required.",),
            how_you_earn=("Workers receive IO from eligible block rewards and completed compute jobs, subject to availability and slashing rules.",),
            how_to_exit_or_claim=("Use the io.net earnings and billing interface to inspect transactions, claims, and withdrawals.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because current worker demand, utilization, cluster assignment, reward policy, hardware, and operating costs are not reproducible from public evidence alone.",
            missing_evidence=("Current worker utilization and job-payment observations.", "A complete hardware, power, bandwidth, and slashing cost basis."),
            modeling_requirements=("Authorized worker earnings observations.", "A reproducible net IO and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="aleph-im-compute-resource-node",
        opportunity_type="DEPIN_NODE",
        name="Aleph.im Compute Resource Node",
        status="active",
        platforms=("server", "compute-node"),
        chains=(),
        economy_types=("decentralized-compute", "storage"),
        reward_asset_or_points_type=("ALEPH",),
        value_realization_status="realizable",
        source_references=(
            ("Compute resource nodes", "https://main.branch.docs.aleph.im/nodes/compute/"),
            ("Node rewards", "https://main.branch.docs.aleph.im/nodes/reliability/rewards/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Aleph.im documentation describes compute-resource-node hardware, registration, reliability scoring, and ALEPH rewards, but node demand and operating costs are deployment-specific.",
        outbound_destination_slug="aleph-im-compute-resource-node-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the official Aleph.im compute-resource-node installation and registration documentation.",),
            what_you_need=("A server with the documented CPU, memory, storage, and connectivity requirements plus ALEPH collateral is needed.",),
            how_you_earn=("Performant compute-resource nodes receive ALEPH rewards according to the current reliability and decentralization rules.",),
            how_to_exit_or_claim=("Use the Aleph account and node tooling to review rewards, staking, and withdrawal operations.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because node score, location, network composition, demand, collateral, and operating costs are not reproducible for a generic setup.",
            missing_evidence=("Current node score and reward observations.", "A complete hardware, bandwidth, power, and collateral cost basis."),
            modeling_requirements=("Authorized node performance and reward observations.", "A current net ALEPH and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="acurast-compute-provider",
        opportunity_type="DEPIN_NODE",
        name="Acurast Compute Provider",
        status="active",
        platforms=("mobile", "smartphone"),
        chains=("acurast",),
        economy_types=("mobile-compute", "staked-compute"),
        reward_asset_or_points_type=("ACU", "MIST points"),
        value_realization_status="realizable",
        source_references=(
            ("Compute provider setup", "https://docs.acurast.com/processors/become-compute-provider/"),
            ("Processor rewards", "https://docs.acurast.com/processors/rewards/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Acurast documentation describes supported phones, processor setup, benchmark and staking rewards, and deployment bonuses, but utilization and device costs vary.",
        outbound_destination_slug="acurast-compute-provider-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review Acurast's official compatible-device and Compute Provider setup documentation.",),
            what_you_need=("A compatible Android or iOS device, wallet, internet connection, and power are required; staked compute has additional token requirements.",),
            how_you_earn=("Providers receive ACU benchmark, staking, and deployment-execution rewards under the current processor rules.",),
            how_to_exit_or_claim=("Use the configured Acurast wallet and processor documentation to inspect and claim available rewards.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because processor utilization, device performance, staking, token value, power, and deployment demand are not reproducible for a generic phone.",
            missing_evidence=("Current device-level utilization and reward observations.", "A complete device, power, connectivity, and staking cost basis."),
            modeling_requirements=("Authorized processor observations.", "A reproducible net ACU and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="nym-mixnode",
        opportunity_type="DEPIN_NODE",
        name="Nym Mixnode",
        status="active",
        platforms=("server", "desktop"),
        chains=("nym",),
        economy_types=("privacy-network", "bandwidth-relay"),
        reward_asset_or_points_type=("NYM",),
        value_realization_status="realizable",
        source_references=(
            ("Nym network overview", "https://nym.com/docs"),
            ("Mixnode reward scheme", "https://nym.com/blog/improved-nym-node-reward-scheme"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Nym materials describe mixnode and gateway roles, stake and reputation effects, and NYM rewards, but demand, selection, bandwidth, and operating costs vary.",
        outbound_destination_slug="nym-mixnode-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review Nym's current node operator documentation and supported deployment instructions.",),
            what_you_need=("A reliable server, bandwidth, wallet, and the current mixnode configuration and delegation requirements are needed.",),
            how_you_earn=("Mixnodes relay mixnet traffic and can receive NYM rewards based on the current performance, stake, and selection rules.",),
            how_to_exit_or_claim=("Use the official Nym wallet and node tools to manage delegation, rewards, and withdrawals.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because node selection, traffic demand, reputation, stake, bandwidth, and operating costs are not reproducible from public evidence alone.",
            missing_evidence=("Current mixnode traffic, selection, and reward observations.", "A complete server, bandwidth, power, and stake cost basis."),
            modeling_requirements=("Authorized mixnode observations.", "A current net NYM and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="subspace-farmer",
        opportunity_type="DEPIN_NODE",
        name="Subspace Farmer",
        status="active",
        platforms=("desktop", "server", "storage-node"),
        chains=("subspace",),
        economy_types=("storage-farming", "block-production"),
        reward_asset_or_points_type=("SSC",),
        value_realization_status="realizable",
        source_references=(
            ("Protocol fees and rewards", "https://subspace.github.io/protocol-specs/docs/fees_and_rewards"),
            ("Subspace protocol specifications", "https://subspace.github.io/protocol-specs/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Subspace specifications describe farmers, storage fees, block rewards, and protocol participation, but current network status, capacity requirements, and operating costs need validation.",
        outbound_destination_slug="subspace-farmer-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review the current Subspace farmer software and protocol specifications before committing storage.",),
            what_you_need=("Supported storage hardware, a reliable connection, farmer software, and the current network setup are required.",),
            how_you_earn=("Farmers may receive block-production rewards and storage-related fees under the protocol rules.",),
            how_to_exit_or_claim=("Use the official farmer wallet and protocol tooling to inspect balances and transfer available SSC.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because current network usage, storage capacity, hardware, issuance, fees, and operating costs are not fixed by the specifications.",
            missing_evidence=("Current farmer utilization and reward observations.", "A complete storage, power, bandwidth, and hardware cost basis."),
            modeling_requirements=("Authorized farmer observations.", "A reproducible net SSC and operating-cost model."),
        ),
    ),
    _opportunity(
        opportunity_id="bittensor-miner",
        opportunity_type="DEPIN_NODE",
        name="Bittensor Miner",
        status="active",
        platforms=("gpu-node", "server", "linux"),
        chains=("bittensor",),
        economy_types=("machine-intelligence", "subnet-mining"),
        reward_asset_or_points_type=("TAO", "subnet emissions"),
        value_realization_status="realizable",
        source_references=(
            ("Official mining guide", "https://www.bittensor.com/docs/guides/mining"),
            ("Registration collateral", "https://www.bittensor.com/docs/guides/mining/collateral"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary="Official Bittensor documentation describes subnet-specific miner work, registration, emissions, and collateral, but subnet selection and performance economics are not generic or stable.",
        outbound_destination_slug="bittensor-miner-official",
        guidance=OpportunityGuidance(
            how_to_start=("Choose a current subnet and follow the official Bittensor wallet, registration, and miner documentation.",),
            what_you_need=("A supported Linux mining host, hotkey, subnet registration funds or collateral, and subnet-specific software are needed.",),
            how_you_earn=("Miners provide the commodity defined by a subnet and receive emissions according to that subnet's incentive mechanism.",),
            how_to_exit_or_claim=("Use the official Bittensor tooling to manage hotkeys, emissions, collateral, and withdrawable stake.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="Financial ROI is unavailable because subnet incentives, registration cost, competition, hardware, task demand, and emissions differ by subnet and change over time.",
            missing_evidence=("A selected subnet with current miner performance and emission observations.", "A complete hardware, power, registration, and collateral cost basis."),
            modeling_requirements=("Authorized miner observations for one selected subnet.", "A reproducible subnet-specific net TAO model."),
        ),
    ),
    _opportunity(
        opportunity_id="fluxnode",
        opportunity_type="DEPIN_NODE",
        name="FluxNode",
        status="watchlist",
        platforms=("server", "desktop"),
        chains=("flux",),
        economy_types=("decentralized-compute", "node-collateral"),
        reward_asset_or_points_type=("FLUX",),
        value_realization_status="realizable",
        source_references=(("Flux official whitepaper", "https://fluxwhitepaper.app.runonflux.io/Flux_-_Whitepaper_2.1.pdf"),),
        data_feasibility_status="PARKED",
        feasibility_summary="Official material describes FluxNode rewards, but current tier requirements, collateral, software status, and operator economics need a current primary documentation review before admission.",
        outbound_destination_slug="fluxnode-official",
        guidance=OpportunityGuidance(
            how_to_start=("Review current Flux node requirements and software documentation before acquiring collateral or hardware.",),
            what_you_need=("A supported node host, collateral, connectivity, and current Flux operator tooling are required.",),
            how_you_earn=("FluxNode operators participate in the Flux compute network and may receive FLUX rewards under current node rules.",),
            how_to_exit_or_claim=("Use official Flux wallet and node tooling to review collateral and rewards before stopping the node.",),
        ),
        roi_unavailable=RoiUnavailableExplanation(
            reason="The opportunity remains watchlisted because current primary documentation for tiers, collateral, and reward operation was not sufficiently current for admission in this batch.",
            missing_evidence=("Current official node setup and tier requirements.", "Current reward, collateral, and payout documentation."),
            modeling_requirements=("A fresh primary-source operator review.",),
        ),
    ),
)

GAMES = tuple(
    GameCatalogEntry(
        game_id=str(opportunity.legacy_game_id),
        opportunity_id=opportunity.opportunity_id,
        opportunity_type=opportunity.opportunity_type,
        name=opportunity.name,
        chains=opportunity.chains,
        economy_types=opportunity.economy_types,
        status=opportunity.status,
        strategy_ids=opportunity.strategy_ids,
        outbound_destination_slugs=opportunity.outbound_destination_slugs,
    )
    for opportunity in OPPORTUNITIES
    if opportunity.legacy_game_id is not None and opportunity.strategy_ids
)

OUTBOUND_DESTINATIONS = (
    _destination(
        opportunity_id="defi-kingdoms",
        opportunity_type="GAME",
        slug="defi-kingdoms-play",
        label="Play DeFi Kingdoms",
        official_url="https://defikingdoms.com/",
        game_id="defi-kingdoms",
        destination_type="play",
    ),
    _destination(
        opportunity_id="farmers-world",
        opportunity_type="GAME",
        slug="farmers-world-play",
        label="Play Farmers World",
        official_url="https://farmersworld.io/",
        game_id="farmers-world",
        destination_type="play",
    ),
    _destination(
        opportunity_id="splinterlands",
        opportunity_type="GAME",
        slug="splinterlands-play",
        label="Play Splinterlands",
        official_url="https://splinterlands.com/",
        game_id="splinterlands",
        destination_type="play",
    ),
    _destination(opportunity_id="storj-storage-node", opportunity_type="DEPIN_NODE", slug="storj-storage-node-official", label="Open Storj Node", official_url="https://storj.dev/node"),
    _destination(opportunity_id="geodnet", opportunity_type="DEPIN_NODE", slug="geodnet-official", label="Open GEODNET", official_url="https://geodnet.com/"),
    _destination(opportunity_id="weatherxm", opportunity_type="DEPIN_NODE", slug="weatherxm-official", label="Open WeatherXM", official_url="https://weatherxm.com/"),
    _destination(opportunity_id="dimo", opportunity_type="DEPIN_NODE", slug="dimo-official", label="Open DIMO", official_url="https://drivedimo.com/"),
    _destination(opportunity_id="mysterium-network-node", opportunity_type="DEPIN_NODE", slug="mysterium-network-node-official", label="Open Mysterium", official_url="https://docs.mysterium.network/faq"),
    _destination(opportunity_id="star-atlas-sage-labs", opportunity_type="GAME", slug="star-atlas-sage-labs-official", label="Open Star Atlas SAGE Labs", official_url="https://staratlas.com/game/sage-labs/"),
    _destination(opportunity_id="aavegotchi", opportunity_type="GAME", slug="aavegotchi-official", label="Open Aavegotchi", official_url="https://aavegotchi.com/"),
    _destination(opportunity_id="alien-worlds", opportunity_type="GAME", slug="alien-worlds-official", label="Open Alien Worlds", official_url="https://alienworlds.io/"),
    _destination(opportunity_id="axie-infinity", opportunity_type="GAME", slug="axie-infinity-official", label="Open Axie Infinity", official_url="https://axieinfinity.com/"),
    _destination(opportunity_id="big-time", opportunity_type="GAME", slug="big-time-official", label="Open Big Time", official_url="https://bigtime.gg/"),
    _destination(opportunity_id="bless", opportunity_type="DEPIN_NODE", slug="bless-official", label="Open Bless Network", official_url="https://bless.network/"),
    _destination(opportunity_id="blockmesh", opportunity_type="DEPIN_NODE", slug="blockmesh-official", label="Open BlockMesh", official_url="https://blockmesh.xyz/"),
    _destination(opportunity_id="datagram", opportunity_type="DEPIN_NODE", slug="datagram-official", label="Open Datagram", official_url="https://datagram.network/"),
    _destination(opportunity_id="dawn", opportunity_type="DEPIN_NODE", slug="dawn-official", label="Open DAWN", official_url="https://www.dawninternet.com/"),
    _destination(opportunity_id="galxe", opportunity_type="POINTS", slug="galxe-official", label="Open Galxe", official_url="https://www.galxe.com/"),
    _destination(opportunity_id="gods-unchained", opportunity_type="GAME", slug="gods-unchained-official", label="Open Gods Unchained", official_url="https://godsunchained.com/"),
    _destination(opportunity_id="grass", opportunity_type="DEPIN_NODE", slug="grass-official", label="Open Grass", official_url="https://www.grass.io/"),
    _destination(opportunity_id="illuvium", opportunity_type="GAME", slug="illuvium-official", label="Open Illuvium", official_url="https://illuvium.io/"),
    _destination(opportunity_id="kaisar-network", opportunity_type="DEPIN_NODE", slug="kaisar-network-official", label="Open Kaisar Network", official_url="https://kaisar.io/"),
    _destination(opportunity_id="kaito-yaps", opportunity_type="POINTS", slug="kaito-yaps-official", label="Open Kaito Yaps", official_url="https://yaps.kaito.ai/"),
    _destination(opportunity_id="layer3", opportunity_type="POINTS", slug="layer3-official", label="Open Layer3", official_url="https://layer3.xyz/"),
    _destination(opportunity_id="nexus", opportunity_type="DEPIN_NODE", slug="nexus-official", label="Open Nexus", official_url="https://nexus.xyz/"),
    _destination(opportunity_id="nifty-island", opportunity_type="GAME", slug="nifty-island-official", label="Open Nifty Island", official_url="https://niftyisland.com/"),
    _destination(opportunity_id="nodepay", opportunity_type="POINTS", slug="nodepay-official", label="Open Nodepay", official_url="https://nodepay.ai/"),
    _destination(opportunity_id="pirate-nation", opportunity_type="GAME", slug="pirate-nation-official", label="Open Pirate Nation", official_url="https://piratenation.game/"),
    _destination(opportunity_id="pixels", opportunity_type="GAME", slug="pixels-official", label="Open Pixels", official_url="https://www.pixels.xyz/"),
    _destination(opportunity_id="teneo", opportunity_type="DEPIN_NODE", slug="teneo-official", label="Open Teneo", official_url="https://teneo.pro/"),
    _destination(opportunity_id="wild-forest", opportunity_type="GAME", slug="wild-forest-official", label="Open Wild Forest", official_url="https://playwildforest.io/"),
    _destination(opportunity_id="aro-network", opportunity_type="DEPIN_NODE", slug="aro-network-official", label="Open ARO Network", official_url="https://aro.network/"),
    _destination(opportunity_id="hivemapper", opportunity_type="DEPIN_NODE", slug="hivemapper-official", label="Open Hivemapper", official_url="https://www.hivemapper.com/"),
    _destination(opportunity_id="honeygain", opportunity_type="DEPIN_NODE", slug="honeygain-official", label="Open Honeygain", official_url="https://www.honeygain.com/"),
    _destination(opportunity_id="earnapp", opportunity_type="DEPIN_NODE", slug="earnapp-official", label="Open EarnApp", official_url="https://earnapp.com/"),
    _destination(opportunity_id="akash-provider", opportunity_type="DEPIN_NODE", slug="akash-provider-official", label="Open Akash Provider", official_url="https://akash.network/providers/"),
    _destination(opportunity_id="golem-provider", opportunity_type="DEPIN_NODE", slug="golem-provider-official", label="Open Golem Provider", official_url="https://docs.golem.network/docs/providers/provider-installation"),
    _destination(opportunity_id="helium-iot-hotspot", opportunity_type="DEPIN_NODE", slug="helium-iot-hotspot-official", label="Open Helium IoT Hotspot", official_url="https://docs.helium.com/iot/onboard-a-hotspot/"),
    _destination(opportunity_id="theta-edge-node", opportunity_type="DEPIN_NODE", slug="theta-edge-node-official", label="Open Theta Edge Node", official_url="https://docs.thetatoken.org/docs/setup-theta-edge-node"),
    _destination(opportunity_id="render-node-operator", opportunity_type="DEPIN_NODE", slug="render-node-operator-official", label="Open Render Node Operator", official_url="https://rendernetwork.com/participate-node-operators"),
    _destination(opportunity_id="filecoin-storage-provider", opportunity_type="DEPIN_NODE", slug="filecoin-storage-provider-official", label="Open Filecoin Storage Provider", official_url="https://www.filecoin.io/provide-storage"),
    _destination(opportunity_id="nosana-gpu-host", opportunity_type="DEPIN_NODE", slug="nosana-gpu-host-official", label="Open Nosana GPU Host", official_url="https://nosana.com/hosts/"),
    _destination(opportunity_id="livepeer-orchestrator", opportunity_type="DEPIN_NODE", slug="livepeer-orchestrator-official", label="Open Livepeer Orchestrator", official_url="https://docs.livepeer.org/v2"),
    _destination(opportunity_id="aethir-checker-node", opportunity_type="DEPIN_NODE", slug="aethir-checker-node-official", label="Open Aethir Checker Node", official_url="https://docs.aethir.com/checker-guide/what-is-the-checker-node/how-do-checker-nodes-work"),
    _destination(opportunity_id="io-net-worker", opportunity_type="DEPIN_NODE", slug="io-net-worker-official", label="Open io.net Worker", official_url="https://io.net/docs/guides/workers/earnings-rewards"),
    _destination(opportunity_id="aleph-im-compute-resource-node", opportunity_type="DEPIN_NODE", slug="aleph-im-compute-resource-node-official", label="Open Aleph.im Compute Node", official_url="https://main.branch.docs.aleph.im/nodes/compute/"),
    _destination(opportunity_id="acurast-compute-provider", opportunity_type="DEPIN_NODE", slug="acurast-compute-provider-official", label="Open Acurast Compute Provider", official_url="https://docs.acurast.com/processors/become-compute-provider/"),
    _destination(opportunity_id="nym-mixnode", opportunity_type="DEPIN_NODE", slug="nym-mixnode-official", label="Open Nym Mixnode", official_url="https://nym.com/docs"),
    _destination(opportunity_id="subspace-farmer", opportunity_type="DEPIN_NODE", slug="subspace-farmer-official", label="Open Subspace Farmer", official_url="https://subspace.github.io/protocol-specs/"),
    _destination(opportunity_id="bittensor-miner", opportunity_type="DEPIN_NODE", slug="bittensor-miner-official", label="Open Bittensor Miner", official_url="https://www.bittensor.com/docs/guides/mining"),
    _destination(opportunity_id="fluxnode", opportunity_type="DEPIN_NODE", slug="fluxnode-official", label="Open FluxNode", official_url="https://fluxwhitepaper.app.runonflux.io/Flux_-_Whitepaper_2.1.pdf"),
)


def list_opportunities() -> tuple[OpportunityCatalogEntry, ...]:
    return tuple(sorted(OPPORTUNITIES, key=lambda opportunity: opportunity.opportunity_id))


def get_opportunity(opportunity_id: str) -> OpportunityCatalogEntry | None:
    return next((opportunity for opportunity in OPPORTUNITIES if opportunity.opportunity_id == opportunity_id), None)


def list_games() -> tuple[GameCatalogEntry, ...]:
    return tuple(sorted(GAMES, key=lambda game: game.game_id))


def get_game(game_id: str) -> GameCatalogEntry | None:
    return next((game for game in GAMES if game.game_id == game_id), None)


def list_strategies() -> tuple[StrategyCatalogEntry, ...]:
    return tuple(sorted(STRATEGIES, key=lambda strategy: strategy.strategy_id))


def get_strategy(strategy_id: str) -> StrategyCatalogEntry | None:
    return next((strategy for strategy in STRATEGIES if strategy.strategy_id == strategy_id), None)


def list_outbound_destinations() -> tuple[OutboundDestination, ...]:
    return tuple(sorted(OUTBOUND_DESTINATIONS, key=lambda destination: destination.destination_slug))


def get_outbound_destination(destination_slug: str) -> OutboundDestination | None:
    return next(
        (destination for destination in OUTBOUND_DESTINATIONS if destination.destination_slug == destination_slug),
        None,
    )


def outbound_destinations_for_opportunity(opportunity_id: str) -> tuple[OutboundDestination, ...]:
    opportunity = get_opportunity(opportunity_id)
    if opportunity is None:
        return ()
    by_slug = {destination.destination_slug: destination for destination in OUTBOUND_DESTINATIONS}
    return tuple(
        destination
        for slug in opportunity.outbound_destination_slugs
        if (destination := by_slug.get(slug)) is not None
    )


def primary_destination_for_opportunity(opportunity_id: str) -> OutboundDestination | None:
    destinations = outbound_destinations_for_opportunity(opportunity_id)
    return destinations[0] if destinations else None


def outbound_destinations_for_strategy(strategy_id: str) -> tuple[OutboundDestination, ...]:
    strategy = get_strategy(strategy_id)
    if strategy is None:
        return ()
    by_slug = {destination.destination_slug: destination for destination in OUTBOUND_DESTINATIONS}
    return tuple(
        destination
        for slug in strategy.outbound_destination_slugs
        if (destination := by_slug.get(slug)) is not None
    )


def primary_destination_for_strategy(strategy_id: str) -> OutboundDestination | None:
    destinations = outbound_destinations_for_strategy(strategy_id)
    strategy = get_strategy(strategy_id)
    if destinations:
        return destinations[0]
    if strategy is None:
        return None
    return primary_destination_for_opportunity(strategy.opportunity_id)
