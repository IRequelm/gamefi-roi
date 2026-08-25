"""Static catalog for opportunities, modeled games, and versioned strategies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1, DFK_JEWELER_STRATEGIES
from app.strategies.farmers_world import FARMERS_WORLD_AXE_STRATEGIES, FARMERS_WORLD_AXE_WOOD_V1
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

STRATEGIES = (*DFK_STRATEGY_CATALOGS, *FARMERS_WORLD_STRATEGY_CATALOGS, *SPLINTERLANDS_STRATEGY_CATALOGS)

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
