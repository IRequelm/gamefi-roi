from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.config.settings import Settings
from app.sources.coingecko import CoinGeckoMarketDataSource
from app.sources.errors import SourceParseError
from app.sources.market_data import TokenPriceRequest
from app.sources.observations import ObservationStatus, SourceType

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        allow_sqlite_for_tests=True,
        coingecko_base_url="https://provider.example/api/v3",
        market_data_http_timeout_seconds=3,
        market_data_http_max_retries=0,
    )


def test_coingecko_simple_price_fixture_maps_to_observations() -> None:
    fixture = (FIXTURE_DIR / "coingecko_simple_price.json").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/simple/price"
        assert request.url.params["ids"] == "bitcoin,ethereum"
        assert request.url.params["vs_currencies"] == "usd"
        assert request.url.params["include_last_updated_at"] == "true"
        return httpx.Response(200, text=fixture, request=request)

    source = CoinGeckoMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_token_prices(
        TokenPriceRequest(
            provider_asset_ids=("bitcoin", "ethereum"),
            quote_currency="usd",
            freshness_window=timedelta(minutes=5),
        )
    )

    assert [observation.entity_id for observation in observations] == [
        "coingecko:bitcoin",
        "coingecko:ethereum",
    ]
    assert observations[0].value == Decimal("68123.456789")
    assert observations[0].source_type == SourceType.MARKET_API
    assert observations[0].status == ObservationStatus.FRESH
    assert observations[0].observed_at == datetime(2024, 3, 25, 8, 45, tzinfo=UTC)
    assert "include_last_updated_at=true" in observations[0].source_locator


def test_coingecko_missing_asset_returns_missing_observation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"bitcoin": {"usd": "100.0"}}, request=request)

    source = CoinGeckoMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_token_prices(
        TokenPriceRequest(
            provider_asset_ids=("unknown-token",),
            quote_currency="usd",
            freshness_window=timedelta(minutes=5),
        )
    )

    assert len(observations) == 1
    assert observations[0].value is None
    assert observations[0].status == ObservationStatus.MISSING


def test_coingecko_rejects_non_integer_observed_timestamp() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"bitcoin": {"usd": 100.0, "last_updated_at": "now"}}, request=request)

    source = CoinGeckoMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(SourceParseError):
        source.get_token_prices(
            TokenPriceRequest(
                provider_asset_ids=("bitcoin",),
                quote_currency="usd",
                freshness_window=timedelta(minutes=5),
            )
        )
