from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from app.config.settings import Settings
from app.sources.atomicassets import AtomicAssetsFloorRequest, AtomicAssetsMarketDataSource
from app.sources.errors import SourceParseError
from app.sources.observations import ObservationStatus, SourceType


def _settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        allow_sqlite_for_tests=True,
        atomicassets_base_url="https://atomic.provider.example",
        market_data_http_timeout_seconds=3,
        market_data_http_max_retries=0,
    )


def test_atomicassets_floor_fixture_maps_listing_observations() -> None:
    fixture = """
    {
      "success": true,
      "data": [
        {
          "sale_id": "123456789",
          "price": {
            "amount": "34569990",
            "token_precision": 8,
            "token_symbol": "WAX",
            "token_contract": "eosio.token"
          },
          "current_collection_fee": 0.05
        }
      ],
      "query_time": 1
    }
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/atomicmarket/v2/sales"
        assert request.url.params["collection_name"] == "farmersworld"
        assert request.url.params["template_id"] == "203881"
        assert request.url.params["state"] == "1"
        return httpx.Response(200, text=fixture, request=request)

    source = AtomicAssetsMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_floor_listing(
        AtomicAssetsFloorRequest(
            collection_name="farmersworld",
            schema_name="tools",
            template_id="203881",
            listing_symbol="WAX",
            freshness_window=timedelta(minutes=5),
        )
    )

    by_metric = {observation.metric: observation for observation in observations}
    assert by_metric["atomicassets.nft.floor_price"].value == Decimal("0.3456999")
    assert by_metric["atomicassets.nft.floor_price"].unit == "WAX"
    assert by_metric["atomicassets.collection_market_fee_ratio"].value == Decimal("0.05")
    assert by_metric["atomicassets.nft.floor_price"].source_type == SourceType.MARKET_API
    assert by_metric["atomicassets.nft.floor_price"].status == ObservationStatus.FRESH
    assert by_metric["atomicassets.nft.floor_price"].metadata["classification"] == "LIVE"


def test_atomicassets_empty_floor_returns_missing_observation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "data": []}, request=request)

    source = AtomicAssetsMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_floor_listing(
        AtomicAssetsFloorRequest(
            collection_name="farmersworld",
            schema_name="tools",
            template_id="203881",
            listing_symbol="WAX",
            freshness_window=timedelta(minutes=5),
        )
    )

    assert len(observations) == 1
    assert observations[0].status == ObservationStatus.MISSING
    assert observations[0].value is None


def test_atomicassets_rejects_malformed_price() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "data": [{"price": {"amount": "bad"}}]}, request=request)

    source = AtomicAssetsMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(SourceParseError):
        source.get_floor_listing(
            AtomicAssetsFloorRequest(
                collection_name="farmersworld",
                schema_name="tools",
                template_id="203881",
                listing_symbol="WAX",
                freshness_window=timedelta(minutes=5),
            )
        )


def test_atomicassets_rejects_zero_floor_price() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {
                        "price": {"amount": "0", "token_precision": 8, "token_symbol": "WAX"},
                        "current_collection_fee": "0.05",
                    }
                ],
            },
            request=request,
        )

    source = AtomicAssetsMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(SourceParseError, match="strictly positive"):
        source.get_floor_listing(
            AtomicAssetsFloorRequest(
                collection_name="farmersworld",
                schema_name="tools",
                template_id="203881",
                listing_symbol="WAX",
                freshness_window=timedelta(minutes=5),
            )
        )
