"""Routes for the static G11 web MVP."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from app.strategies.catalog import get_outbound_destination

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
FRONTEND_ASSETS = FRONTEND_ROOT / "assets"
INDEX_HTML = FRONTEND_ROOT / "index.html"

router = APIRouter(include_in_schema=False)
logger = logging.getLogger(__name__)


def frontend_assets() -> StaticFiles:
    return StaticFiles(directory=FRONTEND_ASSETS)


@router.get("/")
@router.get("/rankings")
@router.get("/opportunities")
@router.get("/opportunities/{opportunity_id}")
@router.get("/methodology")
@router.get("/games/{game_id}")
@router.get("/strategies/{strategy_id}")
def serve_frontend() -> FileResponse:
    return FileResponse(INDEX_HTML)


@router.get("/go/{destination_slug}")
def outbound_redirect(destination_slug: str) -> RedirectResponse:
    destination = get_outbound_destination(destination_slug)
    if destination is None or not destination.is_active() or "redirect" not in destination.allowed_surfaces:
        raise HTTPException(status_code=404, detail="Unknown or inactive outbound destination.")

    target_url = destination.target_url
    parsed = urlsplit(target_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=404, detail="Outbound destination is not reviewed for redirect.")

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
    return RedirectResponse(target_url, status_code=302, headers={"Cache-Control": "no-store"})
