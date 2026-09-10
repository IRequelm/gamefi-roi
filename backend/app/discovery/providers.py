"""Provider adapters for discovery. Failures are explicit and never become fake signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from statistics import mean
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config.settings import get_settings
from app.sources.coingecko import CoinGeckoMarketDataSource
from app.sources.market_data import TokenPriceRequest


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    status: str
    retrieved_at: datetime
    signals: tuple[dict[str, object], ...] = ()
    limitation: str | None = None


class GoogleTrendsProvider:
    homepage = "https://trends.google.com/"
    explore_url = "https://trends.google.com/trends/api/explore"
    widget_url = "https://trends.google.com/trends/api/widgetdata/multiline"

    def probe(self, *, timeout: int = 15) -> ProviderResult:
        return self.query(("GameFi", "DePIN"), timeframe="now 7-d", timeout=timeout)

    def query(
        self,
        keywords: tuple[str, ...],
        *,
        timeframe: str = "now 7-d",
        geo: str = "",
        timeout: int = 15,
    ) -> ProviderResult:
        retrieved = datetime.now(UTC)
        if not keywords:
            return ProviderResult("google_trends", "INVALID_REQUEST", retrieved, limitation="At least one keyword is required.")
        explore_request = {
            "comparisonItem": [{"keyword": keyword, "geo": geo, "time": timeframe} for keyword in keywords],
            "category": 0,
            "property": "",
        }
        try:
            explore_payload = _get_json(self.explore_url + "?hl=en-US&tz=0&req=" + quote(json.dumps(explore_request, separators=(",", ":"))), timeout)
            widget = next((item for item in explore_payload.get("widgets", []) if item.get("id") == "TIMESERIES"), None)
            if not widget or not widget.get("token") or not widget.get("request"):
                return ProviderResult("google_trends", "QUERY_UNAVAILABLE", retrieved, limitation="Explore response did not expose a TIMESERIES widget.")
            series_request = quote(json.dumps(widget["request"], separators=(",", ":")))
            series_payload = _get_json(self.widget_url + "?hl=en-US&tz=0&req=" + series_request + "&token=" + quote(str(widget["token"])), timeout)
            signals = _series_signals(series_payload, keywords=keywords, source_locator=self.widget_url, retrieved_at=retrieved)
            if not signals:
                return ProviderResult("google_trends", "QUERY_EMPTY", retrieved, limitation="TIMESERIES response contained no usable relative-index points.")
            return ProviderResult("google_trends", "LIVE", retrieved, tuple(signals))
        except Exception as exc:
            return ProviderResult("google_trends", "BLOCKED", retrieved, limitation=f"Live retrieval failed: {type(exc).__name__}: {exc}")


class CoinGeckoMarketProvider:
    """Discovery-facing adapter over the existing provenance-preserving market connector."""

    default_assets = ("akash-network", "aethir", "grass", "hivemapper")

    def query(self, provider_asset_ids: tuple[str, ...] = default_assets, *, timeout_seconds: int | None = None) -> ProviderResult:
        retrieved = datetime.now(UTC)
        if not provider_asset_ids:
            return ProviderResult("coingecko_market", "INVALID_REQUEST", retrieved, limitation="At least one CoinGecko asset id is required.")
        try:
            settings = get_settings()
            source = CoinGeckoMarketDataSource(settings)
            try:
                observations = source.get_token_prices(
                    TokenPriceRequest(
                        provider_asset_ids=provider_asset_ids,
                        quote_currency="USD",
                        freshness_window=timedelta(seconds=timeout_seconds or settings.market_data_price_freshness_seconds),
                    )
                )
            finally:
                source.close()
            signals = tuple(
                {
                    "name": "market_price_usd",
                    "asset_id": asset_id,
                    "value": str(observation.value) if observation.value is not None else None,
                    "unit": "USD",
                    "source": "coingecko",
                    "source_locator": observation.source_locator,
                    "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
                    "retrieved_at": observation.retrieved_at.isoformat(),
                    "freshness": observation.status.value,
                    "status": "LIVE" if observation.value is not None else "MISSING",
                    "explanation": "Current token quote only; it is not an earnings or ROI estimate.",
                }
                for asset_id, observation in zip(provider_asset_ids, observations, strict=True)
            )
            if not any(signal["value"] is not None for signal in signals):
                return ProviderResult("coingecko_market", "QUERY_EMPTY", retrieved, signals, "CoinGecko returned no usable token prices.")
            return ProviderResult("coingecko_market", "LIVE", retrieved, signals)
        except Exception as exc:
            return ProviderResult("coingecko_market", "BLOCKED", retrieved, limitation=f"Live market retrieval failed: {type(exc).__name__}: {exc}")


def _get_json(url: str, timeout: int) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "GamCryp-discovery/1.0"})
    with urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"HTTP {status} from Google Trends")
        raw = response.read().decode("utf-8-sig")
    if raw.startswith(")]}'"):
        raw = raw[4:]
        if raw.startswith(","):
            raw = raw[1:]
    return json.loads(raw.lstrip("\n"))


def _series_signals(payload: dict[str, object], *, keywords: tuple[str, ...], source_locator: str, retrieved_at: datetime) -> list[dict[str, object]]:
    timeline = payload.get("default", {}).get("timelineData", []) if isinstance(payload.get("default"), dict) else []
    if not timeline:
        return []
    values_by_keyword: dict[str, list[float]] = {}
    for point in timeline:
        if not isinstance(point, dict):
            continue
        values = point.get("value", [])
        for index, value in enumerate(values if isinstance(values, list) else []):
            if isinstance(value, (int, float)):
                keyword = keywords[index] if index < len(keywords) else f"keyword_{index}"
                values_by_keyword.setdefault(keyword, []).append(float(value))
    signals: list[dict[str, object]] = []
    for keyword, values in values_by_keyword.items():
        if not values:
            continue
        window = max(1, len(values) // 3)
        baseline = mean(values[:-window]) if len(values) > window else mean(values)
        current = mean(values[-window:])
        direction = "UP" if current > baseline * 1.05 else "DOWN" if current < baseline * 0.95 else "FLAT"
        signals.append({
            "name": "search_momentum",
            "keyword": keyword,
            "value": round(current, 2),
            "baseline": round(baseline, 2),
            "direction": direction,
            "source": "google_trends",
            "source_locator": source_locator,
            "observed_at": retrieved_at.isoformat(),
            "status": "LIVE_RELATIVE_INDEX",
            "explanation": f"Google Trends relative interest {direction.lower()} versus the preceding comparable window; not absolute search volume.",
        })
    return signals


class UnavailableProvider:
    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def probe(self) -> ProviderResult:
        return ProviderResult(self.name, "BLOCKED", datetime.now(UTC), limitation=self.reason)
