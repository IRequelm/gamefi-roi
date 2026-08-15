"""Splinterlands official game-data source connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.config.settings import Settings, get_settings
from app.engine.decimal_context import decimal_from_int
from app.sources.errors import SourceErrorDetail, SourceParseError
from app.sources.http import SourceHttpClient
from app.sources.observations import Observation, ObservationStatus, SourceType


SETTINGS_STARTER_PACK_PRICE_USD = "splinterlands.settings.starter_pack_price_usd"
SETTINGS_SPS_PRICE_USD = "splinterlands.settings.sps_price_usd"
SETTINGS_CONFIG_VERSION = "splinterlands.settings.config_version"
SETTINGS_SEASON_ID = "splinterlands.settings.season_id"
SETTINGS_SEASON_END_UNIX = "splinterlands.settings.season_end_unix"
SETTINGS_ENERGY_MAX = "splinterlands.settings.energy_max"
SETTINGS_ENERGY_REGEN_PER_HOUR = "splinterlands.settings.energy_regen_per_hour"
SEASON_ID = "splinterlands.season.id"
SEASON_END_UNIX = "splinterlands.season.end_unix"


@dataclass(frozen=True)
class SplinterlandsSettingsRequest:
    freshness_window: timedelta


@dataclass(frozen=True)
class SplinterlandsSeasonRequest:
    season_id: str
    freshness_window: timedelta


class SplinterlandsGameDataSource:
    provider_name = "splinterlands"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        active_settings = settings or get_settings()
        self._client = SourceHttpClient(
            provider=self.provider_name,
            base_url=active_settings.splinterlands_base_url,
            timeout_seconds=active_settings.market_data_http_timeout_seconds,
            max_retries=active_settings.market_data_http_max_retries,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_settings(self, request: SplinterlandsSettingsRequest) -> tuple[Observation, ...]:
        path = "/settings"
        payload = self._client.get_json(path, params={}, operation="get_settings")
        retrieved_at = datetime.now(UTC)
        locator = self._client.source_locator(path, {})
        observed_at = _settings_observed_at(payload) or retrieved_at
        fresh_until = retrieved_at + request.freshness_window

        season = _require_mapping(payload, "season", "get_settings")
        energy = _require_mapping(payload, "energy", "get_settings")
        season_ends = _parse_iso_utc(_require_str(season, "ends", "get_settings"), "season.ends", "get_settings")

        return (
            _official_observation(
                entity_type="game",
                entity_id="splinterlands",
                metric=SETTINGS_STARTER_PACK_PRICE_USD,
                value=_require_decimal(payload, "starter_pack_price", "get_settings"),
                unit="USD",
                quote_currency="USD",
                locator=locator,
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "starter_pack_price"},
            ),
            _official_observation(
                entity_type="asset",
                entity_id="splinterlands:sps",
                metric=SETTINGS_SPS_PRICE_USD,
                value=_require_decimal(payload, "sps_price", "get_settings"),
                unit="USD",
                quote_currency="USD",
                locator=locator,
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "sps_price"},
            ),
            _official_observation(
                entity_type="game",
                entity_id="splinterlands",
                metric=SETTINGS_CONFIG_VERSION,
                value=_require_decimal(payload, "config_version", "get_settings"),
                unit="version",
                quote_currency=None,
                locator=locator,
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "config_version"},
            ),
            _official_observation(
                entity_type="season",
                entity_id=f"splinterlands:season:{_require_decimal(season, 'id', 'get_settings')}",
                metric=SETTINGS_SEASON_ID,
                value=_require_decimal(season, "id", "get_settings"),
                unit="season",
                quote_currency=None,
                locator=locator,
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "season.id"},
            ),
            _official_observation(
                entity_type="season",
                entity_id=f"splinterlands:season:{_require_decimal(season, 'id', 'get_settings')}",
                metric=SETTINGS_SEASON_END_UNIX,
                value=decimal_from_int(_unix_seconds(season_ends)),
                unit="unix_second",
                quote_currency=None,
                locator=locator,
                observed_at=season_ends,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "season.ends"},
            ),
            _official_observation(
                entity_type="game",
                entity_id="splinterlands",
                metric=SETTINGS_ENERGY_MAX,
                value=_require_decimal(energy, "max_energy", "get_settings"),
                unit="energy",
                quote_currency=None,
                locator=locator,
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "energy.max_energy"},
            ),
            _official_observation(
                entity_type="game",
                entity_id="splinterlands",
                metric=SETTINGS_ENERGY_REGEN_PER_HOUR,
                value=_require_decimal(energy, "hourly_regen_rate", "get_settings"),
                unit="energy/hour",
                quote_currency=None,
                locator=locator,
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "energy.hourly_regen_rate"},
            ),
        )

    def get_season(self, request: SplinterlandsSeasonRequest) -> tuple[Observation, ...]:
        path = "/season"
        params = {"id": request.season_id}
        payload = self._client.get_json(path, params=params, operation="get_season")
        retrieved_at = datetime.now(UTC)
        locator = self._client.source_locator(path, params)
        season_id = _require_decimal(payload, "id", "get_season")
        season_ends = _parse_iso_utc(_require_str(payload, "ends", "get_season"), "ends", "get_season")
        fresh_until = retrieved_at + request.freshness_window
        entity_id = f"splinterlands:season:{season_id}"

        return (
            _official_observation(
                entity_type="season",
                entity_id=entity_id,
                metric=SEASON_ID,
                value=season_id,
                unit="season",
                quote_currency=None,
                locator=locator,
                observed_at=retrieved_at,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "id"},
            ),
            _official_observation(
                entity_type="season",
                entity_id=entity_id,
                metric=SEASON_END_UNIX,
                value=decimal_from_int(_unix_seconds(season_ends)),
                unit="unix_second",
                quote_currency=None,
                locator=locator,
                observed_at=season_ends,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={"classification": "LIVE", "source_field": "ends"},
            ),
        )


def _official_observation(
    *,
    entity_type: str,
    entity_id: str,
    metric: str,
    value: Decimal,
    unit: str,
    quote_currency: str | None,
    locator: str,
    observed_at: datetime,
    retrieved_at: datetime,
    fresh_until: datetime,
    metadata: dict[str, Any],
) -> Observation:
    return Observation(
        observation_id=_observation_id(entity_id, metric, observed_at),
        entity_type=entity_type,
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency=quote_currency,
        source_provider=SplinterlandsGameDataSource.provider_name,
        source_type=SourceType.OFFICIAL_API,
        source_locator=locator,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        fresh_until=fresh_until,
        status=ObservationStatus.FRESH,
        metadata=metadata,
    )


def _require_mapping(payload: dict[str, Any], key: str, operation: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise _parse_error(operation, f"{key} must be an object")
    return value


def _require_str(payload: dict[str, Any], key: str, operation: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise _parse_error(operation, f"{key} must be a non-empty string")
    return value


def _require_decimal(payload: dict[str, Any], key: str, operation: str) -> Decimal:
    value = payload.get(key)
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return Decimal(value)
        if isinstance(value, str):
            return Decimal(value)
    except InvalidOperation as exc:
        raise _parse_error(operation, f"{key} must be decimal-safe") from exc
    raise _parse_error(operation, f"{key} must be decimal-safe")


def _settings_observed_at(payload: dict[str, Any]) -> datetime | None:
    value = payload.get("timestamp")
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise _parse_error("get_settings", "timestamp must be UNIX milliseconds")
    seconds, milliseconds = divmod(value, 1000)
    return datetime.fromtimestamp(seconds, UTC) + timedelta(milliseconds=milliseconds)


def _parse_iso_utc(value: str, field_name: str, operation: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _parse_error(operation, f"{field_name} must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _parse_error(operation, f"{field_name} must include a timezone")
    return parsed.astimezone(UTC)


def _unix_seconds(value: datetime) -> int:
    return int(value.timestamp())


def _parse_error(operation: str, message: str) -> SourceParseError:
    return SourceParseError(
        SourceErrorDetail(
            provider=SplinterlandsGameDataSource.provider_name,
            operation=operation,
            message=message,
            retryable=False,
        )
    )


def _observation_id(entity_id: str, metric: str, observed_at: datetime) -> str:
    key = f"{SplinterlandsGameDataSource.provider_name}|{entity_id}|{metric}|{observed_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
