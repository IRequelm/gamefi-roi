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
            ("Mystnodes", "https://mystnodes.com/"),
        ),
        data_feasibility_status="GO",
        feasibility_summary="Official device support, network fee, settlement threshold, and dashboard availability support a B2B-only existing-device strategy with explicit demand assumptions.",
        strategy_ids=("mysterium-b2b-existing-device",),
        outbound_destination_slug="mysterium-network-node-official",
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
