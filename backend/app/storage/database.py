"""Database engine helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text

from app.config.settings import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    kwargs = {"pool_pre_ping": True}
    if active_settings.database_backend == "postgresql":
        kwargs.update(
            {
                "pool_size": active_settings.database_pool_size,
                "max_overflow": active_settings.database_max_overflow,
                "pool_timeout": active_settings.database_pool_timeout_seconds,
                "pool_recycle": active_settings.database_pool_recycle_seconds,
            }
        )
    return create_engine(active_settings.sqlalchemy_database_url, **kwargs)


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
