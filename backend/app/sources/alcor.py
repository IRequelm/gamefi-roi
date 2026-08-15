"""Alcor WAX market-data source connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.config.settings import Settings, get_settings
from app.sources.errors import SourceErrorDetail, SourceParseError
from app.sources.http import SourceHttpClient
from app.sources.observations import Observation, ObservationStatus, SourceType


@dataclass(frozen=True)
class AlcorTickerRequest:
    ticker_id: str
    freshness_window: timedelta


class AlcorMarketDataSource:
    provider_name = "alcor"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        active_settings = settings or get_settings()
        self._client = SourceHttpClient(
            provider=self.provider_name,
            base_url=active_settings.alcor_base_url,
            timeout_seconds=active_settings.market_data_http_timeout_seconds,
            max_retries=active_settings.market_data_http_max_retries,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_ticker(self, request: AlcorTickerRequest) -> tuple[Observation, ...]:
        path = f"/tickers/{request.ticker_id}"
        payload = self._client.get_json(path, params={}, operation="get_ticker")
        retrieved_at = datetime.now(UTC)
        locator = self._client.source_locator(path, {})

        ticker_id = _require_str(payload, "ticker_id")
        base_currency = _require_str(payload, "base_currency")
        target_currency = _require_str(payload, "target_currency")
        base_unit = f"wax:{base_currency}"
        target_unit = f"wax:{target_currency}"
        entity_id = f"alcor:wax:{ticker_id}"
        metadata = {
            "classification": "LIVE",
            "ticker_id": ticker_id,
            "base_currency": base_currency,
            "target_currency": target_currency,
            "market_id": str(payload.get("market_id")) if payload.get("market_id") is not None else None,
        }
        fresh_until = retrieved_at + request.freshness_window

        return (
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.last_price",
                value=_require_decimal(payload, "last_price"),
                unit=target_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.bid",
                value=_require_decimal(payload, "bid"),
                unit=target_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.ask",
                value=_require_decimal(payload, "ask"),
                unit=target_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.base_amm_liquidity",
                value=_require_decimal(payload, "base_amm_liquidity"),
                unit=base_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.target_amm_liquidity",
                value=_require_decimal(payload, "target_amm_liquidity"),
                unit=target_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.fee_bps",
                value=_fee_to_bps(_require_decimal(payload, "fee")),
                unit="basis_point",
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.volume_usd_24h",
                value=_require_decimal(payload, "volumeUSD24"),
                unit="USD",
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
                quote_currency="USD",
            ),
            _market_observation(
                entity_id=entity_id,
                metric="alcor.market.frozen",
                value=_frozen_to_decimal(payload),
                unit="boolean",
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
        )


def _market_observation(
    *,
    entity_id: str,
    metric: str,
    value: Decimal,
    unit: str,
    locator: str,
    retrieved_at: datetime,
    fresh_until: datetime,
    metadata: dict[str, Any],
    quote_currency: str | None = None,
) -> Observation:
    return Observation(
        observation_id=_observation_id(entity_id, metric, retrieved_at),
        entity_type="market",
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency=quote_currency,
        source_provider=AlcorMarketDataSource.provider_name,
        source_type=SourceType.MARKET_API,
        source_locator=locator,
        observed_at=retrieved_at,
        retrieved_at=retrieved_at,
        fresh_until=fresh_until,
        status=ObservationStatus.FRESH,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SourceParseError(
            SourceErrorDetail(
                provider=AlcorMarketDataSource.provider_name,
                operation="get_ticker",
                message=f"{key} must be a non-empty string",
                retryable=False,
            )
        )
    return value


def _require_decimal(payload: dict[str, Any], key: str) -> Decimal:
    value = _optional_decimal(payload, key)
    if value is None:
        raise SourceParseError(
            SourceErrorDetail(
                provider=AlcorMarketDataSource.provider_name,
                operation="get_ticker",
                message=f"{key} must be decimal-safe",
                retryable=False,
            )
        )
    return value


def _optional_decimal(payload: dict[str, Any], key: str) -> Decimal | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return Decimal(value)
        if isinstance(value, str):
            return Decimal(value)
    except InvalidOperation:
        return None
    return None


def _fee_to_bps(fee_value: Decimal) -> Decimal:
    return fee_value


def _frozen_to_decimal(payload: dict[str, Any]) -> Decimal:
    value = payload.get("frozen")
    if isinstance(value, bool):
        return Decimal("1") if value else Decimal("0")
    if isinstance(value, int) and value in {0, 1}:
        return Decimal(value)
    raise SourceParseError(
        SourceErrorDetail(
            provider=AlcorMarketDataSource.provider_name,
            operation="get_ticker",
            message="frozen must be a boolean or 0/1 flag",
            retryable=False,
        )
    )


def _observation_id(entity_id: str, metric: str, retrieved_at: datetime) -> str:
    key = f"{AlcorMarketDataSource.provider_name}|{entity_id}|{metric}|{retrieved_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
