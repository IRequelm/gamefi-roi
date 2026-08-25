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
from app.strategies.catalog import CATALOG_REVIEWED_AT, list_games, list_opportunities, list_strategies


@dataclass(frozen=True)
class CuratedRankingPage:
    slug: str
    title: str
    description: str
    filters: dict[str, object]

    @property
    def path(self) -> str:
        return f"/rankings/{self.slug}"


@dataclass(frozen=True)
class CanonicalPage:
    path: str
    lastmod: datetime
    priority: str = "0.6"
    changefreq: str = "hourly"

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
)


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

    for opportunity in list_opportunities():
        strategy_times = [
            latest_by_strategy[strategy_id].calculated_at
            for strategy_id in opportunity.strategy_ids
            if strategy_id in latest_by_strategy
        ]
        pages.append(
            CanonicalPage(
                f"/opportunities/{opportunity.opportunity_id}",
                max(strategy_times, default=CATALOG_REVIEWED_AT),
                priority="0.7" if opportunity.strategy_ids else "0.55",
            )
        )

    for game in list_games():
        strategy_times = [
            latest_by_strategy[strategy_id].calculated_at
            for strategy_id in game.strategy_ids
            if strategy_id in latest_by_strategy
        ]
        pages.append(CanonicalPage(f"/games/{game.game_id}", max(strategy_times, default=CATALOG_REVIEWED_AT)))

    for strategy in list_strategies():
        snapshot = latest_by_strategy.get(strategy.strategy_id)
        pages.append(
            CanonicalPage(
                f"/strategies/{strategy.strategy_id}",
                snapshot.calculated_at if snapshot is not None else CATALOG_REVIEWED_AT,
                priority="0.75",
            )
        )

    service = ApiDataService(engine)
    for page in CURATED_RANKING_PAGES:
        rankings = service.rankings_page(limit=50, offset=0, **page.filters)
        if rankings.items:
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
