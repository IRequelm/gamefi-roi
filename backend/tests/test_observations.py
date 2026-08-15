from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.sources.observations import Observation, ObservationStatus, SourceType


def _observation(**overrides) -> Observation:
    retrieved_at = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    payload = {
        "observation_id": "obs-1",
        "entity_type": "asset",
        "entity_id": "coingecko:bitcoin",
        "metric": "token.price",
        "value": Decimal("100.25"),
        "unit": "USD",
        "quote_currency": "usd",
        "source_provider": "coingecko",
        "source_type": SourceType.MARKET_API,
        "source_locator": "https://example.test/simple/price",
        "observed_at": retrieved_at,
        "retrieved_at": retrieved_at,
        "fresh_until": retrieved_at + timedelta(minutes=5),
        "status": ObservationStatus.FRESH,
        "metadata": {"provider_asset_id": "bitcoin"},
    }
    payload.update(overrides)
    return Observation(**payload)


def test_observation_normalizes_quote_currency_and_status() -> None:
    observation = _observation()

    assert observation.quote_currency == "USD"
    assert observation.status_at(datetime(2026, 8, 15, 12, 4, tzinfo=UTC)) == ObservationStatus.FRESH
    assert observation.status_at(datetime(2026, 8, 15, 12, 6, tzinfo=UTC)) == ObservationStatus.STALE


def test_observation_rejects_float_values() -> None:
    with pytest.raises(ValidationError):
        _observation(value=100.25)


def test_fresh_observation_requires_explicit_value() -> None:
    with pytest.raises(ValidationError):
        _observation(value=None)


def test_missing_observation_can_carry_no_value() -> None:
    retrieved_at = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    observation = _observation(
        value=None,
        observed_at=None,
        fresh_until=retrieved_at,
        status=ObservationStatus.MISSING,
    )

    assert observation.value is None
    assert observation.status == ObservationStatus.MISSING
