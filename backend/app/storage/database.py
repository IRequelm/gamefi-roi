"""Database engine helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text

from app.config.settings import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    return create_engine(active_settings.database_url, pool_pre_ping=True)


@contextmanager
def connect(settings: Settings | None = None) -> Iterator[Engine]:
    engine = create_database_engine(settings)
    try:
        yield engine
    finally:
        engine.dispose()


def check_connectivity(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("select 1"))
