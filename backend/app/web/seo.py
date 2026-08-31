"""Server-rendered public pages for search and AI discovery."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Request

from app.api.v1.schemas import (
    OpportunityDetail,
    OpportunitySummary,
    RankingItem,
    RankingsPage,
    StrategySnapshotPayload,
    StrategySummary,
)
from app.api.v1.service import ApiDataService
from app.config.settings import Settings
from app.search.canonical import (
    CuratedRankingPage,
    canonical_url,
    curated_rankings_for_page,
    lastmod_date,
    published_curated_ranking_pages,
)
from app.storage.monetization import MonetizationRepository, normalize_acquisition_channel
from app.strategies.catalog import CATALOG_REVIEWED_AT

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ASSETS = PROJECT_ROOT / "frontend" / "assets"
MONTH_NAMES = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class SeoPage:
    path: str
    title: str
    description: str
    body_html: str
    json_ld: tuple[dict, ...]
    robots: str = "index,follow"
    og_type: str = "website"
    lastmod: datetime | None = None


def render_document(page: SeoPage, *, settings: Settings) -> str:
    canonical = canonical_url(settings, page.path)
    image_url = canonical_url(settings, "/assets/brand/gamcryp-logo.png")
    verification_meta = _verification_meta(settings)
    scripts = "\n".join(
        f'<script type="application/ld+json">{_json_ld(payload)}</script>' for payload in page.json_ld
    )
    styles = asset_url("/assets/styles.css")
    app_js = asset_url("/assets/app.js")
    logo = asset_url("/assets/brand/gamcryp-logo.png")
    public_config = _public_config_script(settings)
    footer = _footer_html(settings)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(page.title)}</title>
    <meta name="description" content="{escape(page.description)}">
    <meta name="robots" content="{escape(page.robots)}">
    <link rel="canonical" href="{escape(canonical)}">
    <meta property="og:title" content="{escape(page.title)}">
    <meta property="og:description" content="{escape(page.description)}">
    <meta property="og:url" content="{escape(canonical)}">
    <meta property="og:type" content="{escape(page.og_type)}">
    <meta property="og:image" content="{escape(image_url)}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape(page.title)}">
    <meta name="twitter:description" content="{escape(page.description)}">
    <meta name="twitter:image" content="{escape(image_url)}">
    {verification_meta}
    <link rel="stylesheet" href="{escape(styles)}">
    {scripts}
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="/" data-link>
        <img class="brand-logo" src="{escape(logo)}" alt="GamCryp">
        <span class="brand-lockup">
          <span class="brand-name">GamCryp</span>
          <span class="brand-tagline">Web3 Opportunity Intelligence</span>
        </span>
      </a>
      <nav class="site-nav" aria-label="Primary">
        <a href="/" data-link>ROI Finder</a>
        <a href="/rankings" data-link>Rankings</a>
        <a href="/opportunities" data-link>Opportunities</a>
        <a href="/methodology" data-link>Methodology</a>
      </nav>
    </header>
    <main id="app" tabindex="-1">
      {page.body_html}
    </main>
    {footer}
    {public_config}
    <script type="module" src="{escape(app_js)}"></script>
  </body>
</html>"""


