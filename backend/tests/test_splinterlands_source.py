from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from app.config.settings import Settings
from app.sources.errors import SourceParseError
from app.sources.observations import ObservationStatus, SourceType
from app.sources.splinterlands import (
    SEASON_END_UNIX,
    SEASON_ID,
    SETTINGS_CONFIG_VERSION,
    SETTINGS_ENERGY_MAX,
    SETTINGS_ENERGY_REGEN_PER_HOUR,
    SETTINGS_SEASON_END_UNIX,
    SETTINGS_SEASON_ID,
    SETTINGS_SPS_PRICE_USD,
    SETTINGS_STARTER_PACK_PRICE_USD,
    SplinterlandsGameDataSource,
    SplinterlandsSeasonRequest,
    SplinterlandsSettingsRequest,
)


def _settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        allow_sqlite_for_tests=True,
        splinterlands_base_url="https://splinterlands.provider.example",
        market_data_http_timeout_seconds=3,
        market_data_http_max_retries=0,
    )


def test_splinterlands_settings_fixture_maps_official_observations() -> None:
    fixture = {
        "starter_pack_price": 10,
        "sps_price": 0.0033603,
        "config_version": 208,
        "timestamp": 1786816129292,
        "season": {
            "id": 189,
            "name": "Ranked Rewards Season 102",
            "ends": "2026-08-31T14:00:00.000Z",
        },
        "energy": {
            "max_energy": 50,
            "hourly_regen_rate": 1,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/settings"
        return httpx.Response(200, json=fixture, request=request)

    source = SplinterlandsGameDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_settings(SplinterlandsSettingsRequest(freshness_window=timedelta(minutes=5)))

    by_metric = {observation.metric: observation for observation in observations}
    assert by_metric[SETTINGS_STARTER_PACK_PRICE_USD].value == Decimal("10")
    assert by_metric[SETTINGS_SPS_PRICE_USD].value == Decimal("0.0033603")
    assert by_metric[SETTINGS_CONFIG_VERSION].value == Decimal("208")
    assert by_metric[SETTINGS_SEASON_ID].value == Decimal("189")
    assert by_metric[SETTINGS_SEASON_END_UNIX].value == Decimal("1788184800")
    assert by_metric[SETTINGS_ENERGY_MAX].value == Decimal("50")
    assert by_metric[SETTINGS_ENERGY_REGEN_PER_HOUR].value == Decimal("1")
    assert by_metric[SETTINGS_STARTER_PACK_PRICE_USD].source_type == SourceType.OFFICIAL_API
    assert by_metric[SETTINGS_STARTER_PACK_PRICE_USD].status == ObservationStatus.FRESH
    assert by_metric[SETTINGS_STARTER_PACK_PRICE_USD].metadata["classification"] == "LIVE"


def test_splinterlands_season_fixture_maps_official_observations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/season"
        assert request.url.params["id"] == "189"
        return httpx.Response(
            200,
            json={"id": 189, "ends": "2026-08-31T14:00:00.000Z", "reset_block_num": None},
            request=request,
        )

    source = SplinterlandsGameDataSource(_settings(), transport=httpx.MockTransport(handler))

    observations = source.get_season(SplinterlandsSeasonRequest(season_id="189", freshness_window=timedelta(minutes=5)))

    by_metric = {observation.metric: observation for observation in observations}
    assert by_metric[SEASON_ID].value == Decimal("189")
    assert by_metric[SEASON_END_UNIX].value == Decimal("1788184800")
    assert by_metric[SEASON_ID].source_type == SourceType.OFFICIAL_API


def test_splinterlands_settings_rejects_missing_required_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"starter_pack_price": 10, "season": {"id": 189, "ends": "2026-08-31T14:00:00.000Z"}},
            request=request,
        )

    source = SplinterlandsGameDataSource(_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(SourceParseError):
        source.get_settings(SplinterlandsSettingsRequest(freshness_window=timedelta(minutes=5)))
