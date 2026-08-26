from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import get_settings


def test_database_url_is_required(monkeypatch) -> None:
    monkeypatch.delenv("GAMEFI_DATABASE_URL", raising=False)
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
