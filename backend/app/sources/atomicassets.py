"""AtomicAssets WAX marketplace source connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.config.settings import Settings, get_settings
from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_int
from app.sources.errors import SourceErrorDetail, SourceParseError
from app.sources.http import SourceHttpClient
from app.sources.observations import Observation, ObservationStatus, SourceType


@dataclass(frozen=True)
class AtomicAssetsFloorRequest:
    collection_name: str
    schema_name: str
    template_id: str
    listing_symbol: str
    freshness_window: timedelta


class AtomicAssetsMarketDataSource:
    provider_name = "atomicassets"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        active_settings = settings or get_settings()
        self._client = SourceHttpClient(
            provider=self.provider_name,
            base_url=active_settings.atomicassets_base_url,
            timeout_seconds=active_settings.market_data_http_timeout_seconds,
            max_retries=active_settings.market_data_http_max_retries,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_floor_listing(self, request: AtomicAssetsFloorRequest) -> tuple[Observation, ...]:
        params = {
            "collection_name": request.collection_name,
            "schema_name": request.schema_name,
            "template_id": request.template_id,
            "state": "1",
            "symbol": request.listing_symbol,
            "sort": "price",
            "order": "asc",
            "limit": "1",
        }
        payload = self._client.get_json("/atomicmarket/v2/sales", params=params, operation="get_floor_listing")
        retrieved_at = datetime.now(UTC)
        locator = self._client.source_locator("/atomicmarket/v2/sales", params)
        entity_id = f"atomicassets:{request.collection_name}:{request.schema_name}:{request.template_id}"
        fresh_until = retrieved_at + request.freshness_window

        data = payload.get("data")
        if not isinstance(data, list):
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation="get_floor_listing",
                    message="AtomicAssets sales payload data must be a list",
                    retryable=False,
                )
            )
        if not data:
            return (
                _missing_observation(
                    entity_id=entity_id,
                    metric="atomicassets.nft.floor_price",
                    unit=request.listing_symbol.upper(),
                    locator=locator,
                    retrieved_at=retrieved_at,
                ),
            )

        sale = data[0]
        if not isinstance(sale, dict):
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation="get_floor_listing",
                    message="AtomicAssets sale must be an object",
                    retryable=False,
                )
            )
        price_value, price_unit = _sale_price(sale)
        market_fee_ratio = _market_fee_ratio(sale)
        metadata = {
            "classification": "LIVE",
            "collection_name": request.collection_name,
            "schema_name": request.schema_name,
            "template_id": request.template_id,
            "sale_id": str(sale.get("sale_id")) if sale.get("sale_id") is not None else None,
        }

        return (
            _market_observation(
                entity_id=entity_id,
                metric="atomicassets.nft.floor_price",
                value=price_value,
                unit=price_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="atomicassets.collection_market_fee_ratio",
                value=market_fee_ratio,
                unit="ratio",
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
        )


def _sale_price(sale: dict[str, Any]) -> tuple[Decimal, str]:
    price = sale.get("price")
    if not isinstance(price, dict):
        raise SourceParseError(
            SourceErrorDetail(
                provider=AtomicAssetsMarketDataSource.provider_name,
                operation="get_floor_listing",
                message="AtomicAssets sale price must be an object",
                retryable=False,
            )
        )
    amount = price.get("amount")
    precision = price.get("token_precision")
    symbol = price.get("token_symbol")
    if not isinstance(amount, str) or not amount.isdigit() or not isinstance(precision, int) or precision < 0:
        raise SourceParseError(
            SourceErrorDetail(
                provider=AtomicAssetsMarketDataSource.provider_name,
                operation="get_floor_listing",
                message="AtomicAssets sale price amount and precision must be decimal-safe",
                retryable=False,
            )
        )
    if not isinstance(symbol, str) or not symbol:
        raise SourceParseError(
            SourceErrorDetail(
                provider=AtomicAssetsMarketDataSource.provider_name,
                operation="get_floor_listing",
                message="AtomicAssets sale token symbol is required",
                retryable=False,
            )
        )

    denominator = decimal_from_int(10) ** precision
    value = FINANCIAL_DECIMAL_CONTEXT.divide(Decimal(amount), denominator)
    if value <= Decimal("0"):
        raise SourceParseError(
            SourceErrorDetail(
                provider=AtomicAssetsMarketDataSource.provider_name,
                operation="get_floor_listing",
                message="AtomicAssets sale floor price must be strictly positive",
                retryable=False,
            )
        )
    return value, symbol.upper()


def _market_fee_ratio(sale: dict[str, Any]) -> Decimal:
    raw = sale.get("current_collection_fee")
    try:
        if isinstance(raw, Decimal):
            return raw
        if isinstance(raw, str):
            return Decimal(raw)
        if isinstance(raw, int) and not isinstance(raw, bool):
            return Decimal(raw)
    except InvalidOperation:
        pass
    raise SourceParseError(
        SourceErrorDetail(
            provider=AtomicAssetsMarketDataSource.provider_name,
            operation="get_floor_listing",
            message="AtomicAssets collection fee must be decimal-safe",
            retryable=False,
        )
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
) -> Observation:
    return Observation(
        observation_id=_observation_id(entity_id, metric, retrieved_at),
        entity_type="nft_collection_template",
        entity_id=entity_id,
        metric=metric,
        value=value,
        unit=unit,
        quote_currency=None,
        source_provider=AtomicAssetsMarketDataSource.provider_name,
        source_type=SourceType.MARKET_API,
        source_locator=locator,
        observed_at=retrieved_at,
        retrieved_at=retrieved_at,
        fresh_until=fresh_until,
        status=ObservationStatus.FRESH,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


def _missing_observation(
    *,
    entity_id: str,
    metric: str,
    unit: str,
    locator: str,
    retrieved_at: datetime,
) -> Observation:
    return Observation(
        observation_id=_observation_id(entity_id, metric, retrieved_at),
        entity_type="nft_collection_template",
        entity_id=entity_id,
        metric=metric,
        value=None,
        unit=unit,
        quote_currency=None,
        source_provider=AtomicAssetsMarketDataSource.provider_name,
        source_type=SourceType.MARKET_API,
        source_locator=locator,
        observed_at=None,
        retrieved_at=retrieved_at,
        fresh_until=retrieved_at,
        status=ObservationStatus.MISSING,
        metadata={"classification": "LIVE"},
    )


def _observation_id(entity_id: str, metric: str, retrieved_at: datetime) -> str:
    key = f"{AtomicAssetsMarketDataSource.provider_name}|{entity_id}|{metric}|{retrieved_at.isoformat()}"
    return str(uuid5(NAMESPACE_URL, key))