def home_page(service: ApiDataService, *, settings: Settings, request: Request) -> SeoPage:
    rankings = service.rankings_page(limit=50, offset=0)
    opportunities, _total = service.opportunities_page(limit=50, offset=0)
    top = rankings.items[0] if rankings.items else None
    answer = (
        _ranking_answer(top.latest_snapshot, top.strategy)
        if top is not None
        else "GamCryp has no current modeled strategy snapshot available."
    )
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">GamCryp public beta</p>
          <h1>Web3 earning opportunities with ROI, Risk, Confidence, and evidence.</h1>
          <p class="lede">GamCryp tracks Web3 earning opportunities. When rewards and exits can be priced reproducibly, we calculate modeled ROI. When they cannot, we show why instead of inventing a number.</p>
          <p class="muted">{escape(answer)}</p>
          <div class="hero-proof-points" aria-label="GamCryp data principles">
            <span>Latest modeled snapshots</span>
            <span>Risk and confidence separated</span>
            <span>Unavailable ROI stays unavailable</span>
          </div>
        </section>
        {_render_home_answer_block(rankings, opportunities)}
        {_render_catalog_stats(rankings, opportunities)}
        {_render_ranking_cards(rankings.items[:3], heading="Current organic leaders")}
        {_render_opportunity_cards(opportunities, heading="Opportunity radar")}
      </div>
    """
    description = "Compare Web3 earning opportunities using latest modeled ROI, capital, net/day, break-even, Risk, Confidence, freshness, and source-backed unavailable states."
    return _page(
        request=request,
        settings=settings,
        path="/",
        title="GamCryp | Web3 Opportunity Intelligence",
        description=description,
        body_html=body,
        json_ld=(
            _organization_json(settings),
            _website_json(settings),
            _webpage_json(settings, "/", "GamCryp Web3 Opportunity Intelligence", description),
        ),
        lastmod=_rankings_lastmod(rankings),
    )


def rankings_page(service: ApiDataService, *, settings: Settings, request: Request) -> SeoPage:
    rankings = service.rankings_page(limit=50, offset=0)
    description = "Organic Web3 strategy rankings by latest 30D ROI, confidence, risk, calculation time, and strategy id. Sponsor and affiliate data never changes this order."
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Organic rankings</p>
          <h1>Current Web3 ROI strategy rankings</h1>
          <p class="lede">{escape(_rankings_summary(rankings))}</p>
          <p class="muted">Organic order is supplied by stored strategy snapshots and risk/confidence scores. Commercial metadata is separate.</p>
        </section>
        {_render_rankings_answer_block(rankings, "Current Web3 ROI strategy rankings")}
        {_render_curated_links(service)}
        {_render_ranking_cards(rankings.items, heading="Ranked strategies")}
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path="/rankings",
        title="Web3 ROI Rankings, Risk & Confidence | GamCryp",
        description=description,
        body_html=body,
        json_ld=_ranking_json_ld(
            settings,
            "/rankings",
            "Web3 ROI Rankings",
            description,
            rankings.items,
            [("/", "Home"), ("/rankings", "Rankings")],
        ),
        lastmod=_rankings_lastmod(rankings),
    )


def curated_rankings_page(
    service: ApiDataService,
    *,
    settings: Settings,
    request: Request,
    landing: CuratedRankingPage,
    rankings: RankingsPage | None = None,
) -> SeoPage:
    rankings = rankings or curated_rankings_for_page(service, landing)
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Curated organic rankings</p>
          <h1>{escape(landing.title)}</h1>
          <p class="lede">{escape(_rankings_summary(rankings))}</p>
          <p class="muted">{escape(landing.description)} Sponsored and affiliate relationships never affect these results.</p>
        </section>
        {_render_rankings_answer_block(rankings, landing.title, landing.filters)}
        {_render_ranking_cards(rankings.items, heading="Matching modeled strategies")}
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path=landing.path,
        title=f"{landing.title} | GamCryp",
        description=landing.description,
        body_html=body,
        json_ld=_ranking_json_ld(
            settings,
            landing.path,
            landing.title,
            landing.description,
            rankings.items,
            [("/", "Home"), ("/rankings", "Rankings"), (landing.path, landing.title)],
        ),
        lastmod=_rankings_lastmod(rankings),
    )


def opportunities_page(service: ApiDataService, *, settings: Settings, request: Request) -> SeoPage:
    opportunities, _total = service.opportunities_page(limit=100, offset=0)
    description = "Crawlable catalog of Games, DePIN / Nodes, and Points programs reviewed by GamCryp, including modeled ROI availability and unavailable-value reasons."
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Opportunity radar</p>
          <h1>Games, DePIN nodes, and points programs under review</h1>
          <p class="lede">GamCryp publishes financial ROI only when reward value, costs, timing, and exit route are lawful and reproducible. Points-only opportunities remain unavailable, not zero.</p>
        </section>
        {_render_opportunity_index_answer_block(opportunities)}
        {_render_opportunity_cards(opportunities, heading="Reviewed opportunities")}
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path="/opportunities",
        title="Web3 Opportunity Radar: Games, DePIN & Points | GamCryp",
        description=description,
        body_html=body,
        json_ld=(
            _webpage_json(settings, "/opportunities", "Web3 Opportunity Radar", description),
            _breadcrumb_json(settings, [("/", "Home"), ("/opportunities", "Opportunities")]),
        ),
        lastmod=_max_opportunity_lastmod(opportunities),
    )


def opportunity_page(
    opportunity: OpportunityDetail,
    *,
    settings: Settings,
    request: Request,
) -> SeoPage:
    strategy = opportunity.strategies[0] if opportunity.strategies else None
    snapshot = strategy.latest_snapshot if strategy else None
    answer = _opportunity_answer(opportunity, strategy, snapshot)
    title = f"{opportunity.name} ROI, Risk & Evidence | GamCryp"
    description = _truncate_text(answer, 155)
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">{escape(opportunity_type_label(opportunity.opportunity_type))}</p>
          <h1>{escape(opportunity.name)} ROI status and evidence</h1>
          <p class="lede">{escape(answer)}</p>
          <div class="button-row">
            {_destination_button(opportunity.primary_destination, "Open official link")}
          </div>
        </section>
        {_render_opportunity_answer_block(opportunity, strategy, snapshot)}
        {_render_opportunity_human_summary(opportunity, strategy, snapshot)}
        <section class="section-panel">
          <div class="section-header"><h2>Executive Summary</h2></div>
          <div class="section-body metric-grid">
            {_metric("Opportunity type", opportunity_type_label(opportunity.opportunity_type))}
            {_metric("ROI status", value_status_label(opportunity.value_realization_status, opportunity.strategy_count))}
            {_metric("Review state", feasibility_label(opportunity.data_feasibility_status))}
            {_metric("Reward model", ", ".join(opportunity.reward_asset_or_points_type) or "Unspecified")}
          </div>
        </section>
        {_render_strategy_cards(opportunity.strategies)}
        {_render_unavailable_roi(opportunity) if not opportunity.strategies else ""}
        {_render_sources(opportunity)}
        {_render_related_opportunities(opportunity)}
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path=f"/opportunities/{opportunity.opportunity_id}",
        title=title,
        description=description,
        body_html=body,
        json_ld=(
            _webpage_json(settings, f"/opportunities/{opportunity.opportunity_id}", title, description),
            _breadcrumb_json(
                settings,
                [("/", "Home"), ("/opportunities", "Opportunities"), (f"/opportunities/{opportunity.opportunity_id}", opportunity.name)],
            ),
        ),
        lastmod=snapshot.calculated_at if snapshot is not None else _max_opportunity_lastmod([opportunity]),
    )


def game_page(game, *, settings: Settings, request: Request) -> SeoPage:
    first_strategy = game.strategies[0] if game.strategies else None
    snapshot = first_strategy.latest_snapshot if first_strategy else None
    description = (
        _ranking_answer(snapshot, first_strategy)
        if snapshot is not None and first_strategy is not None
        else f"{game.name} is a Games opportunity in the GamCryp catalog."
    )
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Game compatibility page</p>
          <h1>{escape(game.name)} ROI strategies</h1>
          <p class="lede">{escape(description)}</p>
          <div class="button-row">
            {_destination_button(game.primary_destination, cta_label_for_snapshot(snapshot, "Start"))}
            <a class="secondary-button" href="/opportunities/{escape(game.opportunity_id)}">Canonical opportunity</a>
          </div>
        </section>
        {_render_strategy_cards(game.strategies)}
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path=f"/games/{game.game_id}",
        title=f"{game.name} ROI Strategies | GamCryp",
        description=_truncate_text(description, 155),
        body_html=body,
        json_ld=(
            _webpage_json(settings, f"/games/{game.game_id}", f"{game.name} ROI Strategies", description),
            _breadcrumb_json(settings, [("/", "Home"), ("/opportunities", "Opportunities"), (f"/games/{game.game_id}", game.name)]),
        ),
        lastmod=snapshot.calculated_at if snapshot is not None else None,
    )


def strategy_page(
    strategy: StrategySummary,
    history_items: list[StrategySnapshotPayload],
    *,
    settings: Settings,
    request: Request,
) -> SeoPage:
    snapshot = strategy.latest_snapshot
    if snapshot is None:
        answer = f"{strategy.name} has no successful stored calculation yet."
    else:
        answer = _ranking_answer(snapshot, strategy)
    description = _truncate_text(answer, 155)
    body = f"""
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Strategy intelligence</p>
          <h1>{escape(strategy.name)}</h1>
          <p class="lede">{escape(answer)}</p>
          <div class="button-row">
            <a class="secondary-button" href="/opportunities/{escape(strategy.opportunity_id)}">Parent opportunity</a>
            <a class="secondary-button" href="/games/{escape(strategy.game_id)}">Game view</a>
            {_destination_button(strategy.primary_destination, cta_label_for_snapshot(snapshot, "Start"))}
          </div>
          {_render_cta_risk_notice(snapshot)}
        </section>
        {_render_strategy_answer_block(strategy, snapshot)}
        {_render_strategy_human_summary(strategy, snapshot)}
        {_render_snapshot_detail(snapshot) if snapshot is not None else _empty("No stored snapshot", "This strategy has not produced a valid stored calculation yet.")}
        {_render_history_context(history_items)}
        <section class="section-panel">
          <div class="section-header"><h2>Methodology Context</h2></div>
          <div class="section-body">
            <p class="muted">Model version {escape(snapshot.versions.model_version if snapshot else "Unavailable")} and strategy version {escape(strategy.strategy_version)}. ROI is strategy-specific and is calculated from stored snapshots, not from live page requests.</p>
            <p><a class="strategy-link" href="/methodology">Read the GamCryp methodology</a></p>
          </div>
        </section>
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path=f"/strategies/{strategy.strategy_id}",
        title=f"{strategy.name} ROI, Risk & Break-even | GamCryp",
        description=description,
        body_html=body,
        json_ld=(
            _webpage_json(settings, f"/strategies/{strategy.strategy_id}", strategy.name, description),
            _breadcrumb_json(
                settings,
                [("/", "Home"), ("/rankings", "Rankings"), (f"/strategies/{strategy.strategy_id}", strategy.name)],
            ),
        ),
        lastmod=snapshot.calculated_at if snapshot is not None else None,
    )


