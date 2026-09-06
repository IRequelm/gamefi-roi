from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import get_settings


def test_database_url_is_required(monkeypatch) -> None:
    # An ignored local .env may provide the setting; an explicit empty value
    # keeps this missing-setting regression deterministic in local runs too.
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "")
    monkeypatch.delenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", raising=False)

    with pytest.raises(ValidationError):
        get_settings()


def test_postgresql_database_url_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "local")
    monkeypatch.setenv(
        "GAMEFI_DATABASE_URL",
        "postgresql+psycopg://gamefi:gamefi_local_password@localhost:5432/gamefi_roi",
    )

    settings = get_settings()

    assert settings.database_backend == "postgresql"


def test_sqlite_is_only_allowed_for_deterministic_tests(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "local")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "false")

    with pytest.raises(ValidationError):
        get_settings()


def test_sqlite_test_override_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")

    settings = get_settings()

    assert settings.database_backend == "sqlite"


def test_blank_coingecko_api_key_is_not_treated_as_secret(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_COINGECKO_API_KEY", "")

    settings = get_settings()

    assert settings.coingecko_api_key is None


def test_public_base_url_is_normalized_and_required_https_in_production(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "local")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/gamefi")
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "https://example.com/")

    settings = get_settings()

    assert settings.public_base_url == "https://example.com"

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "production")
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "http://example.com")
    monkeypatch.setenv("GAMEFI_COINGECKO_API_KEY", "secret-test-key")
    monkeypatch.setenv("GAMEFI_DFK_CHAIN_RPC_URL", "https://dedicated-rpc.example/dfk")

    with pytest.raises(ValidationError):
        get_settings()

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "local")
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "https://example.com/app")

    with pytest.raises(ValidationError):
        get_settings()


def test_indexnow_key_is_optional_but_validated_when_present(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_INDEXNOW_KEY", "")

    settings = get_settings()

    assert settings.indexnow_key is None

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_INDEXNOW_KEY", "bad key")

    with pytest.raises(ValidationError):
        get_settings()


def test_ga_and_public_brand_config_are_optional_and_validated(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_GA_MEASUREMENT_ID", "")
    monkeypatch.setenv("GAMEFI_PUBLIC_X_URL", "")

    settings = get_settings()

    assert settings.ga_measurement_id is None
    assert settings.public_x_url is None
    assert settings.public_youtube_url == "https://www.youtube.com/@GamCryp"
    assert settings.public_contact_email == "info@gamcryp.com"

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_GA_MEASUREMENT_ID", "G-test1234")
    monkeypatch.setenv("GAMEFI_PUBLIC_X_URL", "https://x.com/GamCryp")

    settings = get_settings()

    assert settings.ga_measurement_id == "G-TEST1234"
    assert settings.public_x_url == "https://x.com/GamCryp"

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_GA_MEASUREMENT_ID", "UA-legacy")

    with pytest.raises(ValidationError):
        get_settings()

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_GA_MEASUREMENT_ID", "")
    monkeypatch.setenv("GAMEFI_PUBLIC_X_URL", "http://x.example/gamcryp")

    with pytest.raises(ValidationError):
        get_settings()


def test_render_postgresql_url_is_normalized_to_psycopg_driver(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "local")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "postgresql://user:pass@host:5432/gamefi")

    settings = get_settings()

    assert settings.database_backend == "postgresql"
    assert settings.sqlalchemy_database_url == "postgresql+psycopg://user:pass@host:5432/gamefi"


def test_production_requires_market_key_and_dedicated_dfk_rpc(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "production")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/gamefi")
    monkeypatch.setenv("GAMEFI_DFK_CHAIN_RPC_URL", "https://dedicated-rpc.example/dfk")
    monkeypatch.setenv("GAMEFI_COINGECKO_API_KEY", "")

    with pytest.raises(ValidationError):
        get_settings()


def test_production_rejects_public_dfk_rpc_default(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "production")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/gamefi")
    monkeypatch.setenv("GAMEFI_COINGECKO_API_KEY", "secret-test-key")

    with pytest.raises(ValidationError):
        get_settings()


def test_cors_origins_parse_and_wildcard_is_not_allowed_in_production(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "local")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/gamefi")
    monkeypatch.setenv("GAMEFI_ALLOWED_CORS_ORIGINS", "https://app.example, https://beta.example")

    settings = get_settings()

    assert settings.allowed_cors_origin_values == ("https://app.example", "https://beta.example")

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "production")
    monkeypatch.setenv("GAMEFI_COINGECKO_API_KEY", "secret-test-key")
    monkeypatch.setenv("GAMEFI_DFK_CHAIN_RPC_URL", "https://dedicated-rpc.example/dfk")
    monkeypatch.setenv("GAMEFI_ALLOWED_CORS_ORIGINS", "*")

    with pytest.raises(ValidationError):
        get_settings()


