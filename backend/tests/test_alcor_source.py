from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from app.config.settings import Settings
from app.sources.alcor import AlcorMarketDataSource, AlcorTickerRequest
from app.sources.errors import SourceParseError
from app.sources.observations import ObservationStatus, SourceType


def _settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        allow_sqlite_for_tests=True,
        alcor_base_url="https://wax.provider.example/api/v2",
        market_data_http_timeout_seconds=3,
        market_data_http_max_retries=0,
    )


def test_alcor_ticker_fixture_maps_market_observations() -> None:
    fixture = """
    {
      "ticker_id": "fww-farmerstoken_wax-eosio.token",
      "market_id": 104,
      "target_currency": "wax-eosio.token",
      "base_currency": "fww-farmerstoken",
      "last_price": 0.00004394,
      "bid": 0.00001943,
      "ask": 0.0000439,
      "base_amm_liquidity": 1397476935.6326,
      "target_amm_liquidity": 7227.697110040001,
      "volumeUSD24": 6.8115,
      "frozen": false,
      "fee": 20
    }
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/tickers/fww-farmerstoken_wax-eosio.token"
        return httpx.Response(200, text=fixture, request=request)

    source = AlcorMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_ticker(
        AlcorTickerRequest(
            ticker_id="fww-farmerstoken_wax-eosio.token",
            freshness_window=timedelta(minutes=5),
        )
    )

    by_metric = {observation.metric: observation for observation in observations}
    assert by_metric["alcor.market.last_price"].value == Decimal("0.00004394")
    assert by_metric["alcor.market.last_price"].unit == "wax:wax-eosio.token"
    assert by_metric["alcor.market.base_amm_liquidity"].unit == "wax:fww-farmerstoken"
    assert by_metric["alcor.market.fee_bps"].value == Decimal("20")
    assert by_metric["alcor.market.frozen"].value == Decimal("0")
    assert by_metric["alcor.market.last_price"].source_type == SourceType.MARKET_API
    assert by_metric["alcor.market.last_price"].status == ObservationStatus.FRESH
    assert by_metric["alcor.market.last_price"].metadata["classification"] == "LIVE"


def test_alcor_ticker_rejects_missing_required_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ticker_id": "fww-farmerstoken_wax-eosio.token",
                "base_currency": "fww-farmerstoken",
                "target_currency": "wax-eosio.token",
            },
            request=request,
        )

    source = AlcorMarketDataSource(_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(SourceParseError):
        source.get_ticker(
            AlcorTickerRequest(
                ticker_id="fww-farmerstoken_wax-eosio.token",
                freshness_window=timedelta(minutes=5),
            )
        )
