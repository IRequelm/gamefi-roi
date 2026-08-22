"""Static catalog for opportunities, modeled games, and versioned strategies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1

G14_REVIEWED_AT = datetime(2026, 8, 23, tzinfo=UTC)


@dataclass(frozen=True)
class SourceReference:
    label: str
    url: str


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
    expires_at: datetime | None = None

    @property
    def target_url(self) -> str:
        return self.referral_url or self.official_url

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


DFK_STRATEGY_CATALOG = StrategyCatalogEntry(
    strategy_id=DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
    strategy_version=DFK_CJEWEL_MAX_LOCK_V1.strategy_version,
    opportunity_id=DFK_CJEWEL_MAX_LOCK_V1.game_id,
    opportunity_type="GAME",
    game_id=DFK_CJEWEL_MAX_LOCK_V1.game_id,
    game_name="DeFi Kingdoms",
    name=DFK_CJEWEL_MAX_LOCK_V1.name,
    chain="dfk-chain",
    economy_type="locked-yield-reward",
    description="cJEWEL max-lock strategy with claimable JEWEL rewards and emergency-exit valuation.",
    outbound_destination_slugs=("defi-kingdoms-play",),
)

FARMERS_WORLD_STRATEGY_CATALOG = StrategyCatalogEntry(
    strategy_id=FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
    strategy_version=FARMERS_WORLD_AXE_WOOD_V1.strategy_version,
    opportunity_id=FARMERS_WORLD_AXE_WOOD_V1.game_id,
    opportunity_type="GAME",
    game_id=FARMERS_WORLD_AXE_WOOD_V1.game_id,
    game_name="Farmers World",
    name=FARMERS_WORLD_AXE_WOOD_V1.name,
    chain=FARMERS_WORLD_AXE_WOOD_V1.chain,
    economy_type="resource-production",
    description="Axe wood production strategy with resource input costs and player-market exit value.",
    outbound_destination_slugs=("farmers-world-play",),
)

SPLINTERLANDS_STRATEGY_CATALOG = StrategyCatalogEntry(
    strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
    strategy_version=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_version,
    opportunity_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.game_id,
    opportunity_type="GAME",
    game_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.game_id,
    game_name="Splinterlands",
    name=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.name,
    chain=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.chain,
    economy_type="probabilistic-performance",
    description="Modern Ranked SPS expected-value strategy with explicit win-rate uncertainty.",
    outbound_destination_slugs=("splinterlands-play",),
)

STRATEGIES = (
    DFK_STRATEGY_CATALOG,
    FARMERS_WORLD_STRATEGY_CATALOG,
    SPLINTERLANDS_STRATEGY_CATALOG,
)

OPPORTUNITIES = (
    OpportunityCatalogEntry(
        opportunity_id="defi-kingdoms",
        opportunity_type="GAME",
        name="DeFi Kingdoms",
        status="active",
        platforms=("web",),
        chains=("dfk-chain",),
        economy_types=("locked-yield-reward",),
        reward_asset_or_points_type=("JEWEL", "cJEWEL"),
        value_realization_status="realizable",
        official_source_references=(SourceReference("Official site", "https://defikingdoms.com/"),),
        data_feasibility_status="GO",
        feasibility_summary="Existing G4 adapter has current entry/reward/exit inputs and persisted production snapshots.",
        strategy_ids=(DFK_CJEWEL_MAX_LOCK_V1.strategy_id,),
        outbound_destination_slugs=("defi-kingdoms-play",),
        legacy_game_id="defi-kingdoms",
    ),
    OpportunityCatalogEntry(
        opportunity_id="farmers-world",
        opportunity_type="GAME",
        name="Farmers World",
        status="active",
        platforms=("web",),
        chains=("wax",),
        economy_types=("resource-production",),
        reward_asset_or_points_type=("FWW", "FWF", "FWG"),
        value_realization_status="realizable",
        official_source_references=(SourceReference("Official site", "https://farmersworld.io/"),),
        data_feasibility_status="GO",
        feasibility_summary="Existing G5 adapter has deterministic production economics and marketplace realization assumptions.",
        strategy_ids=(FARMERS_WORLD_AXE_WOOD_V1.strategy_id,),
        outbound_destination_slugs=("farmers-world-play",),
        legacy_game_id="farmers-world",
    ),
    OpportunityCatalogEntry(
        opportunity_id="splinterlands",
        opportunity_type="GAME",
        name="Splinterlands",
        status="active",
        platforms=("web",),
        chains=("hive",),
        economy_types=("probabilistic-performance",),
        reward_asset_or_points_type=("SPS",),
        value_realization_status="realizable",
        official_source_references=(SourceReference("Official site", "https://splinterlands.com/"),),
        data_feasibility_status="GO",
        feasibility_summary="Existing G6 adapter models a supportable SPS expected-value strategy with explicit uncertainty.",
        strategy_ids=(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,),
        outbound_destination_slugs=("splinterlands-play",),
        legacy_game_id="splinterlands",
    ),
    OpportunityCatalogEntry(
        opportunity_id="grass",
        opportunity_type="DEPIN_NODE",
        name="Grass",
        status="candidate",
        platforms=("browser-extension", "desktop"),
        chains=("solana",),
        economy_types=("bandwidth-contribution", "points-program"),
        reward_asset_or_points_type=("Grass Points", "GRASS"),
        value_realization_status="non_transferable_points",
        official_source_references=(
            SourceReference("Grass terms", "https://www.grass.io/terms-and-conditions/"),
            SourceReference("Grass points guide", "https://grass-foundation.gitbook.io/grass-docs/how-to-guide/grass-points"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary=(
            "Official materials describe points and rewards, but points are not a reproducible financial ROI input without "
            "authorized account data and a current lawful realizable value route."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("grass-official",),
    ),
    OpportunityCatalogEntry(
        opportunity_id="teneo",
        opportunity_type="DEPIN_NODE",
        name="Teneo",
        status="candidate",
        platforms=("browser-extension",),
        chains=(),
        economy_types=("data-signal-contribution", "points-program"),
        reward_asset_or_points_type=("Teneo Points",),
        value_realization_status="non_transferable_points",
        official_source_references=(
            SourceReference("Rewards and tokenomics", "https://teneo.gitbook.io/teneo-docs/rewards-and-tokenomics"),
            SourceReference("Official site", "https://teneo.pro/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary=(
            "Official docs describe heartbeat and data-signal points, but beta points are not financial products and "
            "individual earning data appears account/dashboard scoped."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("teneo-official",),
    ),
    OpportunityCatalogEntry(
        opportunity_id="aro-network",
        opportunity_type="DEPIN_NODE",
        name="ARO Network",
        status="candidate",
        platforms=("desktop", "mobile", "extension", "hardware-node"),
        chains=(),
        economy_types=("edge-resource-contribution", "points-program"),
        reward_asset_or_points_type=("Jade", "Badge", "ARO"),
        value_realization_status="future_airdrop_claim",
        official_source_references=(
            SourceReference("ARO docs", "https://docs.aro.network/"),
            SourceReference("Testnet S2", "https://docs.aro.network/campaign-hub/testnet-s2/"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary=(
            "Official docs describe node types, Jade emissions, and future drops, but exact individual share and "
            "realizable value are not yet reproducibly sourceable for financial ROI."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("aro-network-official",),
    ),
    OpportunityCatalogEntry(
        opportunity_id="nodepay",
        opportunity_type="POINTS",
        name="Nodepay",
        status="candidate",
        platforms=("web", "extension"),
        chains=("solana",),
        economy_types=("human-signal-contribution", "points-program"),
        reward_asset_or_points_type=("Signal Points", "Node Points", "NC"),
        value_realization_status="future_airdrop_claim",
        official_source_references=(
            SourceReference("Rewards system", "https://docs.nodepay.ai/user-participation-and-rewards/rewards-system"),
            SourceReference("Nodecoin utility", "https://docs.nodepay.ai/nodecoin-usdnc/utility-of-usdnc"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary=(
            "Official docs describe point aggregation and possible conversion to Nodecoin, but pool share, account "
            "eligibility, and automated data access are insufficient for a public financial ROI model."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("nodepay-official",),
    ),
    OpportunityCatalogEntry(
        opportunity_id="dawn",
        opportunity_type="DEPIN_NODE",
        name="DAWN",
        status="candidate",
        platforms=("browser-extension",),
        chains=(),
        economy_types=("bandwidth-validation", "points-program"),
        reward_asset_or_points_type=("Rewards Points",),
        value_realization_status="non_transferable_points",
        official_source_references=(SourceReference("DAWN terms", "https://www.dawninternet.com/terms"),),
        data_feasibility_status="REJECTED",
        feasibility_summary=(
            "Official terms state rewards have no monetary value and are not redeemable or transferable; financial ROI is "
            "rejected until terms and realizable value evidence change."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("dawn-official",),
    ),
    OpportunityCatalogEntry(
        opportunity_id="blockmesh",
        opportunity_type="DEPIN_NODE",
        name="BlockMesh",
        status="candidate",
        platforms=("browser-extension",),
        chains=(),
        economy_types=("bandwidth-contribution", "points-program"),
        reward_asset_or_points_type=("BlockMesh Points", "BlockMesh Tokens"),
        value_realization_status="future_airdrop_claim",
        official_source_references=(SourceReference("BlockMesh FAQ", "https://block-mesh.github.io/docs/faq/faq.html"),),
        data_feasibility_status="PARTIAL",
        feasibility_summary=(
            "Official FAQ says points determine token eligibility, but exact formula, individual data access, and current "
            "realizable value are not sufficient for a financial ROI adapter."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("blockmesh-official",),
    ),
    OpportunityCatalogEntry(
        opportunity_id="bless",
        opportunity_type="DEPIN_NODE",
        name="Bless Network",
        status="candidate",
        platforms=("browser-extension", "docker-node"),
        chains=("blessnet",),
        economy_types=("compute-contribution", "points-program"),
        reward_asset_or_points_type=("Bless rewards", "BLESS"),
        value_realization_status="unknown",
        official_source_references=(
            SourceReference("Run a node introduction", "https://docs.bless.network/run-a-node/introduction"),
            SourceReference("Official site", "https://bless.network/about"),
        ),
        data_feasibility_status="PARTIAL",
        feasibility_summary=(
            "Official docs describe browser and native node participation with rewards, but sourceable reward formula, "
            "individual earning data, and current realizable value are insufficient for financial ROI."
        ),
        strategy_ids=(),
        outbound_destination_slugs=("bless-official",),
    ),
)


GAMES = (
    GameCatalogEntry(
        game_id="defi-kingdoms",
        opportunity_id="defi-kingdoms",
        opportunity_type="GAME",
        name="DeFi Kingdoms",
        chains=("dfk-chain",),
        economy_types=("locked-yield-reward",),
        status="active",
        strategy_ids=(DFK_CJEWEL_MAX_LOCK_V1.strategy_id,),
        outbound_destination_slugs=("defi-kingdoms-play",),
    ),
    GameCatalogEntry(
        game_id="farmers-world",
        opportunity_id="farmers-world",
        opportunity_type="GAME",
        name="Farmers World",
        chains=("wax",),
        economy_types=("resource-production",),
        status="active",
        strategy_ids=(FARMERS_WORLD_AXE_WOOD_V1.strategy_id,),
        outbound_destination_slugs=("farmers-world-play",),
    ),
    GameCatalogEntry(
        game_id="splinterlands",
        opportunity_id="splinterlands",
        opportunity_type="GAME",
        name="Splinterlands",
        chains=("hive",),
        economy_types=("probabilistic-performance",),
        status="active",
        strategy_ids=(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,),
        outbound_destination_slugs=("splinterlands-play",),
    ),
)


OUTBOUND_DESTINATIONS = (
    OutboundDestination(
        destination_id="dest-defi-kingdoms-play-v1",
        destination_slug="defi-kingdoms-play",
        opportunity_id="defi-kingdoms",
        opportunity_type="GAME",
        game_id="defi-kingdoms",
        strategy_id=None,
        destination_type="play",
        label="Play DeFi Kingdoms",
        official_url="https://defikingdoms.com/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://defikingdoms.com/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-farmers-world-play-v1",
        destination_slug="farmers-world-play",
        opportunity_id="farmers-world",
        opportunity_type="GAME",
        game_id="farmers-world",
        strategy_id=None,
        destination_type="play",
        label="Play Farmers World",
        official_url="https://farmersworld.io/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://farmersworld.io/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-splinterlands-play-v1",
        destination_slug="splinterlands-play",
        opportunity_id="splinterlands",
        opportunity_type="GAME",
        game_id="splinterlands",
        strategy_id=None,
        destination_type="play",
        label="Play Splinterlands",
        official_url="https://splinterlands.com/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://splinterlands.com/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-grass-official-v1",
        destination_slug="grass-official",
        opportunity_id="grass",
        opportunity_type="DEPIN_NODE",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open Grass",
        official_url="https://www.grass.io/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://www.grass.io/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-teneo-official-v1",
        destination_slug="teneo-official",
        opportunity_id="teneo",
        opportunity_type="DEPIN_NODE",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open Teneo",
        official_url="https://teneo.pro/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://teneo.pro/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-aro-network-official-v1",
        destination_slug="aro-network-official",
        opportunity_id="aro-network",
        opportunity_type="DEPIN_NODE",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open ARO Network",
        official_url="https://aro.network/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://aro.network/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-nodepay-official-v1",
        destination_slug="nodepay-official",
        opportunity_id="nodepay",
        opportunity_type="POINTS",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open Nodepay",
        official_url="https://nodepay.ai/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://nodepay.ai/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-dawn-official-v1",
        destination_slug="dawn-official",
        opportunity_id="dawn",
        opportunity_type="DEPIN_NODE",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open DAWN",
        official_url="https://www.dawninternet.com/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://www.dawninternet.com/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-blockmesh-official-v1",
        destination_slug="blockmesh-official",
        opportunity_id="blockmesh",
        opportunity_type="DEPIN_NODE",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open BlockMesh",
        official_url="https://blockmesh.xyz/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://blockmesh.xyz/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
    OutboundDestination(
        destination_id="dest-bless-official-v1",
        destination_slug="bless-official",
        opportunity_id="bless",
        opportunity_type="DEPIN_NODE",
        game_id=None,
        strategy_id=None,
        destination_type="official_site",
        label="Open Bless Network",
        official_url="https://bless.network/",
        referral_url=None,
        referral_code=None,
        affiliate_program=None,
        status="active",
        is_affiliate=False,
        commercial_relationship="none",
        disclosure_text="Official outbound link. No affiliate relationship is configured for this destination.",
        source_reference=SourceReference("Official site", "https://bless.network/"),
        reviewed_at=G14_REVIEWED_AT,
        verification_status="verified",
        allowed_surfaces=("web", "api", "redirect"),
    ),
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