def methodology_page(*, settings: Settings, request: Request) -> SeoPage:
    description = "GamCryp methodology for strategy-specific ROI, realizable earnings, slippage, total versus at-risk capital, confidence, risk, and unavailable points value."
    body = """
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Methodology</p>
          <h1>How GamCryp reads Web3 opportunity economics</h1>
          <p class="lede">GamCryp publishes strategy-specific economics from stored snapshots, explicit assumptions, and source provenance. It does not imply guaranteed returns or investment advice.</p>
        </section>
        <section class="method-grid">
          <article class="method-item"><h2>Strategy-specific ROI</h2><p class="muted">A game or opportunity does not have one universal ROI. Every result belongs to a named strategy version and model version.</p></article>
          <article class="method-item"><h2>Realizable earnings</h2><p class="muted">Rewards are valued through a modeled sell or realization route where one is lawful and reproducible.</p></article>
          <article class="method-item"><h2>Slippage</h2><p class="muted">Spot prices can overstate sellable value. Quotes or AMM simulations are preferred when available.</p></article>
          <article class="method-item"><h2>Total vs at-risk capital</h2><p class="muted">Total capital is the entry requirement. Capital at risk is the portion economically exposed after recoverable value is considered.</p></article>
          <article class="method-item"><h2>Confidence vs risk</h2><p class="muted">Confidence measures trust in the calculation and data. Risk measures economic downside. They are independent.</p></article>
          <article class="method-item"><h2>LIVE / CONFIG / DERIVED</h2><p class="muted">LIVE values are current observations, CONFIG values are assumptions, and DERIVED values are calculated from inputs.</p></article>
          <article class="method-item"><h2>Unavailable ROI</h2><p class="muted">Points, badges, and future claims do not become zero-dollar ROI. They remain unavailable until value is lawful and reproducible.</p></article>
          <article class="method-item"><h2>Commercial separation</h2><p class="muted">Referral, affiliate, sponsor, and traffic data never changes ROI, Risk, Confidence, or organic rankings.</p></article>
        </section>
      </div>
    """
    return _page(
        request=request,
        settings=settings,
        path="/methodology",
        title="GamCryp ROI Methodology: Risk, Confidence & Realizable Earnings",
        description=description,
        body_html=body,
        json_ld=(
            _webpage_json(settings, "/methodology", "GamCryp ROI Methodology", description),
            _breadcrumb_json(settings, [("/", "Home"), ("/methodology", "Methodology")]),
        ),
    )


def _page(
    *,
    request: Request,
    settings: Settings,
    path: str,
    title: str,
    description: str,
    body_html: str,
    json_ld: tuple[dict, ...],
    lastmod: datetime | None = None,
) -> SeoPage:
    robots = "noindex,follow" if request.url.query else "index,follow"
    return SeoPage(
        path=path,
        title=title,
        description=description,
        body_html=body_html,
        json_ld=json_ld,
        robots=robots,
        lastmod=lastmod,
    )


def record_landing_visit(request: Request, repository: MonetizationRepository, *, path: str) -> None:
    referrer_domain = _referrer_domain(request.headers.get("referer"))
    utm_source = request.query_params.get("utm_source")
    repository.record_landing_visit(
        landing_path=path,
        referrer_domain=referrer_domain,
        utm_source=utm_source,
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        channel=normalize_acquisition_channel(utm_source=utm_source, referrer_domain=referrer_domain),
        coarse_session_id=request.headers.get("x-gamcryp-session"),
    )


def asset_url(path: str) -> str:
    clean = path.split("?", 1)[0]
    relative = clean.removeprefix("/assets/")
    asset_path = FRONTEND_ASSETS / relative
    try:
        digest = hashlib.sha256(asset_path.read_bytes()).hexdigest()[:12]
    except OSError:
        digest = "missing"
    return f"{clean}?v={digest}"


def _ranking_answer(snapshot: StrategySnapshotPayload, strategy: StrategySummary) -> str:
    return (
        f"GamCryp currently models {strategy.name} at {format_ratio_text(snapshot.roi.roi_total_30d)} 30-day ROI "
        f"using {format_money_text(snapshot.capital.total_capital)} capital. Net earnings are "
        f"{format_money_text(snapshot.earnings.net_earnings_day, per_day=True)}. Risk is "
        f"{score_text(snapshot.risk)} and Confidence is {score_text(snapshot.confidence)}. "
        f"Latest modeled snapshot was calculated at {format_datetime(snapshot.calculated_at)}."
    )


def _opportunity_answer(
    opportunity: OpportunityDetail,
    strategy: StrategySummary | None,
    snapshot: StrategySnapshotPayload | None,
) -> str:
    if strategy is not None and snapshot is not None:
        return _ranking_answer(snapshot, strategy)
    return (
        f"ROI for {opportunity.name} is not measurable yet. {plain_unavailable_reason(opportunity)}"
    )


def _rankings_summary(rankings: RankingsPage) -> str:
    if not rankings.items:
        return "No successful stored strategy snapshots currently match this page."
    top = rankings.items[0]
    return _ranking_answer(top.latest_snapshot, top.strategy)


def _render_home_answer_block(rankings: RankingsPage, opportunities: list[OpportunitySummary]) -> str:
    unavailable_count = sum(1 for opportunity in opportunities if opportunity.strategy_count == 0)
    fields = [
        ("Reviewed opportunities", escape(str(len(opportunities)))),
        ("Modeled strategies", escape(str(rankings.page.total))),
        ("Opportunity coverage", escape(", ".join(sorted({opportunity_type_label(item.opportunity_type) for item in opportunities})) or "Unavailable")),
        ("Current top answer", escape(_rankings_summary(rankings))),
        ("Unavailable ROI policy", escape(f"{unavailable_count} opportunities remain unavailable, not zero, until value is reproducible.")),
        ("Data source", "Stored snapshots served through /api/v1; page requests do not call live providers."),
    ]
    return _render_answer_block(
        "Quick overview",
        "GamCryp is a Web3 opportunity intelligence source for modeled ROI, risk, confidence, freshness, and explicit unavailable states.",
        fields,
    )


def _render_rankings_answer_block(
    rankings: RankingsPage,
    title: str,
    filters: dict[str, object] | None = None,
) -> str:
    fields = [
        ("Comparison page", escape(title)),
        ("Matching modeled strategies", escape(str(rankings.page.total))),
        ("Ranking basis", "30D ROI descending, confidence descending, risk ascending, latest calculation descending, then strategy id."),
        ("Filters", escape(_filter_summary(filters))),
        ("Last snapshot update", escape(format_datetime(_rankings_lastmod(rankings)))),
        ("Data source", "Latest successful persisted strategy snapshots from /api/v1/rankings."),
        ("Commercial policy", "Referral, affiliate, and sponsor metadata never changes organic ranking order or analytical scores."),
    ]
    return _render_answer_block(
        "Quick comparison",
        _rankings_summary(rankings),
        fields,
    )


