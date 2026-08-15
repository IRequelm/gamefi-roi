"""Typed environment configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["local", "test", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GAMEFI_",
        extra="ignore",
    )

    environment: EnvironmentName = "local"
    database_url: str = Field(min_length=1)
    api_title: str = "GameFi ROI API"
    log_level: str = "INFO"
    allow_sqlite_for_tests: bool = False

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        normalized = self.database_url.lower()
        is_postgresql = normalized.startswith(("postgresql://", "postgresql+psycopg://"))
        is_sqlite = normalized.startswith("sqlite")

        if is_postgresql:
            return self

        if is_sqlite and self.environment == "test" and self.allow_sqlite_for_tests:
            return self

        raise ValueError(
            "GAMEFI_DATABASE_URL must be a PostgreSQL SQLAlchemy URL. "
            "SQLite is allowed only for deterministic tests."
        )

    @property
    def database_backend(self) -> str:
        if self.database_url.lower().startswith("sqlite"):
            return "sqlite"
        return "postgresql"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