def test_market_source_retry_config_is_bounded(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_MARKET_DATA_HTTP_MAX_RETRIES", "20")

    with pytest.raises(ValidationError):
        get_settings()


def test_wax_market_source_config_defaults_are_present(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")

    settings = get_settings()

    assert settings.alcor_base_url == "https://wax.alcor.exchange/api/v2"
    assert settings.atomicassets_base_url == "https://wax.api.atomicassets.io"
    assert settings.wax_market_observation_freshness_seconds == 300


def test_splinterlands_source_config_defaults_are_present(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")

    settings = get_settings()

    assert settings.splinterlands_base_url == "https://api.splinterlands.com"
    assert settings.splinterlands_observation_freshness_seconds == 300


def test_observability_config_is_optional_and_validated(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_SENTRY_DSN", "")
    monkeypatch.setenv("GAMEFI_SENTRY_FRONTEND_DSN", "")
    monkeypatch.setenv("GAMEFI_SENTRY_ENVIRONMENT", "")
    monkeypatch.setenv("GAMEFI_SENTRY_RELEASE", "")
    monkeypatch.setenv("GAMEFI_POSTHOG_PROJECT_API_KEY", "")

    settings = get_settings()

    assert settings.sentry_dsn is None
    assert settings.sentry_frontend_dsn is None
    assert settings.sentry_environment is None
    assert settings.sentry_release is None
    assert settings.sentry_traces_sample_rate == 0.02
    assert settings.sentry_error_sample_rate == 1.0
    assert settings.posthog_project_api_key is None
    assert settings.posthog_host == "https://us.i.posthog.com"
    assert settings.posthog_timeout_seconds == 2

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_SENTRY_DSN", "https://public@example.ingest.sentry.io/123")
    monkeypatch.setenv("GAMEFI_SENTRY_FRONTEND_DSN", "https://browser@example.ingest.sentry.io/456")
    monkeypatch.setenv("GAMEFI_SENTRY_ENVIRONMENT", "Production")
    monkeypatch.setenv("GAMEFI_SENTRY_RELEASE", "gamcryp@abc123")
    monkeypatch.setenv("GAMEFI_POSTHOG_PROJECT_API_KEY", "phc_test_key")
    monkeypatch.setenv("GAMEFI_POSTHOG_HOST", "https://eu.i.posthog.com/")

    settings = get_settings()

    assert settings.sentry_dsn == "https://public@example.ingest.sentry.io/123"
    assert settings.sentry_frontend_dsn == "https://browser@example.ingest.sentry.io/456"
    assert settings.sentry_environment == "production"
    assert settings.sentry_release == "gamcryp@abc123"
    assert settings.posthog_project_api_key == "phc_test_key"
    assert settings.posthog_host == "https://eu.i.posthog.com"

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_SENTRY_DSN", "http://example.invalid/1")
    with pytest.raises(ValidationError):
        get_settings()

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_SENTRY_DSN", "")
    monkeypatch.setenv("GAMEFI_POSTHOG_HOST", "https://us.i.posthog.com/capture/")
    with pytest.raises(ValidationError):
        get_settings()

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_POSTHOG_HOST", "https://us.i.posthog.com")
    monkeypatch.setenv("GAMEFI_POSTHOG_PROJECT_API_KEY", "bad key")
    with pytest.raises(ValidationError):
        get_settings()


def test_youtube_publisher_config_is_optional_and_validated(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE", "")
    monkeypatch.setenv("GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE", "")

    settings = get_settings()

    assert settings.youtube_oauth_client_secrets_file is None
    assert settings.youtube_oauth_token_file is None
    assert settings.youtube_publish_state_file == "data/local/youtube/publish_state.json"
    assert settings.youtube_approval_file == "data/local/youtube/approvals.json"
    assert settings.youtube_content_pack_file == "distribution/content_packs/learning_batch_001.json"
    assert settings.youtube_queue_file == "distribution/publish_queue/youtube_publish_queue.json"
    assert settings.youtube_channel_handle == "@GamCryp"
    assert settings.youtube_max_retries == 2

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE", "data/local/youtube/client_secret.json")
    monkeypatch.setenv("GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE", "data/local/youtube/token.json")
    monkeypatch.setenv("GAMEFI_YOUTUBE_PUBLISH_STATE_FILE", "data/local/youtube/state.json")
    monkeypatch.setenv("GAMEFI_YOUTUBE_CHANNEL_HANDLE", "@GamCryp")
    monkeypatch.setenv("GAMEFI_YOUTUBE_MAX_RETRIES", "3")

    settings = get_settings()

    assert settings.youtube_oauth_client_secrets_file == "data/local/youtube/client_secret.json"
    assert settings.youtube_oauth_token_file == "data/local/youtube/token.json"
    assert settings.youtube_publish_state_file == "data/local/youtube/state.json"
    assert settings.youtube_channel_handle == "@GamCryp"
    assert settings.youtube_max_retries == 3

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_YOUTUBE_CHANNEL_HANDLE", "GamCryp")
    with pytest.raises(ValidationError):
        get_settings()

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_YOUTUBE_CHANNEL_HANDLE", "@GamCryp")
    monkeypatch.setenv("GAMEFI_YOUTUBE_MAX_RETRIES", "20")
    with pytest.raises(ValidationError):
        get_settings()