def _render_opportunity_index_answer_block(opportunities: list[OpportunitySummary]) -> str:
    modeled_count = sum(1 for opportunity in opportunities if opportunity.strategy_count > 0)
    unavailable_count = len(opportunities) - modeled_count
    fields = [
        ("Catalog size", escape(str(len(opportunities)))),
        ("Modeled opportunities", escape(str(modeled_count))),
        ("ROI unavailable opportunities", escape(str(unavailable_count))),
        ("Opportunity types", escape(", ".join(sorted({opportunity_type_label(item.opportunity_type) for item in opportunities})) or "Unavailable")),
        ("Financial ROI rule", "Only opportunities with reproducible reward value, costs, timing, and exit route receive ROI."),
        ("Points rule", "Points and future claims are shown as unavailable unless a lawful realizable value route exists."),
    ]
    return _render_answer_block(
        "Quick catalog summary",
        "GamCryp tracks Games, DePIN / Nodes, and Points programs in one opportunity catalog with modeled ROI only where the data supports it.",
        fields,
    )


def _render_opportunity_answer_block(
    opportunity: OpportunityDetail,
    strategy: StrategySummary | None,
    snapshot: StrategySnapshotPayload | None,
) -> str:
    reward_type = ", ".join(opportunity.reward_asset_or_points_type) or "Unspecified"
    if strategy is not None and snapshot is not None:
        fields = _strategy_answer_fields(strategy, snapshot)
        fields.insert(0, ("Opportunity page", escape(opportunity.name)))
        return _render_answer_block("Quick opportunity summary", _ranking_answer(snapshot, strategy), fields)

    fields = [
        ("Opportunity", escape(opportunity.name)),
        ("Opportunity type", escape(opportunity_type_label(opportunity.opportunity_type))),
        ("ROI status", escape(value_status_label(opportunity.value_realization_status, opportunity.strategy_count))),
        ("Review state", escape(feasibility_label(opportunity.data_feasibility_status))),
        ("Reward type", escape(reward_type)),
        ("Value route", escape(plain_unavailable_reason(opportunity))),
        ("Modeled strategies", escape(str(opportunity.strategy_count))),
        ("Reviewed outbound link", escape(_destination_status_text(opportunity.primary_destination))),
        ("Last reviewed", escape(format_datetime(getattr(opportunity.primary_destination, "reviewed_at", None)))),
    ]
    return _render_answer_block("Quick opportunity summary", _opportunity_answer(opportunity, strategy, snapshot), fields)


def _render_strategy_answer_block(strategy: StrategySummary, snapshot: StrategySnapshotPayload | None) -> str:
    if snapshot is None:
        fields = [
            ("Strategy", escape(strategy.name)),
            ("Strategy version", escape(strategy.strategy_version)),
            ("Opportunity", escape(strategy.game_name)),
            ("Opportunity type", escape(opportunity_type_label(strategy.opportunity_type))),
            ("ROI status", "No successful stored calculation yet."),
        ]
        return _render_answer_block("Quick strategy summary", f"{strategy.name} has no successful stored calculation yet.", fields)
    return _render_answer_block("Quick strategy summary", _ranking_answer(snapshot, strategy), _strategy_answer_fields(strategy, snapshot))


def _strategy_answer_fields(strategy: StrategySummary, snapshot: StrategySnapshotPayload) -> list[tuple[str, str]]:
    return [
        ("Opportunity", escape(strategy.game_name)),
        ("Opportunity type", escape(opportunity_type_label(strategy.opportunity_type))),
        ("Strategy", escape(strategy.name)),
        ("Strategy version", escape(strategy.strategy_version)),
        ("Starting capital", format_money_html(snapshot.capital.total_capital)),
        ("Estimated gross earnings/day", format_money_html(snapshot.earnings.gross_nominal_earnings_day, per_day=True)),
        ("Estimated realizable earnings/day", format_money_html(snapshot.earnings.realizable_earnings_day, per_day=True)),
        ("Estimated net earnings/day", format_money_html(snapshot.earnings.net_earnings_day, per_day=True)),
        ("30D ROI", format_ratio_html(snapshot.roi.roi_total_30d)),
        ("Break-even", format_break_even_html(snapshot.roi.break_even)),
        ("Risk", escape(score_text(snapshot.risk))),
        ("Confidence", escape(score_text(snapshot.confidence))),
        ("Data status", escape(labelize(snapshot.freshness.overall_status))),
        ("Snapshot timestamp", escape(format_datetime(snapshot.calculated_at))),
        ("Required time/effort", "Not separately quantified in this strategy snapshot."),
        ("Major assumptions", escape(_major_assumptions(snapshot))),
        ("Warnings", escape(_warning_summary(snapshot.warnings))),
        ("Financial data source", "Latest successful persisted snapshot; no live provider call during page view."),
    ]


def _render_answer_block(title: str, summary: str, fields: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<div class="answer-item"><dt>{escape(label)}</dt><dd>{value}</dd></div>'
        for label, value in fields
    )
    return f"""
      <section class="answer-card" data-ai-answer-block="true">
        <div class="section-header"><h2>{escape(title)}</h2><span class="badge info">Source-ready</span></div>
        <div class="section-body">
          <p class="answer-summary">{escape(summary)}</p>
          <dl class="answer-grid">{items}</dl>
        </div>
      </section>
    """


def _render_human_summary(title: str, items: list[tuple[str, str]]) -> str:
    rendered = "".join(
        f'<article class="human-line"><span>{escape(label)}</span><p>{value}</p></article>'
        for label, value in items
    )
    return f"""
      <section class="section-panel human-summary">
        <div class="section-header"><h2>{escape(title)}</h2></div>
        <div class="section-body human-summary-grid">{rendered}</div>
      </section>
    """


def _render_opportunity_human_summary(
    opportunity: OpportunityDetail,
    strategy: StrategySummary | None,
    snapshot: StrategySnapshotPayload | None,
) -> str:
    access = human_list([*opportunity.platforms, *opportunity.chains], "Check the official project page for access requirements")
    reward_types = human_list(opportunity.reward_asset_or_points_type, "Reward type not specified yet")
    modeled = strategy is not None and snapshot is not None
    unavailable = plain_unavailable_reason(opportunity)
    items = [
        ("What it is", escape(f"{opportunity.name} is tracked as {opportunity_type_label(opportunity.opportunity_type).lower()}.")),
        ("How it may earn", escape(reward_types)),
        ("What you need", escape(access)),
        (
            "Cost and return",
            f"Modeled in {escape(strategy.name)}; open the strategy for current capital, costs, and ROI."
            if modeled and strategy is not None
            else escape(unavailable),
        ),
        (
            "Cash-out",
            "Realizable value is modeled inside the strategy snapshot where market data supports it."
            if modeled
            else escape(unavailable),
        ),
        (
            "Main catch",
            escape("Review risk, confidence, and freshness before acting." if opportunity.data_feasibility_status == "GO" else unavailable),
        ),
    ]
    return _render_human_summary("Plain-language summary", items)


