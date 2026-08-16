"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy import Engine

from app.config.settings import Settings, get_settings
from app.storage.database import create_database_engine


def get_database_engine(settings: Settings = Depends(get_settings)) -> Iterator[Engine]:
    engine = create_database_engine(settings)
    try:
        yield engine
    finally:
        engine.dispose()
