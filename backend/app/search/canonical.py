"""Canonical public URL inventory for crawlable GamCryp pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import Engine

from app.api.v1.service import ApiDataService
from app.config.settings import Settings
from app.storage.history import HistoryRepository
from app.strategies.catalog import (
    CATALOG_REVIEWED_AT,
    GUIDE_ONLY_INDEXABLE_OPPORTUNITY_IDS,
    get_opportunity,
    list_games,
    list_opportunities,
    primary_destination_for_opportunity,
)

CURATED_RANKING_MIN_RESULTS = 2


@dataclass(frozen=True)
class CuratedRankingPage:
    slug: str
    title: str
    description: str
    filters: dict[str, object]
    min_results: int = CURATED_RANKING_MIN_RESULTS
    required_platforms: tuple[str, ...] = ()
    excluded_platforms: tuple[str, ...] = ()
    activation_note: str = ""

    @property
    def path(self) -> str:
        return f"/rankings/{self.slug}"


@dataclass(frozen=True)
class CanonicalPage:
    path: str
    lastmod: datetime
    priority: str = "0.6"
    changefreq: str = "daily"

    def absolute_url(self, settings: Settings) -> str:
        return canonical_url(settings, self.path)


CURATED_RANKING_PAGES: tuple[CuratedRankingPage, ...] = (
    CuratedRankingPage(
        slug="under-25",
        title="Web3 strategies under $25 capital",
        description="Modeled Web3 earning strategies whose latest stored capital requirement is under $25.",
        filters={"capital_max": Decimal("25")},
    ),
    CuratedRankingPage(
        slug="high-confidence",
        title="High-confidence modeled Web3 strategies",
        description="Modeled strategies whose latest stored confidence score is at least 80.",
        filters={"confidence_min": 80},
    ),
    CuratedRankingPage(
        slug="gamefi",
        title="GameFi ROI rankings",
        description="Organic rankings for currently modeled GAME opportunities.",
        filters={"opportunity_type": "GAME"},
    ),
    CuratedRankingPage(
        slug="gamefi-under-10",
        title="GameFi strategies under $10 capital",
        description="Modeled GAME strategies whose latest stored capital requirement is under $10.",
        filters={"opportunity_type": "GAME", "capital_max": Decimal("10")},
    ),
    CuratedRankingPage(
        slug="gamefi-under-50",
        title="GameFi strategies under $50 capital",
        description="Modeled GAME strategies whose latest stored capital requirement is under $50.",
        filters={"opportunity_type": "GAME", "capital_max": Decimal("50")},
    ),
    CuratedRankingPage(
        slug="gamefi-under-100",
        title="GameFi strategies under $100 capital",
        description="Modeled GAME strategies whose latest stored capital requirement is under $100.",
        filters={"opportunity_type": "GAME", "capital_max": Decimal("100")},
    ),
    CuratedRankingPage(
        slug="lowest-capital-gamefi",
        title="Lowest-capital modeled GameFi strategies",
        description="Modeled GAME strategies under $25 capital, shown in organic API order with capital clearly visible.",
        filters={"opportunity_type": "GAME", "capital_max": Decimal("25")},
    ),
    CuratedRankingPage(
        slug="highest-roi-gamefi",
        title="Highest modeled GameFi ROI strategies",
        description="Modeled GAME strategies in organic ROI ranking order using latest successful stored snapshots.",
        filters={"opportunity_type": "GAME"},
    ),
    CuratedRankingPage(
        slug="best-passive-gamefi",
        title="Best passive GameFi ROI strategies",
        description="Modeled GAME strategies with passive or lock/yield-style economics, ranked from latest stored snapshots.",
        filters={"opportunity_type": "GAME", "economy_type": "locked-yield-reward"},
        activation_note="Publish only when at least two passive GameFi strategy snapshots qualify.",
    ),
    CuratedRankingPage(
        slug="best-depin-under-100",
        title="Best DePIN opportunities under $100",
        description="Modeled DePIN / node strategies under $100 capital, ranked only when reproducible snapshots exist.",
        filters={"opportunity_type": "DEPIN_NODE", "capital_max": Decimal("100")},
        activation_note="Blocked until at least two modeled DePIN strategy snapshots under $100 qualify.",
    ),
    CuratedRankingPage(
        slug="phone-depin",
        title="Phone-friendly DePIN earning opportunities",
        description="Modeled DePIN strategies for mobile-supported opportunities, published only when current snapshots qualify.",
        filters={"opportunity_type": "DEPIN_NODE"},
        required_platforms=("mobile",),
        activation_note="Blocked until at least two modeled DePIN strategy snapshots on mobile-supported opportunities qualify.",
    ),
    CuratedRankingPage(
        slug="pc-depin",
        title="PC DePIN earning opportunities",
        description="Modeled DePIN strategies for desktop, browser-extension, CLI, or node software opportunities.",
        filters={"opportunity_type": "DEPIN_NODE"},
        required_platforms=("desktop", "browser-extension", "cli", "docker-node"),
        activation_note="Blocked until at least two modeled DePIN strategy snapshots for PC-compatible opportunities qualify.",
    ),
    CuratedRankingPage(
        slug="no-hardware-depin",
        title="No-hardware DePIN earning opportunities",
        description="Modeled DePIN strategies that do not require a dedicated hardware-node opportunity profile.",
        filters={"opportunity_type": "DEPIN_NODE"},
        required_platforms=("browser-extension", "desktop", "web", "cli", "docker-node"),
        excluded_platforms=("hardware-node",),
        activation_note="Blocked until at least two modeled no-dedicated-hardware DePIN strategy snapshots qualify.",
    ),
)


def get_curated_ranking_page(slug: str) -> CuratedRankingPage | None:
    return next((page for page in CURATED_RANKING_PAGES if page.slug == slug), None)


def curated_rankings_for_page(service: ApiDataService, page: CuratedRankingPage):
    rankings = service.rankings_page(limit=100, offset=0, **page.filters)
    if not page.required_platforms and not page.excluded_platforms:
        return rankings

    items = [item for item in rankings.items if _ranking_item_matches_catalog_constraints(item, page)]
    reranked_items = [item.model_copy(update={"rank": index + 1}) for index, item in enumerate(items)]
    return rankings.model_copy(
        update={
            "items": reranked_items,
            "page": rankings.page.model_copy(update={"limit": rankings.page.limit, "offset": 0, "total": len(items)}),
        }
    )


def is_curated_ranking_page_publishable(page: CuratedRankingPage, rankings) -> bool:
    return rankings.page.total >= page.min_results


def published_curated_ranking_pages(service: ApiDataService) -> tuple[CuratedRankingPage, ...]:
    published = []
    for page in CURATED_RANKING_PAGES:
        rankings = curated_rankings_for_page(service, page)
        if is_curated_ranking_page_publishable(page, rankings):
            published.append(page)
    return tuple(published)


def _ranking_item_matches_catalog_constraints(item, page: CuratedRankingPage) -> bool:
    opportunity = get_opportunity(item.strategy.opportunity_id)
    if opportunity is None:
        return False
    platforms = set(opportunity.platforms)
    if page.required_platforms and platforms.isdisjoint(page.required_platforms):
        return False
    if page.excluded_platforms and not platforms.isdisjoint(page.excluded_platforms):
        return False
    return True


def canonical_url(settings: Settings, path: str) -> str:
    clean_path = canonical_path(path)
    return f"{settings.public_base_url}{clean_path}"


def canonical_path(path: str) -> str:
    text = str(path).strip() or "/"
    if not text.startswith("/"):
        text = f"/{text}"
    return text.split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"


def canonical_page_inventory(engine: Engine) -> list[CanonicalPage]:
    latest_by_strategy = {snapshot.strategy_id: snapshot for snapshot in HistoryRepository(engine).latest_snapshots()}
    latest_snapshot_time = max(
        (snapshot.calculated_at for snapshot in latest_by_strategy.values()),
        default=CATALOG_REVIEWED_AT,
    )
    pages: list[CanonicalPage] = [
        CanonicalPage("/", latest_snapshot_time, priority="1.0"),
        CanonicalPage("/opportunities", latest_snapshot_time, priority="0.8"),
        CanonicalPage("/rankings", latest_snapshot_time, priority="0.9"),
        CanonicalPage("/methodology", CATALOG_REVIEWED_AT, priority="0.7", changefreq="weekly"),
    ]

    service = ApiDataService(engine)
    strategies, _ = service.strategies_page(limit=1000, offset=0)
    current_strategy_times = {
        strategy.strategy_id: strategy.latest_snapshot.calculated_at
        for strategy in strategies
        if strategy.latest_snapshot is not None
        and strategy.latest_snapshot.freshness.overall_status == "fresh"
    }

    for opportunity in list_opportunities():
        strategy_times = [
            current_strategy_times[strategy_id]
            for strategy_id in opportunity.strategy_ids
            if strategy_id in current_strategy_times
        ]
        # Keep ordinary guide-only records out of the sitemap. A small explicit
        # exception allows a current, evidence-rich guide to answer demonstrated
        # search intent even when responsible financial ROI is unavailable.
        if not strategy_times and opportunity.opportunity_id not in GUIDE_ONLY_INDEXABLE_OPPORTUNITY_IDS:
            continue
        destination = primary_destination_for_opportunity(opportunity.opportunity_id)
        reviewed_at = destination.reviewed_at if destination else CATALOG_REVIEWED_AT
        pages.append(
            CanonicalPage(
                f"/opportunities/{opportunity.opportunity_id}",
                max(strategy_times, default=reviewed_at),
                priority="0.7" if strategy_times else "0.6",
            )
        )

    for strategy in strategies:
        snapshot = strategy.latest_snapshot
        if snapshot is None or snapshot.freshness.overall_status != "fresh":
            continue
        pages.append(
            CanonicalPage(
                f"/strategies/{strategy.strategy_id}",
                snapshot.calculated_at,
                priority="0.75",
            )
        )

    for page in CURATED_RANKING_PAGES:
        rankings = curated_rankings_for_page(service, page)
        if is_curated_ranking_page_publishable(page, rankings):
            pages.append(
                CanonicalPage(
                    page.path,
                    max(item.latest_snapshot.calculated_at for item in rankings.items),
                    priority="0.65",
                )
            )

    return sorted(pages, key=lambda page: page.path)


def canonical_public_paths(engine: Engine) -> set[str]:
    return {page.path for page in canonical_page_inventory(engine)}


def is_canonical_public_url(url: str, *, settings: Settings, public_paths: set[str]) -> bool:
    parsed = urlsplit(url)
    base = urlsplit(settings.public_base_url)
    if parsed.scheme != base.scheme or parsed.netloc != base.netloc:
        return False
    if parsed.query or parsed.fragment:
        return False
    path = canonical_path(parsed.path)
    if path.startswith(("/api", "/go", "/assets")):
        return False
    return path in public_paths


def lastmod_date(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).date().isoformat()