def _render_strategy_human_summary(strategy: StrategySummary, snapshot: StrategySnapshotPayload | None) -> str:
    if snapshot is None:
        return ""
    items = [
        ("What it is", escape(f"{strategy.name} is a modeled strategy for {strategy.game_name}.")),
        ("How it may earn", escape(f"{labelize(strategy.economy_type)} economics are converted into the generic ROI model.")),
        ("What you need", f"Estimated starting capital is {format_money_html(snapshot.capital.total_capital)}."),
        (
            "Expected return",
            f"{format_money_html(snapshot.earnings.net_earnings_day, per_day=True)} estimated net earnings and {format_ratio_html(snapshot.roi.roi_total_30d)} modeled 30-day ROI.",
        ),
        (
            "Cash-out",
            f"Recoverable value is {format_money_html(snapshot.capital.recoverable_capital)}; exit-adjusted P&amp;L is {format_money_html(snapshot.roi.exit_adjusted_pnl)}.",
        ),
        ("Main catch", escape(strategy_risk_summary(snapshot))),
    ]
    return _render_human_summary("Plain-language summary", items)

def _filter_summary(filters: dict[str, object] | None) -> str:
    if not filters:
        return "No additional filters."
    parts = []
    for key, value in filters.items():
        if key == "opportunity_type":
            parts.append(f"Opportunity type: {opportunity_type_label(str(value))}")
        elif key == "capital_max":
            parts.append(f"Capital up to ${_trim_decimal(Decimal(str(value)))}")
        elif key == "capital_min":
            parts.append(f"Capital at least ${_trim_decimal(Decimal(str(value)))}")
        elif key == "confidence_min":
            parts.append(f"Confidence at least {value}")
        elif key == "risk_max":
            parts.append(f"Risk up to {value}")
        else:
            parts.append(f"{labelize(key)}: {value}")
    return "; ".join(parts)


def _major_assumptions(snapshot: StrategySnapshotPayload) -> str:
    counts = snapshot.classification_summary.counts
    live = counts.get("LIVE", 0)
    config = counts.get("CONFIG", 0)
    derived = counts.get("DERIVED", 0)
    return f"{live} live observations, {config} configured assumptions, and {derived} derived metrics are attached to this snapshot."


def _warning_summary(warnings) -> str:
    if not warnings:
        return "No warnings attached."
    return " ".join(warning.message for warning in warnings[:2])


def _destination_status_text(destination) -> str:
    if destination is None:
        return "No reviewed outbound destination."
    return f"{destination.label}; {destination.verification_status}; reviewed {format_datetime(destination.reviewed_at)}."


def _render_ranking_cards(items: list[RankingItem], *, heading: str) -> str:
    if not items:
        return _empty("No current matches", "No successful stored strategy snapshot currently matches this view.")
    cards = []
    for item in items:
        snapshot = item.latest_snapshot
        strategy = item.strategy
        cards.append(
            f"""
            <article class="ranking-card">
              <div class="ranking-card-head">
                <span class="rank-chip">#{escape(str(item.rank))}</span>
                <div>
                  <a class="game-link" href="/games/{escape(strategy.game_id)}">{escape(snapshot.game_name)}</a>
                  <h3><a class="strategy-link" href="/strategies/{escape(strategy.strategy_id)}">{escape(strategy.name)}</a></h3>
                  <p class="muted">{escape(strategy.strategy_version)} | {escape(labelize(strategy.economy_type))}</p>
                </div>
              </div>
              <p>{escape(_ranking_answer(snapshot, strategy))}</p>
              <div class="card-metrics">
                {_metric("Estimated starting capital", format_money_html(snapshot.capital.total_capital))}
                {_metric("Estimated net/day", format_money_html(snapshot.earnings.net_earnings_day, per_day=True))}
                {_metric("30-day modeled ROI", format_ratio_html(snapshot.roi.roi_total_30d))}
                {_metric("Current break-even", format_break_even_html(snapshot.roi.break_even))}
              </div>
              <div class="card-badges">
                {_badge(f"Confidence {score_text(snapshot.confidence)}", score_class(snapshot.confidence, "confidence"))}
                {_badge(f"Risk {score_text(snapshot.risk)}", score_class(snapshot.risk, "risk"))}
                {_badge(f"Updated {format_datetime(snapshot.calculated_at)}", "info")}
              </div>
              {_render_cta_risk_notice(snapshot)}
              <div class="card-actions">
                <a class="secondary-button" href="/strategies/{escape(strategy.strategy_id)}">View strategy</a>
                {_destination_button(strategy.primary_destination, cta_label_for_snapshot(snapshot, "Start"))}
              </div>
            </article>
            """
        )
    return f"""
      <section class="section-panel ranking-section">
        <div class="section-header"><h2>{escape(heading)}</h2><span class="badge info">{len(items)} visible</span></div>
        <div class="ranking-card-grid">{''.join(cards)}</div>
      </section>
    """


def _render_opportunity_cards(opportunities: list[OpportunitySummary], *, heading: str) -> str:
    cards = []
    for opportunity in opportunities:
        roi_text = "Review the modeled strategy for current assumptions." if opportunity.strategy_count else plain_unavailable_reason(opportunity)
        cards.append(
            f"""
            <article class="opportunity-card">
              <div class="identity-row">
                {_badge(opportunity_type_label(opportunity.opportunity_type), "info")}
                {_badge(feasibility_label(opportunity.data_feasibility_status), "good" if opportunity.data_feasibility_status == "GO" else "medium")}
              </div>
              <h3><a class="strategy-link" href="/opportunities/{escape(opportunity.opportunity_id)}">{escape(opportunity.name)}</a></h3>
              <p class="muted">{escape(opportunity_intro(opportunity))}</p>
              <p class="muted">{escape(roi_text)}</p>
              <div class="opportunity-facts">
                {_metric("Reward type", escape(", ".join(opportunity.reward_asset_or_points_type) or "Unspecified"))}
                {_metric("Can ROI be measured?", value_status_label(opportunity.value_realization_status, opportunity.strategy_count))}
              </div>
              <div class="card-actions">
                <a class="secondary-button" href="/opportunities/{escape(opportunity.opportunity_id)}">Learn more</a>
                {_destination_button(opportunity.primary_destination, "Open")}
              </div>
            </article>
            """
        )
    return f"""
      <section class="section-panel opportunity-section">
        <div class="section-header"><h2>{escape(heading)}</h2><span class="badge info">{len(opportunities)} reviewed</span></div>
        <div class="opportunity-grid">{''.join(cards)}</div>
      </section>
    """


