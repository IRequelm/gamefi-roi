from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alembic import command
from sqlalchemy import create_engine

from app.config.settings import get_settings
from app.doctor.checks import build_alembic_config
from app.sources.observations import Observation, ObservationStatus, SourceType
from app.storage.observations import list_observations, save_observations


def test_observations_are_persisted_with_provenance(monkeypatch, tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'observations.db').as_posix()}"
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", database_url)
    settings = get_settings()
    command.upgrade(build_alembic_config(settings), "head")
    engine = create_engine(database_url)
    retrieved_at = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    observation = Observation(
        observation_id="obs-storage",
        entity_type="asset",
        entity_id="coingecko:bitcoin",
        metric="token.price",
        value=Decimal("68123.456789"),
        unit="USD",
        quote_currency="USD",
        source_provider="coingecko",
        source_type=SourceType.MARKET_API,
        source_locator="https://provider.example/api/v3/simple/price?ids=bitcoin",
        observed_at=retrieved_at,
        retrieved_at=retrieved_at,
        fresh_until=retrieved_at + timedelta(minutes=5),
        status=ObservationStatus.FRESH,
        metadata={"provider_asset_id": "bitcoin"},
    )

    saved = save_observations(engine, [observation])
    rows = list_observations(engine)

    assert saved == 1
    assert len(rows) == 1
    assert rows[0].value == Decimal("68123.456789")
    assert rows[0].source_provider == "coingecko"
    assert rows[0].metadata == {"provider_asset_id": "bitcoin"}
