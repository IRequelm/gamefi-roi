"""Routes for public web pages, static assets, and outbound redirects."""

from __future__ import annotations

import logging
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.staticfiles import StaticFiles

from app.api.dependencies import get_database_engine
from app.api.v1.service import ApiDataService
from app.config.settings import Settings, get_settings
from app.monetization.referral_operations import (
    ReferralValidationError,
    destination_with_operator_referral,
    program_for_destination,
)
from app.observability import posthog as product_analytics
from app.search.canonical import (
    canonical_page_inventory,
    canonical_url,
    curated_rankings_for_page,
    get_curated_ranking_page,
    is_curated_ranking_page_publishable,
    lastmod_date,
)
from app.storage.monetization import MonetizationRepository
from app.strategies.catalog import get_outbound_destination
from app.web.seo import (
    curated_rankings_page,
    game_page,
    home_page,
    methodology_page,
    opportunities_page,
    opportunity_page,
    rankings_page,
    record_landing_visit,
    render_document,
    strategy_page,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
FRONTEND_ASSETS = FRONTEND_ROOT / "assets"

router = APIRouter(include_in_schema=False)
logger = logging.getLogger(__name__)


def frontend_assets() -> StaticFiles:
    return StaticFiles(directory=FRONTEND_ASSETS)


@router.get("/")
def serve_home(
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = ApiDataService(engine)
    page = home_page(service, settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/rankings")
def serve_rankings(
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = ApiDataService(engine)
    page = rankings_page(service, settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/rankings/{landing_slug}")
def serve_curated_rankings(
    landing_slug: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    landing = get_curated_ranking_page(landing_slug)
    if landing is None:
        raise HTTPException(status_code=404, detail=f"Unknown ranking landing page: {landing_slug}")
    service = ApiDataService(engine)
    rankings = curated_rankings_for_page(service, landing)
    if not is_curated_ranking_page_publishable(landing, rankings):
        raise HTTPException(status_code=404, detail=f"Ranking landing page is not publishable yet: {landing_slug}")
    page = curated_rankings_page(service, settings=settings, request=request, landing=landing, rankings=rankings)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/opportunities")
def serve_opportunities(
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = ApiDataService(engine)
    page = opportunities_page(service, settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/opportunities/{opportunity_id}")
def serve_opportunity_detail(
    opportunity_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = ApiDataService(engine)
    opportunity = service.opportunity_detail(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail=f"Unknown opportunity_id: {opportunity_id}")
    page = opportunity_page(opportunity, settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/games/{game_id}")
def serve_game_detail(
    game_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = ApiDataService(engine)
    game = service.game_detail(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Unknown game_id: {game_id}")
    page = game_page(game, settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/strategies/{strategy_id}")
def serve_strategy_detail(
    strategy_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = ApiDataService(engine)
    strategy = service.strategy_detail(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Unknown strategy_id: {strategy_id}")
    history = service.history_page(strategy_id, limit=50, offset=0)
    history_items = [] if history is None else history.items
    page = strategy_page(strategy, history_items, settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/methodology")
def serve_methodology(
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    page = methodology_page(settings=settings, request=request)
    return _html_response(page, request=request, settings=settings, engine=engine)


@router.get("/robots.txt")
def robots_txt(settings: Settings = Depends(get_settings)) -> PlainTextResponse:
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /go/",
        "Disallow: /operator/",
        "Disallow: /admin/",
        "Disallow: /internal/",
        "Disallow: /debug/",
        "Disallow: /test/",
        "Disallow: /*?*",
        "",
        "# OAI-SearchBot is intentionally allowed for ChatGPT search discovery.",
        "# GPTBot is not separately blocked here; change this policy explicitly if training crawl opt-out is desired.",
        "# ChatGPT-User is user-triggered and not used for automatic search indexing control.",
        f"Sitemap: {canonical_url(settings, '/sitemap.xml')}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap.xml")
def sitemap_xml(
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> Response:
    entries = []
    for page in canonical_page_inventory(engine):
        entries.append(
            "  <url>"
            f"<loc>{escape(page.absolute_url(settings), quote=False)}</loc>"
            f"<lastmod>{lastmod_date(page.lastmod)}</lastmod>"
            f"<changefreq>{escape(page.changefreq)}</changefreq>"
            f"<priority>{escape(page.priority)}</priority>"
            "</url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=300"})


@router.get("/{indexnow_key}.txt")
def indexnow_key_file(indexnow_key: str, settings: Settings = Depends(get_settings)) -> PlainTextResponse:
    if not settings.indexnow_key or indexnow_key != settings.indexnow_key:
        raise HTTPException(status_code=404, detail="IndexNow key file not configured.")
    return PlainTextResponse(settings.indexnow_key, headers={"Cache-Control": "public, max-age=300"})


@router.get("/go/{destination_slug}")
def outbound_redirect(
    destination_slug: str,
    request: Request,
    engine: Engine = Depends(get_database_engine),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    destination = get_outbound_destination(destination_slug)
    if destination is None or not destination.is_active() or "redirect" not in destination.allowed_surfaces:
        raise HTTPException(status_code=404, detail="Unknown or inactive outbound destination.")

    repository = MonetizationRepository(engine)
    try:
        destination = destination_with_operator_referral(
            destination,
            program_for_destination(repository, destination.destination_slug),
        )
    except ReferralValidationError as exc:
        logger.warning(
            "operator_referral_overlay_invalid_official_fallback",
            extra={"destination_slug": destination_slug, "error": str(exc)},
        )

    target_url = destination.target_url
    parsed = urlsplit(target_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=404, detail="Outbound destination is not reviewed for redirect.")

    click_event_id = None
    coarse_session_id = request.headers.get("x-gamcryp-session")
    try:
        click = repository.record_outbound_click(
            destination=destination,
            target_url_kind=destination.target_url_kind,
            source_page=request.query_params.get("source_page"),
            placement=request.query_params.get("placement"),
            coarse_session_id=coarse_session_id,
            user_agent_category=_user_agent_category(request.headers.get("user-agent", "")),
        )
        click_event_id = click.event_id
    except SQLAlchemyError as exc:
        logger.warning(
            "outbound_click_persistence_failed",
            extra={"destination_slug": destination.destination_slug, "error": str(exc)},
        )

    _track_outbound_product_analytics(
        settings=settings,
        destination=destination,
        distinct_id=product_analytics.distinct_id_for_outbound_click(coarse_session_id, click_event_id),
        source_page=request.query_params.get("source_page"),
        placement=request.query_params.get("placement"),
    )

    logger.info(
        "outbound_redirect",
        extra={
            "destination_slug": destination.destination_slug,
            "opportunity_id": destination.opportunity_id,
            "opportunity_type": destination.opportunity_type,
            "commercial_relationship": destination.commercial_relationship,
            "is_affiliate": destination.is_affiliate,
        },
    )
    return RedirectResponse(
        target_url,
        status_code=302,
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"},
    )


def _track_outbound_product_analytics(
    *,
    settings: Settings,
    destination,
    distinct_id: str,
    source_page: str | None,
    placement: str | None,
) -> None:
    properties = {
        "destination_slug": destination.destination_slug,
        "opportunity_id": destination.opportunity_id,
        "opportunity_slug": destination.opportunity_id,
        "opportunity_type": destination.opportunity_type,
        "strategy_id": destination.strategy_id,
        "strategy_slug": destination.strategy_id,
        "target_url_kind": destination.target_url_kind,
        "referral_status": destination.referral_status,
        "commercial_relationship": destination.commercial_relationship,
        "is_affiliate": destination.is_affiliate,
        "source_page": source_page,
        "placement": placement,
        "page_path": f"/go/{destination.destination_slug}",
    }
    event_names = ["outbound_go_click"]
    event_names.append("referral_outbound_click" if destination.target_url_kind == "referral" else "official_fallback_outbound_click")
    for event_name in event_names:
        try:
            product_analytics.track_product_event(
                settings,
                event_name=event_name,
                distinct_id=distinct_id,
                properties=properties,
            )
        except Exception as exc:  # Analytics must never block outbound redirects.
            logger.warning(
                "posthog_outbound_event_failed",
                extra={"event_name": event_name, "destination_slug": destination.destination_slug, "error": str(exc)},
            )


def _html_response(page, *, request: Request, settings: Settings, engine: Engine) -> HTMLResponse:
    try:
        record_landing_visit(request, MonetizationRepository(engine), path=page.path)
    except SQLAlchemyError as exc:
        logger.warning("landing_visit_persistence_failed", extra={"path": page.path, "error": str(exc)})
    return HTMLResponse(render_document(page, settings=settings), headers={"Cache-Control": "public, max-age=60"})


def _user_agent_category(user_agent: str) -> str:
    text = user_agent.lower()
    if not text:
        return "unknown"
    if "bot" in text or "crawler" in text or "spider" in text:
        return "bot"
    if "mobile" in text or "iphone" in text or "android" in text:
        return "mobile"
    if "ipad" in text or "tablet" in text:
        return "tablet"
    return "desktop"