def _render_catalog_stats(rankings: RankingsPage, opportunities: list[OpportunitySummary]) -> str:
    opportunity_count = len(opportunities)
    modeled_count = rankings.page.total
    unavailable_count = sum(1 for opportunity in opportunities if opportunity.strategy_count == 0)
    opportunity_types = ", ".join(
        sorted({opportunity_type_label(opportunity.opportunity_type) for opportunity in opportunities})
    )
    return f"""
      <section class="catalog-stat-grid" aria-label="GamCryp V1 coverage">
        {_summary("Reviewed opportunities", escape(str(opportunity_count)))}
        {_summary("Modeled strategies", escape(str(modeled_count)))}
        {_summary("Opportunity types", escape(opportunity_types))}
        {_summary("ROI not measured", escape(f"{unavailable_count} explicit"))}
      </section>
    """


def _render_strategy_cards(strategies: list[StrategySummary]) -> str:
    if not strategies:
        return _empty("ROI not measurable yet", "No modeled strategy is currently available for this opportunity.")
    items = [
        RankingItem(rank=index + 1, strategy=strategy, latest_snapshot=strategy.latest_snapshot)
        for index, strategy in enumerate(strategies)
        if strategy.latest_snapshot is not None
    ]
    return _render_ranking_cards(items, heading="Modeled strategies")


def _render_snapshot_detail(snapshot: StrategySnapshotPayload) -> str:
    warnings = " ".join(warning.message for warning in snapshot.warnings) or "No strategy warnings are attached."
    confidence_reason = snapshot.confidence.contributions[0].reason if snapshot.confidence.contributions else "No confidence contribution detail recorded."
    risk_reason = snapshot.risk.contributions[0].reason if snapshot.risk.contributions else "No risk contribution detail recorded."
    return f"""
      <section class="summary-grid" aria-label="Strategy summary">
        {_summary("Estimated starting capital", format_money_html(snapshot.capital.total_capital))}
        {_summary("Estimated net/day", format_money_html(snapshot.earnings.net_earnings_day, per_day=True))}
        {_summary("30-day modeled ROI", format_ratio_html(snapshot.roi.roi_total_30d))}
        {_summary("Current break-even", format_break_even_html(snapshot.roi.break_even))}
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Risk and Confidence</h2></div>
        <div class="section-body metric-grid">
          {_metric("Risk", score_text(snapshot.risk))}
          {_metric("Risk explanation", escape(risk_reason))}
          {_metric("Confidence", score_text(snapshot.confidence))}
          {_metric("Confidence explanation", escape(confidence_reason))}
          {_metric("Warnings", escape(warnings))}
        </div>
      </section>
      <details class="advanced-panel snapshot-advanced">
        <summary>Technical snapshot details</summary>
        <div class="advanced-panel-body">
          <section class="section-panel">
            <div class="section-header"><h2>Versions</h2></div>
            <div class="section-body metric-grid">
              {_metric("Strategy ID", escape(snapshot.strategy_id))}
              {_metric("Adapter contract", escape(snapshot.versions.adapter_contract_version))}
              {_metric("ROI model", escape(snapshot.versions.model_version))}
              {_metric("Scoring methodology", escape(snapshot.versions.scoring_methodology_version or "Unavailable"))}
              {_metric("Last calculated", escape(format_datetime(snapshot.calculated_at)))}
            </div>
          </section>
          <section class="section-panel">
            <div class="section-header"><h2>LIVE / CONFIG / DERIVED</h2></div>
            <div class="section-body metric-grid">
              {_metric("LIVE", escape(str(snapshot.classification_summary.counts.get("LIVE", 0))))}
              {_metric("CONFIG", escape(str(snapshot.classification_summary.counts.get("CONFIG", 0))))}
              {_metric("DERIVED", escape(str(snapshot.classification_summary.counts.get("DERIVED", 0))))}
            </div>
          </section>
        </div>
      </details>
    """


def _render_history_context(history_items: list[StrategySnapshotPayload]) -> str:
    if len(history_items) < 2:
        return _empty("Historical context", "Insufficient history for a trend view. At least two stored snapshots are needed.")
    latest = history_items[-1]
    previous = history_items[-2]
    body = f"""
      <div class="section-body metric-grid">
        {_metric("Latest snapshot", format_datetime(latest.calculated_at))}
        {_metric("Previous snapshot", format_datetime(previous.calculated_at))}
        {_metric("Latest 30D ROI", format_ratio_html(latest.roi.roi_total_30d))}
        {_metric("Previous 30D ROI", format_ratio_html(previous.roi.roi_total_30d))}
      </div>
    """
    return f'<section class="section-panel"><div class="section-header"><h2>Historical context</h2></div>{body}</section>'


def _render_unavailable_roi(opportunity: OpportunityDetail) -> str:
    return _empty("Why ROI is unavailable", _unavailable_reason(opportunity))


def _render_sources(opportunity: OpportunityDetail) -> str:
    references = "".join(
        f'<article class="contributor"><strong>{escape(source.label)}</strong><a href="{escape(source.url)}" target="_blank" rel="noopener noreferrer">{escape(source.url)}</a></article>'
        for source in opportunity.official_source_references
    )
    destinations = "".join(
        f'<article class="contributor"><strong>{escape(destination.label)}</strong><span>{escape(destination.disclosure_text)}</span><small>{escape(destination.verification_status)} | reviewed {format_datetime(destination.reviewed_at)}</small></article>'
        for destination in opportunity.outbound_destinations
    )
    return f"""
      <section class="section-panel">
        <div class="section-header"><h2>Sources / Evidence</h2></div>
        <div class="section-body contributor-list">{references}{destinations}</div>
      </section>
    """


def _render_related_opportunities(opportunity: OpportunityDetail) -> str:
    links = [
        '<a class="secondary-button" href="/opportunities">All opportunities</a>',
        '<a class="secondary-button" href="/rankings">Organic rankings</a>',
        '<a class="secondary-button" href="/methodology">Methodology</a>',
    ]
    if opportunity.legacy_game_id:
        links.append(f'<a class="secondary-button" href="/games/{escape(opportunity.legacy_game_id)}">Game compatibility page</a>')
    return f'<section class="section-panel"><div class="section-header"><h2>Related pages</h2></div><div class="section-body button-row">{"".join(links)}</div></section>'


def _render_curated_links(service: ApiDataService) -> str:
    links = "".join(
        f'<a class="secondary-button" href="{escape(page.path)}">{escape(page.title)}</a>'
        for page in published_curated_ranking_pages(service)
    )
    return f'<section class="section-panel"><div class="section-header"><h2>Curated views</h2></div><div class="section-body button-row">{links}</div></section>'


def _empty(title: str, body: str) -> str:
    return f'<section class="empty-state"><h2>{escape(title)}</h2><p class="muted">{escape(body)}</p></section>'


