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
