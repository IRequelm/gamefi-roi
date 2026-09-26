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
from app.sources.errors import InsufficientMarketDepth, SourceErrorDetail, SourceParseError
from app.sources.http import SourceHttpClient
from app.sources.observations import Observation, ObservationStatus, SourceType


@dataclass(frozen=True)
class AtomicAssetsFloorRequest:
    collection_name: str
    schema_name: str
    template_id: str
    listing_symbol: str
    freshness_window: timedelta
    quantity: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or not 1 <= self.quantity <= 100:
            raise ValueError("AtomicAssets listing quantity must be an integer between 1 and 100")


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
            "limit": str(request.quantity),
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

        if len(data) < request.quantity:
            raise InsufficientMarketDepth(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation="get_floor_listing",
                    message=(
                        f"AtomicAssets has {len(data)} active listings for {request.template_id}; "
                        f"strategy requires {request.quantity} distinct tool listings to price entry and exit."
                    ),
                    retryable=False,
                )
            )

        sales = data[: request.quantity]
        parsed_sales: list[tuple[dict[str, Any], Decimal, str, Decimal]] = []
        for sale in sales:
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
            if price_unit != request.listing_symbol.upper():
                raise SourceParseError(
                    SourceErrorDetail(
                        provider=self.provider_name,
                        operation="get_floor_listing",
                        message=f"AtomicAssets listing quote currency {price_unit} does not match {request.listing_symbol.upper()}",
                        retryable=False,
                    )
                )
            if market_fee_ratio < Decimal("0") or market_fee_ratio > Decimal("1"):
                raise SourceParseError(
                    SourceErrorDetail(
                        provider=self.provider_name,
                        operation="get_floor_listing",
                        message="AtomicAssets collection market fee ratio must be between zero and one",
                        retryable=False,
                    )
                )
            parsed_sales.append((sale, price_value, price_unit, market_fee_ratio))

        symbols = {entry[2] for entry in parsed_sales}
        fees = {entry[3] for entry in parsed_sales}
        if len(symbols) != 1 or len(fees) != 1:
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation="get_floor_listing",
                    message="AtomicAssets basket listings must use one quote currency and one collection fee",
                    retryable=False,
                )
            )
        floor_sale, floor_price, price_unit, market_fee_ratio = parsed_sales[0]
        basket_cost = Decimal("0")
        basket_exit_value = Decimal("0")
        for _, price, _, fee in parsed_sales:
            basket_cost = FINANCIAL_DECIMAL_CONTEXT.add(basket_cost, price)
            net_sale_value = FINANCIAL_DECIMAL_CONTEXT.multiply(
                price, FINANCIAL_DECIMAL_CONTEXT.subtract(Decimal("1"), fee)
            )
            basket_exit_value = FINANCIAL_DECIMAL_CONTEXT.add(basket_exit_value, net_sale_value)
        sale_ids = [str(sale.get("sale_id")) for sale, _, _, _ in parsed_sales if sale.get("sale_id") is not None]
        if len(sale_ids) != request.quantity or len(set(sale_ids)) != request.quantity:
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation="get_floor_listing",
                    message="AtomicAssets basket must contain a distinct sale ID for every requested listing",
                    retryable=False,
                )
            )
        metadata = {
            "classification": "LIVE",
            "collection_name": request.collection_name,
            "schema_name": request.schema_name,
            "template_id": request.template_id,
            "sale_id": str(floor_sale.get("sale_id")),
            "basket_quantity": request.quantity,
            "basket_sale_ids": sale_ids,
        }

        return (
            _market_observation(
                entity_id=entity_id,
                metric="atomicassets.nft.floor_price",
                value=floor_price,
                unit=price_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata={**metadata, "basket_quantity": 1, "basket_sale_ids": [metadata["sale_id"]]},
            ),
            _market_observation(
                entity_id=entity_id,
                metric="atomicassets.nft.listing_basket_cost",
                value=basket_cost,
                unit=price_unit,
                locator=locator,
                retrieved_at=retrieved_at,
                fresh_until=fresh_until,
                metadata=metadata,
            ),
            _market_observation(
                entity_id=entity_id,
                metric="atomicassets.nft.listing_basket_exit_value",
                value=basket_exit_value,
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