def _destination_button(destination, label: str) -> str:
    if destination is None or destination.status != "active":
        return '<span class="badge">No reviewed link</span>'
    relationship = destination_relationship_label(destination)
    relationship_html = f"<span>{escape(relationship)}</span>" if relationship else ""
    return f'<a class="button cta" href="{escape(destination.redirect_url)}" target="_blank" rel="noopener noreferrer"{analytics_attributes(destination)}>{escape(label)}{relationship_html}</a>'


def _render_cta_risk_notice(snapshot) -> str:
    if not is_elevated_risk(snapshot):
        return ""
    return '<p class="cta-risk-note">High-risk strategy. Opening the project is not a recommendation; review the assumptions first.</p>'

def _summary(label: str, value: str) -> str:
    return f'<div class="summary-item"><span>{escape(label)}</span><strong>{value}</strong></div>'


def _metric(label: str, value: str) -> str:
    return f'<div class="metric-item"><span>{escape(label)}</span><strong>{value}</strong></div>'


def _badge(label: str, class_name: str = "") -> str:
    return f'<span class="badge {escape(class_name)}">{escape(label)}</span>'


def format_money_html(money, *, per_day: bool = False) -> str:
    return f'<span class="money" title="{escape(money.amount)} {escape(money.currency)}">{escape(format_money_text(money, per_day=per_day))}</span>'


def format_money_text(money, *, per_day: bool = False) -> str:
    suffix = "/day" if per_day else ""
    try:
        amount = Decimal(str(money.amount))
    except (InvalidOperation, TypeError):
        return "Unavailable"
    if money.currency == "USD":
        sign = "-" if amount < 0 else ""
        absolute = abs(amount)
        if absolute != 0 and absolute < Decimal("0.0001"):
            return f"{'loss ' if amount < 0 else ''}< $0.0001{suffix}"
        decimals = Decimal("0.0001") if absolute < Decimal("0.01") and absolute != 0 else Decimal("0.01")
        rounded = absolute.quantize(decimals, rounding=ROUND_HALF_UP)
        return f"{sign}${_trim_decimal(rounded)}{suffix}"
    return f"{_trim_decimal(amount.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))} {money.currency}{suffix}"


def format_ratio_html(metric) -> str:
    return f'<span class="ratio" title="Exact ratio: {escape(str(metric.value))}">{escape(format_ratio_text(metric))}</span>'


def format_ratio_text(metric) -> str:
    if metric is None or metric.value is None:
        return metric.reason if metric and metric.reason else "Unavailable"
    value = Decimal(str(metric.value)) * Decimal("100")
    return f"{_trim_decimal(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}%"


def format_break_even_html(metric) -> str:
    if metric.days is None:
        reason = metric.reason or "Unavailable"
        label = "Not profitable" if "positive net earnings" in reason.lower() else reason
        return f'<span class="muted" title="{escape(reason)}">{escape(label)}</span>'
    days = Decimal(str(metric.days)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f'<span class="break-even" title="Exact days: {escape(str(metric.days))}">{int(days):,} days</span>'


def score_text(score) -> str:
    if not score.available:
        return "Unavailable"
    return f"{score.score} {labelize(score.label)}"


def score_class(score, kind: str) -> str:
    if not score.available:
        return ""
    label = str(score.label or "").lower().replace(" ", "-")
    if kind == "confidence":
        return "good" if label == "high" else "medium" if label == "moderate" else "low-confidence"
    return "good" if label == "low" else "medium" if label == "medium" else label


def is_elevated_risk(snapshot) -> bool:
    if not snapshot or not hasattr(snapshot, "risk") or not snapshot.risk.available:
        return False
    label = str(snapshot.risk.label or "").upper()
    return label in ["HIGH", "VERY HIGH"]


def cta_label_for_snapshot(snapshot, fallback: str = "Start") -> str:
    return "Open project" if is_elevated_risk(snapshot) else fallback


def strategy_risk_summary(snapshot) -> str:
    if not snapshot:
        return "No snapshot available for risk assessment."
    if hasattr(snapshot, "freshness") and hasattr(snapshot.freshness, "overall_status"):
        if snapshot.freshness.overall_status and snapshot.freshness.overall_status != "fresh":
            return "The latest stored data is stale, so treat the result as outdated until a fresh snapshot appears."
    if is_elevated_risk(snapshot):
        return "Elevated risk: this CTA opens the project, not a recommendation to start."
    if hasattr(snapshot, "confidence") and snapshot.confidence.available:
        if snapshot.confidence.label == "LOW":
            return "Low confidence means the calculation depends on weaker or incomplete evidence."
    if hasattr(snapshot, "warnings") and snapshot.warnings:
        return snapshot.warnings[0].message
    return "No critical warning is attached, but ROI is still an estimate rather than a promise."


def human_list(values: list[str] | None, fallback: str) -> str:
    if not values:
        return fallback
    labels = [labelize(value) for value in values if value]
    return ", ".join(labels) if labels else fallback


def format_datetime(value: datetime | str | None) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, str):
        parsed = _parse_datetime(value)
        if parsed is not None:
            return _format_datetime_utc(parsed)
        return _strip_timestamp_noise(value)
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return _format_datetime_utc(value)


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_datetime_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    utc_value = value.astimezone(UTC)
    return f"{MONTH_NAMES[utc_value.month]} {utc_value.day}, {utc_value.year} {utc_value:%H:%M} UTC"


def _strip_timestamp_noise(value: str) -> str:
    text = str(value).replace("T", " ").replace("Z", " UTC")
    suffix = " UTC" if "+00:00" in text or " UTC" in text else ""
    text = text.replace("+00:00", "")
    if "." in text:
        text = text.split(".", 1)[0]
    return f"{text}{suffix}".replace(":00 UTC", " UTC")


def labelize(value: str) -> str:
    return str(value).replace("_", " ").replace("-", " ").title()


def _unavailable_reason(opportunity) -> str:
    return plain_unavailable_reason(opportunity)


def _rankings_lastmod(rankings: RankingsPage) -> datetime | None:
    if not rankings.items:
        return None
    return max(item.latest_snapshot.calculated_at for item in rankings.items)


def _max_opportunity_lastmod(opportunities) -> datetime:
    dates = []
    for opportunity in opportunities:
        destination = getattr(opportunity, "primary_destination", None)
        if destination is not None:
            dates.append(destination.reviewed_at)
    return max(dates, default=CATALOG_REVIEWED_AT)


