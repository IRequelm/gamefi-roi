"""Routes for the static G11 web MVP."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
FRONTEND_ASSETS = FRONTEND_ROOT / "assets"
INDEX_HTML = FRONTEND_ROOT / "index.html"

router = APIRouter(include_in_schema=False)


def frontend_assets() -> StaticFiles:
    return StaticFiles(directory=FRONTEND_ASSETS)


@router.get("/")
@router.get("/rankings")
@router.get("/methodology")
@router.get("/games/{game_id}")
@router.get("/strategies/{strategy_id}")
def serve_frontend() -> FileResponse:
    return FileResponse(INDEX_HTML)
