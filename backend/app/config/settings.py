"""Typed environment configuration."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["local", "test", "production"]
DEFAULT_PUBLIC_DFK_CHAIN_RPC_URL = "https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        env_prefix="GAMEFI_",
        extra="ignore",
    )

    environment: EnvironmentName = "local"
    database_url: str = Field(min_length=1)
    api_title: str = "GameFi ROI API"
    log_level: str = "INFO"
    allow_sqlite_for_tests: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=2, ge=0, le=20)
    database_pool_timeout_seconds: int = Field(default=30, gt=0, le=120)
    database_connect_timeout_seconds: int = Field(default=10, gt=0, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=300, le=86_400)
    allowed_cors_origins: str = ""
    security_headers_enabled: bool = True
    public_base_url: str = "http://localhost:8000"
    ga_measurement_id: str | None = None
    sentry_dsn: str | None = None
    sentry_frontend_dsn: str | None = None
    sentry_environment: str | None = None
    sentry_release: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.02, ge=0, le=1)
    sentry_error_sample_rate: float = Field(default=1.0, ge=0, le=1)
    posthog_project_api_key: str | None = None
    posthog_host: str = "https://us.i.posthog.com"
    posthog_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    youtube_oauth_client_secrets_file: str | None = None
    youtube_oauth_token_file: str | None = None
    youtube_publish_state_file: str = "data/local/youtube/publish_state.json"
    youtube_approval_file: str = "data/local/youtube/approvals.json"
    youtube_content_pack_file: str = "distribution/content_packs/learning_batch_001.json"
    youtube_queue_file: str = "distribution/publish_queue/youtube_publish_queue.json"
    youtube_channel_handle: str = "@GamCryp"
    youtube_max_retries: int = Field(default=2, ge=0, le=5)
    elevenlabs_api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("ELEVENLABS_API_KEY", "GAMEFI_ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str | None = Field(default=None, validation_alias=AliasChoices("ELEVENLABS_VOICE_ID", "GAMEFI_ELEVENLABS_VOICE_ID"))
    elevenlabs_model_id: str | None = Field(default=None, validation_alias=AliasChoices("ELEVENLABS_MODEL_ID", "GAMEFI_ELEVENLABS_MODEL_ID"))
    elevenlabs_output_directory: str = Field(default="data/local/youtube/narration", validation_alias=AliasChoices("ELEVENLABS_OUTPUT_DIRECTORY", "GAMEFI_ELEVENLABS_OUTPUT_DIRECTORY"))
    public_x_url: str | None = "https://x.com/GamCryp"
    public_youtube_url: str = "https://www.youtube.com/@GamCryp"
    public_contact_email: str = "info@gamcryp.com"
    indexnow_key: str | None = None
    google_site_verification: str | None = None
    bing_site_verification: str | None = None
    operator_username: str | None = None
    operator_password: str | None = None
    referral_reverify_days: int = Field(default=30, ge=1, le=365)
    referral_pending_recheck_days: int = Field(default=14, ge=1, le=180)
    scheduler_cadence_minutes: int = Field(default=240, ge=5, le=1_440)
    production_hard_stale_seconds: int = Field(default=28_800, ge=300, le=86_400)
    market_data_http_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    market_data_http_max_retries: int = Field(default=2, ge=0, le=5)
    market_data_request_cache_seconds: int = Field(default=30, ge=0, le=300)
    market_data_price_freshness_seconds: int = Field(default=21_600, gt=0, le=86_400)
    coingecko_base_url: str = Field(
        default="https://api.coingecko.com/api/v3",
        min_length=1,
    )
    coingecko_api_key: str | None = None
    alcor_base_url: str = Field(
        default="https://wax.alcor.exchange/api/v2",
        min_length=1,
    )
    atomicassets_base_url: str = Field(
        default="https://wax.api.atomicassets.io",
        min_length=1,
    )
    wax_market_observation_freshness_seconds: int = Field(default=21_600, gt=0, le=86_400)
    dfk_chain_rpc_url: str = Field(default=DEFAULT_PUBLIC_DFK_CHAIN_RPC_URL, min_length=1)
    dfk_chain_observation_freshness_seconds: int = Field(default=21_600, gt=0, le=86_400)
    dfk_jeweler_refresh_enabled: bool = True
    splinterlands_base_url: str = Field(
        default="https://api.splinterlands.com",
        min_length=1,
    )
    splinterlands_observation_freshness_seconds: int = Field(default=21_600, gt=0, le=86_400)

    @field_validator("coingecko_api_key", mode="before")
    @classmethod
    def blank_api_key_is_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator(
        "indexnow_key",
        "google_site_verification",
        "bing_site_verification",
        "ga_measurement_id",
        "sentry_dsn",
        "sentry_frontend_dsn",
        "sentry_environment",
        "sentry_release",
        "posthog_project_api_key",
        "youtube_oauth_client_secrets_file",
        "youtube_oauth_token_file",
        "public_x_url",
        "operator_username",
        "operator_password",
        mode="before",
    )
    @classmethod
    def blank_optional_search_setting_is_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("indexnow_key")
    @classmethod
    def validate_indexnow_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", text):
            raise ValueError("GAMEFI_INDEXNOW_KEY must be 8-128 characters using letters, numbers, or dashes")
        return text

    @field_validator("ga_measurement_id")
    @classmethod
    def validate_ga_measurement_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().upper()
        if not re.fullmatch(r"G-[A-Z0-9]{6,20}", text):
            raise ValueError("GAMEFI_GA_MEASUREMENT_ID must look like G-XXXXXXXXXX")
        return text

    @field_validator("sentry_dsn", "sentry_frontend_dsn")
    @classmethod
    def validate_sentry_dsn(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        parsed = urlsplit(text)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Sentry DSNs must be HTTPS URLs with a host")
        if parsed.query or parsed.fragment:
            raise ValueError("Sentry DSNs must not include query or fragment")
        return text

    @field_validator("sentry_environment")
    @classmethod
    def validate_sentry_environment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{1,40}", text):
            raise ValueError(
                "GAMEFI_SENTRY_ENVIRONMENT must use 1-40 lowercase letters, numbers, dots, underscores, or dashes"
            )
        return text

    @field_validator("sentry_release")
    @classmethod
    def validate_sentry_release(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9._:@/+~-]{1,200}", text):
            raise ValueError("GAMEFI_SENTRY_RELEASE contains unsupported characters")
        return text

    @field_validator("posthog_project_api_key")
    @classmethod
    def validate_posthog_project_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", text):
            raise ValueError("GAMEFI_POSTHOG_PROJECT_API_KEY must be 8-128 token characters")
        return text

    @field_validator("posthog_host")
    @classmethod
    def validate_posthog_host(cls, value: str) -> str:
        text = value.strip().rstrip("/")
        parsed = urlsplit(text)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("GAMEFI_POSTHOG_HOST must be an HTTPS URL with a host")
        if parsed.path or parsed.query or parsed.fragment:
            raise ValueError("GAMEFI_POSTHOG_HOST must not include path, query, or fragment")
        return text

    @field_validator(
        "youtube_publish_state_file",
        "youtube_approval_file",
        "youtube_content_pack_file",
        "youtube_queue_file",
    )
    @classmethod
    def validate_youtube_file_setting(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("YouTube publisher file settings must not be blank")
        return text

    @field_validator("youtube_channel_handle")
    @classmethod
    def validate_youtube_channel_handle(cls, value: str) -> str:
        text = value.strip()
        if not re.fullmatch(r"@[A-Za-z0-9._-]{3,64}", text):
            raise ValueError("GAMEFI_YOUTUBE_CHANNEL_HANDLE must look like @GamCryp")
        return text
    @field_validator("public_base_url")
    @classmethod
    def normalize_public_base_url(cls, value: str) -> str:
        text = value.strip().rstrip("/")
        if not text.startswith(("http://", "https://")):
            raise ValueError("GAMEFI_PUBLIC_BASE_URL must start with http:// or https://")
        parsed = urlsplit(text)
        if not parsed.netloc:
            raise ValueError("GAMEFI_PUBLIC_BASE_URL must include a host")
        if parsed.path:
            raise ValueError("GAMEFI_PUBLIC_BASE_URL must not include a path")
        if parsed.query or parsed.fragment:
            raise ValueError("GAMEFI_PUBLIC_BASE_URL must not include query or fragment")
        return text

    @field_validator("public_x_url", "public_youtube_url")
    @classmethod
    def validate_public_https_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().rstrip("/")
        parsed = urlsplit(text)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Public brand URLs must be HTTPS URLs with a host")
        if parsed.query or parsed.fragment:
            raise ValueError("Public brand URLs must not include query or fragment")
        return text

    @field_validator("public_contact_email")
    @classmethod
    def validate_public_contact_email(cls, value: str) -> str:
        text = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
            raise ValueError("GAMEFI_PUBLIC_CONTACT_EMAIL must be a valid public contact email")
        return text

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        normalized = self.database_url.lower()
        is_postgresql = normalized.startswith(("postgresql://", "postgresql+psycopg://"))
        is_sqlite = normalized.startswith("sqlite")

        if is_postgresql:
            self._validate_production_settings()
            return self

        if is_sqlite and self.environment == "test" and self.allow_sqlite_for_tests:
            self._validate_production_settings()
            return self

        raise ValueError(
            "GAMEFI_DATABASE_URL must be a PostgreSQL SQLAlchemy URL. "
            "SQLite is allowed only for deterministic tests."
        )

    def _validate_production_settings(self) -> None:
        if self.environment != "production":
            return

        if not self.coingecko_api_key:
            raise ValueError("GAMEFI_COINGECKO_API_KEY is required in production")

        if self.dfk_chain_rpc_url.rstrip("/") == DEFAULT_PUBLIC_DFK_CHAIN_RPC_URL.rstrip("/"):
            raise ValueError("GAMEFI_DFK_CHAIN_RPC_URL must use a production RPC provider, not the public default")

        if "*" in self.allowed_cors_origin_values:
            raise ValueError("GAMEFI_ALLOWED_CORS_ORIGINS cannot contain '*' in production")

        if not self.security_headers_enabled:
            raise ValueError("GAMEFI_SECURITY_HEADERS_ENABLED must remain true in production")

        if not self.public_base_url.startswith("https://"):
            raise ValueError("GAMEFI_PUBLIC_BASE_URL must be an HTTPS canonical host in production")

    @property
    def database_backend(self) -> str:
        if self.database_url.lower().startswith("sqlite"):
            return "sqlite"
        return "postgresql"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def allowed_cors_origin_values(self) -> tuple[str, ...]:
        if self.allowed_cors_origins.strip() == "":
            return ()
        return tuple(origin.strip() for origin in self.allowed_cors_origins.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