def _truncate_text(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _trim_decimal(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _referrer_domain(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    return parsed.netloc.lower() or None


def _verification_meta(settings: Settings) -> str:
    parts = []
    if settings.google_site_verification:
        parts.append(f'<meta name="google-site-verification" content="{escape(settings.google_site_verification)}">')
    if settings.bing_site_verification:
        parts.append(f'<meta name="msvalidate.01" content="{escape(settings.bing_site_verification)}">')
    return "\n    ".join(parts)


def _public_config_script(settings: Settings) -> str:
    payload = {
        "gaMeasurementId": settings.ga_measurement_id,
        "posthogProjectApiKey": settings.posthog_project_api_key,
        "posthogHost": settings.posthog_host,
        "sentryFrontendDsn": settings.sentry_frontend_dsn,
        "sentryEnvironment": settings.sentry_environment or settings.environment,
        "sentryRelease": settings.sentry_release,
        "sentryTracesSampleRate": settings.sentry_traces_sample_rate,
        "xUrl": settings.public_x_url or "https://x.com/GamCryp",
        "youtubeUrl": settings.public_youtube_url,
        "contactEmail": settings.public_contact_email,
    }
    return f"<script>window.GAMCRYP_PUBLIC_CONFIG = {_json_ld(payload)};</script>"


def _footer_html(settings: Settings) -> str:
    x_url = settings.public_x_url or "https://x.com/GamCryp"
    x_link = f'<a href="{escape(x_url)}" rel="noopener noreferrer" target="_blank">X</a>'
    return f"""
    <footer class="site-footer">
      <nav class="footer-links" aria-label="Brand links">
        <span>GamCryp</span>
        {x_link}
        <a href="{escape(settings.public_youtube_url)}" rel="noopener noreferrer" target="_blank">YouTube</a>
        <a href="mailto:{escape(settings.public_contact_email)}">{escape(settings.public_contact_email)}</a>
        <a href="/methodology" data-link>Methodology</a>
      </nav>
      <p>Analytics only. No guaranteed returns. Not investment advice. Commercial relationships never affect ROI, Risk, Confidence, or organic rankings.</p>
    </footer>
    """


def _json_ld(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def opportunity_type_label(value: str) -> str:
    normalized = str(value or "").upper()
    if normalized == "GAME":
        return "Games"
    if normalized == "DEPIN_NODE":
        return "DePIN / Nodes"
    if normalized == "POINTS":
        return "Points programs"
    return labelize(value or "Opportunity")


def opportunity_type_description(value: str) -> str:
    normalized = str(value or "").upper()
    if normalized == "GAME":
        return "Earn through blockchain game economies where rewards and exits can be reviewed."
    if normalized == "DEPIN_NODE":
        return "Earn rewards by running software or providing network, compute, storage, bandwidth, or similar resources."
    if normalized == "POINTS":
        return "Earn points now; cash or token value may not exist yet."
    return "A reviewed Web3 earning opportunity."


def opportunity_intro(opportunity) -> str:
    reward_types = ", ".join(opportunity.reward_asset_or_points_type)
    reward_text = f" Rewards tracked: {reward_types}." if reward_types else ""
    feasibility_summary = getattr(opportunity, "feasibility_summary", "")
    summary = f" {feasibility_summary}" if feasibility_summary else ""
    return f"{opportunity_type_description(opportunity.opportunity_type)}{reward_text}{summary}".strip()


def value_status_label(status: str, strategy_count: int) -> str:
    if str(status or "").lower() == "realizable" and strategy_count > 0:
        return "ROI can be measured"
    return "ROI not measurable yet"


def feasibility_label(status: str) -> str:
    normalized = str(status or "").upper()
    if normalized == "GO":
        return "Ready"
    if normalized == "PARTIAL":
        return "Research"
    if normalized == "PARKED":
        return "Watchlist"
    if normalized == "REJECTED":
        return "Not modelable"
    return "Under review"


def plain_unavailable_reason(opportunity) -> str:
    value_status = str(opportunity.value_realization_status or "").lower()
    feasibility = str(opportunity.data_feasibility_status or "").upper()
    summary = str(getattr(opportunity, "feasibility_summary", "") or "").lower()
    if "non_transferable_points" in value_status or "points are not" in summary or "no monetary value" in summary:
        return "Points cannot currently be converted to cash reliably."
    if "future_airdrop" in value_status or "future" in summary or "airdrop" in summary:
        return "Reward value is not yet verifiable."
    if feasibility == "REJECTED" or "unknown" in value_status or "exit" in summary or "realizable value" in summary:
        return "A reproducible exit value is not available yet."
    return "Reward has no reliable market price yet."


def destination_relationship_label(destination) -> str:
    if getattr(destination, "is_affiliate", False):
        return "Affiliate"
    relationship = str(getattr(destination, "commercial_relationship", "") or "").lower()
    if relationship in {"", "none", "official"}:
        return ""
    return labelize(relationship)


def analytics_attributes(destination) -> str:
    target_url_kind = getattr(destination, "target_url_kind", None)
    if not target_url_kind:
        referral_status = str(getattr(destination, "referral_status", "") or "").upper()
        target_url_kind = "referral" if getattr(destination, "referral_url", None) and referral_status == "ACTIVE" else "official"
    attributes = {
        "data-analytics-link": "outbound",
        "data-destination-slug": destination.destination_slug,
        "data-opportunity-id": destination.opportunity_id,
        "data-strategy-id": getattr(destination, "strategy_id", None),
        "data-opportunity-type": opportunity_type_label(destination.opportunity_type),
        "data-placement": "server_rendered_cta",
        "data-source-page": "server_rendered",
        "data-target-url-kind": target_url_kind,
        "data-referral-status": str(getattr(destination, "referral_status", "") or "none").lower(),
        "data-commercial-relationship": getattr(destination, "commercial_relationship", "none"),
        "data-is-affiliate": "true" if getattr(destination, "is_affiliate", False) else "false",
    }
    return "".join(
        f' {key}="{escape(str(value))}"'
        for key, value in attributes.items()
        if value is not None and str(value).strip()
    )


def _organization_json(settings: Settings) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f"{settings.public_base_url}/#organization",
        "name": "GamCryp",
        "url": settings.public_base_url,
        "logo": canonical_url(settings, "/assets/brand/gamcryp-logo.png"),
    }


def _website_json(settings: Settings) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f"{settings.public_base_url}/#website",
        "name": "GamCryp",
        "url": settings.public_base_url,
        "publisher": {"@id": f"{settings.public_base_url}/#organization"},
    }


def _ranking_json_ld(
    settings: Settings,
    path: str,
    name: str,
    description: str,
    items: list[RankingItem],
    breadcrumbs: list[tuple[str, str]],
) -> tuple[dict, ...]:
    payloads = (
        _webpage_json(settings, path, name, description),
        _breadcrumb_json(settings, breadcrumbs),
    )
    if items:
        payloads += (_itemlist_json(settings, path, name, items),)
    return payloads


def _itemlist_json(settings: Settings, path: str, name: str, items: list[RankingItem]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": f"{canonical_url(settings, path)}#itemlist",
        "name": name,
        "url": canonical_url(settings, path),
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "numberOfItems": len(items),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": item.strategy.name,
                "url": canonical_url(settings, f"/strategies/{item.strategy.strategy_id}"),
            }
            for index, item in enumerate(items)
        ],
    }

def _webpage_json(settings: Settings, path: str, name: str, description: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{canonical_url(settings, path)}#webpage",
        "url": canonical_url(settings, path),
        "name": name,
        "description": description,
        "isPartOf": {"@id": f"{settings.public_base_url}/#website"},
    }


def _breadcrumb_json(settings: Settings, items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": name,
                "item": canonical_url(settings, path),
            }
            for index, (path, name) in enumerate(items)
        ],
    }
