"""Typed environment configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    market_data_http_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    market_data_http_max_retries: int = Field(default=2, ge=0, le=5)
    market_data_price_freshness_seconds: int = Field(default=300, gt=0, le=86_400)
    coingecko_base_url: str = Field(
        default="https://api.coingecko.com/api/v3",
        min_length=1,
    )
    coingecko_api_key: str | None = None
    dfk_chain_rpc_url: str = Field(
        default="https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc",
        min_length=1,
    )
    dfk_chain_observation_freshness_seconds: int = Field(default=300, gt=0, le=86_400)

    @field_validator("coingecko_api_key", mode="before")
    @classmethod
    def blank_api_key_is_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

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
