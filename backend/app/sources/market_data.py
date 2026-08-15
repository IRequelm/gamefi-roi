"""Provider-neutral market-data source contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from app.sources.errors import SourceErrorDetail, UnsupportedSourceCapability
from app.sources.observations import Observation


@dataclass(frozen=True)
class TokenPriceRequest:
    provider_asset_ids: tuple[str, ...]
    quote_currency: str
    freshness_window: timedelta


@dataclass(frozen=True)
class PoolStateRequest:
    pool_id: str
    freshness_window: timedelta


@dataclass(frozen=True)
class SellQuoteRequest:
    asset_id: str
    amount: str
    target_asset_id: str
    freshness_window: timedelta


@dataclass(frozen=True)
class OhlcvRequest:
    asset_id: str
    quote_currency: str
    days: int
    freshness_window: timedelta


class MarketDataSource(Protocol):
    provider_name: str

    def get_token_prices(self, request: TokenPriceRequest) -> Sequence[Observation]:
        ...


class UnsupportedMarketDataSource:
    provider_name: str

    def get_pool_state(self, request: PoolStateRequest) -> Sequence[Observation]:
        raise UnsupportedSourceCapability(
            SourceErrorDetail(
                provider=self.provider_name,
                operation="get_pool_state",
                message="Provider does not implement pool-state observations",
                retryable=False,
            )
        )

    def quote_sell(self, request: SellQuoteRequest) -> Sequence[Observation]:
        raise UnsupportedSourceCapability(
            SourceErrorDetail(
                provider=self.provider_name,
                operation="quote_sell",
                message="Provider does not implement executable sell quotes",
                retryable=False,
            )
        )

    def get_ohlcv(self, request: OhlcvRequest) -> Sequence[Observation]:
        raise UnsupportedSourceCapability(
            SourceErrorDetail(
                provider=self.provider_name,
                operation="get_ohlcv",
                message="Provider does not implement OHLCV observations",
                retryable=False,
            )
        )
