"""FastAPI application factory."""

from fastapi import FastAPI

from app import __version__
from app.api.routes.health import router as health_router
from app.api.v1.routes import router as api_v1_router
from app.config.settings import get_settings
from app.web.routes import frontend_assets, router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    api = FastAPI(title=settings.api_title, version=__version__)
    api.include_router(health_router)
    api.include_router(api_v1_router)
    api.mount("/assets", frontend_assets(), name="frontend-assets")
    api.include_router(web_router)
    return api
