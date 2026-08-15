"""CoinGecko market-data source connector."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid5, NAMESPACE_URL

import httpx

from app.config.settings import Settings, get_settings
from app.sources.errors import SourceErrorDetail, SourceParseError
from app.sources.http import SourceHttpClient
from app.sources.market_data import TokenPriceRequest, UnsupportedMarketDataSource
from app.sources.observations import Observation, ObservationStatus, SourceType


class CoinGeckoMarketDataSource(UnsupportedMarketDataSource):
    provider_name = "coingecko"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        active_settings = settings or get_settings()
        self._api_key = active_settings.coingecko_api_key
        self._client = SourceHttpClient(
            provider=self.provider_name,
            base_url=active_settings.coingecko_base_url,
            timeout_seconds=active_settings.market_data_http_timeout_seconds,
            max_retries=active_settings.market_data_http_max_retries,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_token_prices(self, request: TokenPriceRequest) -> list[Observation]:
        params = {
            "ids": ",".join(request.provider_asset_ids),
            "vs_currencies": request.quote_currency.lower(),
            "include_last_updated_at": "true",
            "precision": "full",
        }
        headers = {"x-cg-demo-api-key": self._api_key} if self._api_key else None
        payload = self._client.get_json(
            "/simple/price",
            params=params,
            headers=headers,
            operation="get_token_prices",
        )
        retrieved_at = datetime.now(UTC)
        locator = self._client.source_locator("/simple/price", params)

        return [
            self._observation_from_price_payload(
                provider_asset_id=provider_asset_id,
                quote_currency=request.quote_currency,
                payload=payload.get(provider_asset_id),
                retrieved_at=retrieved_at,
                fresh_until=retrieved_at + request.freshness_window,
                locator=locator,
            )
            for provider_asset_id in request.provider_asset_ids
        ]

    def _observation_from_price_payload(
        self,
        *,
        provider_asset_id: str,
        quote_currency: str,
        payload: Any,
        retrieved_at: datetime,
        fresh_until: datetime,
        locator: str,
    ) -> Observation:
        quote_key = quote_currency.lower()
        entity_id = f"coingecko:{provider_asset_id}"

        if not isinstance(payload, dict) or quote_key not in payload:
            return self._missing_observation(
                entity_id=entity_id,
                provider_asset_id=provider_asset_id,
                quote_currency=quote_currency,
                retrieved_at=retrieved_at,
                locator=locator,
            )

        value = payload[quote_key]
        if not isinstance(value, Decimal):
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation="get_token_prices",
                    message=f"Price for {provider_asset_id}/{quote_currency} was not decimal-safe",
                    retryable=False,
                )
            )

        observed_at = self._observed_at(payload)
        observation_id = self._observation_id(
            entity_id=entity_id,
            metric="token.price",
            quote_currency=quote_currency,
            observed_at=observed_at or retrieved_at,
        )

        return Observation(
            observation_id=observation_id,
            entity_type="asset",
            entity_id=entity_id,
            metric="token.price",
            value=value,
            unit=quote_currency.upper(),
            quote_currency=quote_currency,
            source_provider=self.provider_name,
            source_type=SourceType.MARKET_API,
            source_locator=locator,
            observed_at=observed_at,
            retrieved_at=retrieved_at,
            fresh_until=fresh_until,
            status=ObservationStatus.FRESH,
            metadata={"classification": "LIVE", "provider_asset_id": provider_asset_id},
        )

    def _missing_observation(
        self,
        *,
        entity_id: str,
        provider_asset_id: str,
        quote_currency: str,
        retrieved_at: datetime,
        locator: str,
    ) -> Observation:
        return Observation(
            observation_id=self._observation_id(
                entity_id=entity_id,
                metric="token.price",
                quote_currency=quote_currency,
                observed_at=retrieved_at,
            ),
            entity_type="asset",
            entity_id=entity_id,
            metric="token.price",
            value=None,
            unit=quote_currency.upper(),
            quote_currency=quote_currency,
            source_provider=self.provider_name,
            source_type=SourceType.MARKET_API,
            source_locator=locator,
            observed_at=None,
            retrieved_at=retrieved_at,
            fresh_until=retrieved_at,
            status=ObservationStatus.MISSING,
            metadata={"provider_asset_id": provider_asset_id},
        )

    @staticmethod
    def _observed_at(payload: dict[str, Any]) -> datetime | None:
        raw_timestamp = payload.get("last_updated_at")
        if raw_timestamp is None:
            return None
        if not isinstance(raw_timestamp, int):
            raise SourceParseError(
                SourceErrorDetail(
                    provider=CoinGeckoMarketDataSource.provider_name,
                    operation="get_token_prices",
                    message="last_updated_at must be a UNIX integer timestamp",
                    retryable=False,
                )
            )
        return datetime.fromtimestamp(raw_timestamp, UTC)

    @staticmethod
    def _observation_id(
        *,
        entity_id: str,
        metric: str,
        quote_currency: str,
        observed_at: datetime,
    ) -> str:
        key = f"{CoinGeckoMarketDataSource.provider_name}|{entity_id}|{metric}|{quote_currency.upper()}|{observed_at.isoformat()}"
        return str(uuid5(NAMESPACE_URL, key))
