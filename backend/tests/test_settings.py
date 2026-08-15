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
