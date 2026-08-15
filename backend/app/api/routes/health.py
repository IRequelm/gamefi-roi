"""Application health endpoint."""

from fastapi import APIRouter, Depends

from app import __version__
from app.config.settings import Settings, get_settings

router = APIRouter()


@router.get("/health", tags=["health"])
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.api_title,
        "environment": settings.environment,
        "version": __version__,
    }
