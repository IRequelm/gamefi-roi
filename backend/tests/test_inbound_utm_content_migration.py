from __future__ import annotations

from alembic import command
from sqlalchemy import create_engine, text

from app.config.settings import get_settings
from app.doctor.checks import build_alembic_config


def test_utm_content_migration_preserves_existing_landing_events(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "utm-content-upgrade.db"
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", f"sqlite+pysqlite:///{database_path.as_posix()}")
    settings = get_settings()
    config = build_alembic_config(settings)

    command.upgrade(config, "20260921_0011")
    engine = create_engine(settings.sqlalchemy_database_url)
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO inbound_landing_events (
              event_id, landing_path, channel, occurred_at, created_at
            ) VALUES (
              'legacy-event', '/', 'direct', '2026-09-23 00:00:00', '2026-09-23 00:00:00'
            )
        """))

    command.upgrade(config, "head")

    with engine.begin() as connection:
        legacy = connection.execute(text(
            "SELECT event_id, utm_content FROM inbound_landing_events WHERE event_id='legacy-event'"
        )).one()
        connection.execute(text("""
            INSERT INTO inbound_landing_events (
              event_id, landing_path, channel, occurred_at, created_at, utm_content
            ) VALUES (
              'tagged-event', '/', 'youtube', '2026-09-24 00:00:00', '2026-09-24 00:00:00', 'how_to_use_gamcryp'
            )
        """))
        tagged = connection.execute(text(
            "SELECT event_id, utm_content FROM inbound_landing_events WHERE event_id='tagged-event'"
        )).one()

    engine.dispose()
    assert legacy == ("legacy-event", None)
    assert tagged == ("tagged-event", "how_to_use_gamcryp")
