from __future__ import annotations

from alembic import command

from app.config.settings import get_settings
from app.doctor.checks import build_alembic_config, run_all_checks


def _sqlite_url(path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


def test_doctor_passes_after_database_is_migrated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", _sqlite_url(tmp_path / "doctor.db"))

    settings = get_settings()
    command.upgrade(build_alembic_config(settings), "head")

    results = run_all_checks()

    assert all(result.ok for result in results), results


def test_doctor_reports_pending_migration(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", _sqlite_url(tmp_path / "pending.db"))

    results = run_all_checks()
    migrations = next(result for result in results if result.name == "migrations")

    assert migrations.ok is False
    assert "expected 20260823_0005" in migrations.detail


def test_doctor_includes_market_source_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", _sqlite_url(tmp_path / "doctor-market.db"))

    settings = get_settings()
    command.upgrade(build_alembic_config(settings), "head")
    results = run_all_checks()

    names = {result.name for result in results}
    market_source_config = next(result for result in results if result.name == "market-source-config")

    assert "market-source-config" in names
    assert market_source_config.ok is True
    assert "price_freshness=300s" in market_source_config.detail


def test_doctor_includes_adapter_source_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", _sqlite_url(tmp_path / "doctor-adapter.db"))

    settings = get_settings()
    command.upgrade(build_alembic_config(settings), "head")
    results = run_all_checks()

    names = {result.name for result in results}
    adapter_source_config = next(result for result in results if result.name == "adapter-source-config")

    assert "adapter-source-config" in names
    assert adapter_source_config.ok is True
    assert "dfk_freshness=300s" in adapter_source_config.detail
    assert "alcor_configured=True" in adapter_source_config.detail
    assert "atomicassets_configured=True" in adapter_source_config.detail
    assert "wax_market_freshness=300s" in adapter_source_config.detail
