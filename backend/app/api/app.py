"""FastAPI application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app import __version__
from app.api.routes.health import router as health_router
from app.api.v1.routes import router as api_v1_router
from app.config.settings import get_settings
from app.observability.sentry import initialize_sentry
from app.operator.ai_routes import router as operator_ai_router
from app.operator.routes import router as operator_router
from app.web.routes import frontend_assets, router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_level)
    initialize_sentry(settings)
    api = FastAPI(title=settings.api_title, version=__version__)
    if settings.allowed_cors_origin_values:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.allowed_cors_origin_values),
            allow_methods=["GET"],
            allow_headers=["*"],
        )
    if settings.security_headers_enabled:
        _install_security_headers(api, environment=settings.environment)
    api.include_router(health_router)
    api.include_router(api_v1_router)
    api.include_router(operator_router)
    api.include_router(operator_ai_router)
    api.mount("/assets", frontend_assets(), name="frontend-assets")
    api.include_router(web_router)
    return api


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _install_security_headers(api: FastAPI, *, environment: str) -> None:
    @api.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if environment == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
