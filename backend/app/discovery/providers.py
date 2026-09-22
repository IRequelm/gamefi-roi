"""Provider adapters for discovery. Failures are explicit and never become fake signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
import json
import os
import re
from pathlib import Path
from statistics import mean
from urllib.parse import quote
from urllib.error import HTTPError
from http.cookiejar import MozillaCookieJar
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen
from xml.etree import ElementTree

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
    related_widget_url = "https://trends.google.com/trends/api/widgetdata/relatedsearches"
    trending_rss_url = "https://trends.google.com/trending/rss"
    default_keywords = ("GameFi", "DePIN", "crypto node", "GPU compute", "storage node")

    def __init__(self, *, session_enabled: bool = True) -> None:
        # Google Trends serves the public homepage successfully but commonly
        # rate-limits stateless API calls.  Keep a short-lived cookie session
        # for the explore/widget requests; the stateless mode is retained for
        # deterministic unit tests and offline callers.
        self.session_enabled = session_enabled
        self._session_warmed = False
        self._cookie_file = (
            Path(
                os.getenv(
                    "GAMEFI_DISCOVERY_GOOGLE_TRENDS_COOKIE_FILE",
                    "data/local/discovery/google_trends.cookies",
                )
            )
            if session_enabled
            else None
        )
        self._cookie_jar = MozillaCookieJar(str(self._cookie_file)) if self._cookie_file else None
        if self._cookie_jar is not None and self._cookie_file.is_file():
            try:
                self._cookie_jar.load(ignore_discard=True, ignore_expires=True)
            except (OSError, ValueError):
                # A stale/corrupt public-session cookie must never block the
                # provider; start a fresh session and keep the result explicit.
                self._cookie_jar = MozillaCookieJar(str(self._cookie_file))
        self._opener = build_opener(HTTPCookieProcessor(self._cookie_jar)) if self._cookie_jar else None

    def probe(self, *, timeout: int = 15) -> ProviderResult:
        return self.query(
            _configured_keywords(),
            timeframe="now 7-d",
            geo=_configured_geo(),
            timeout=timeout,
        )

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
        if self.session_enabled:
            self._warm_session(timeout)
        explore_request = {
            "comparisonItem": [{"keyword": keyword, "geo": geo, "time": timeframe} for keyword in keywords],
            "category": 0,
            "property": "",
        }
        try:
            explore_payload = _get_json(
                self.explore_url + "?hl=en-US&tz=0&req=" + quote(json.dumps(explore_request, separators=(",", ":"))),
                timeout,
                open_url=self._open_url,
            )
            widgets = explore_payload.get("widgets", [])
            signals: list[dict[str, object]] = []
            timeseries = next((item for item in widgets if isinstance(item, dict) and item.get("id") == "TIMESERIES"), None)
            if timeseries and timeseries.get("token") and timeseries.get("request"):
                series_request = quote(json.dumps(timeseries["request"], separators=(",", ":")))
                series_payload = _get_json(
                    self.widget_url + "?hl=en-US&tz=0&req=" + series_request + "&token=" + quote(str(timeseries["token"])),
                    timeout,
                    open_url=self._open_url,
                )
                signals.extend(_series_signals(series_payload, keywords=keywords, source_locator=self.widget_url, retrieved_at=retrieved))
            # The live Explore API names these widgets RELATED_QUERIES_0,
            # RELATED_QUERIES_1, ... (the un-suffixed name is used by older
            # fixtures). Read every keyword-specific widget so trend signals
            # can produce actual research leads rather than only reporting
            # momentum for the seed terms.
            related_widgets = [
                item for item in widgets
                if isinstance(item, dict) and str(item.get("id", "")).startswith("RELATED_QUERIES")
            ]
            for related in related_widgets:
                if not related.get("token") or not related.get("request"):
                    continue
                related_request = quote(json.dumps(related["request"], separators=(",", ":")))
                related_payload = _get_json(
                    self.related_widget_url + "?hl=en-US&tz=0&req=" + related_request + "&token=" + quote(str(related["token"])),
                    timeout,
                    open_url=self._open_url,
                )
                signals.extend(_related_query_signals(related_payload, source_locator=self.widget_url, retrieved_at=retrieved))
            if not signals:
                return ProviderResult("google_trends", "QUERY_EMPTY", retrieved, limitation="Google Trends response contained no usable timeseries or related-query signals.")
            return ProviderResult("google_trends", "LIVE", retrieved, tuple(signals))
        except Exception as exc:
            # Explore/widget endpoints are frequently rate-limited even when
            # the official Google Trends RSS feed remains available. The RSS
            # path is deliberately research-only: it yields relevant trend
            # names and approximate traffic labels, never a search-volume or
            # ROI claim.
            if isinstance(exc, HTTPError) and exc.code in {403, 429}:
                fallback = _trending_rss_signals(
                    keywords=keywords,
                    geo=geo,
                    source_locator=self.trending_rss_url,
                    retrieved_at=retrieved,
                    timeout=timeout,
                    open_url=self._open_url,
                )
                if fallback:
                    return ProviderResult("google_trends", "LIVE_RSS", retrieved, tuple(fallback), "Explore API rate-limited; RSS research leads used.")
                return ProviderResult("google_trends", "QUERY_EMPTY", retrieved, limitation="Google Trends Explore API was rate-limited and the official RSS feed contained no relevant crypto/Web3 research lead.")
            return ProviderResult("google_trends", "BLOCKED", retrieved, limitation=f"Live retrieval failed: {type(exc).__name__}: {exc}")

    def _warm_session(self, timeout: int) -> None:
        if self._session_warmed or self._opener is None:
            return
        try:
            request = Request(self.homepage, headers=_trends_headers(self.homepage))
            with self._opener.open(request, timeout=timeout) as response:
                response.read(1024)
            self._save_cookie_jar()
            self._session_warmed = True
        except Exception:
            # The API request below still gets a chance to return an explicit
            # live/blocked result if the homepage warm-up is unavailable.
            self._session_warmed = True

    def _open_url(self, request: Request, *, timeout: int):
        if self._opener is not None:
            response = self._opener.open(request, timeout=timeout)
            self._save_cookie_jar()
            return response
        return urlopen(request, timeout=timeout)

    def _save_cookie_jar(self) -> None:
        if self._cookie_jar is None or self._cookie_file is None:
            return
        try:
            self._cookie_file.parent.mkdir(parents=True, exist_ok=True)
            self._cookie_jar.save(ignore_discard=True, ignore_expires=True)
        except OSError:
            # Cookie persistence is an optimization, never a provider
            # readiness requirement.
            return


class GoogleNewsResearchProvider:
    """Bounded Google News RSS fallback for research leads only.

    Google News results are deliberately never represented as search volume,
    demand, trend strength, or ROI. They are article-level discovery hints
    used only when the Google Trends Explore/RSS path has no usable signal.
    Every resulting lead still requires official identity/evidence review and
    the operator's explicit ``SITEYE_EKLE`` approval before catalog admission.
    """

    rss_search_url = "https://news.google.com/rss/search"
    default_geo = "US"
    default_max_age_days = 180

    def probe(self, *, timeout: int = 15) -> ProviderResult:
        retrieved = datetime.now(UTC)
        keywords = _configured_keywords()
        max_age_days = _google_news_max_age_days()
        signals: list[dict[str, object]] = []
        seen: set[str] = set()
        for keyword in keywords:
            url = (
                f"{self.rss_search_url}?q={quote(keyword)}"
                f"&hl=en-US&gl={self.default_geo}&ceid={self.default_geo}:en"
            )
            request = Request(
                url,
                headers={"User-Agent": "GamCryp-discovery/1.0", "Accept": "application/rss+xml"},
            )
            try:
                with urlopen(request, timeout=timeout) as response:
                    root = ElementTree.fromstring(response.read())
            except Exception:
                # One unavailable query must not hide useful results from the
                # other configured research seeds.
                continue
            for item in root.findall(".//item"):
                title = _xml_text(item.find("title"))
                if not title:
                    continue
                normalized = title.casefold()
                published_text = _xml_text(item.find("pubDate"))
                if published_text and not _is_recent_news(published_text, retrieved, max_age_days=max_age_days):
                    continue
                if (
                    normalized in seen
                    or not _google_news_relevant(normalized, keyword)
                    or not _google_news_researchable_title(title)
                ):
                    continue
                seen.add(normalized)
                source_locator = _xml_text(item.find("link")) or url
                published = published_text or retrieved.isoformat()
                signals.append(
                    {
                        "name": "related_query",
                        "keyword": title,
                        "candidate_hint": _google_news_candidate_hint(title),
                        "value": None,
                        "source": "google_news",
                        "source_locator": source_locator,
                        "search_locator": url,
                        "observed_at": published,
                        "status": "LIVE_GOOGLE_NEWS_RESEARCH_LEAD",
                        "explanation": (
                            "Google News article lead for research only; it is not Google Trends volume, "
                            "proof of official identity, demand, revenue, or ROI."
                        ),
                    }
                )
                if len(signals) >= 25:
                    return ProviderResult("google_news", "LIVE_RESEARCH", retrieved, tuple(signals))
        if signals:
            return ProviderResult("google_news", "LIVE_RESEARCH", retrieved, tuple(signals))
        return ProviderResult(
            "google_news",
            "QUERY_EMPTY",
            retrieved,
            limitation="Google News RSS returned no relevant research lead for the configured seeds.",
        )


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


def _trends_headers(referer: str | None = None) -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        **({"Referer": referer} if referer else {}),
        "X-Requested-With": "XMLHttpRequest",
    }


def _get_json(url: str, timeout: int, *, open_url=urlopen) -> dict[str, object]:
    request = Request(url, headers=_trends_headers("https://trends.google.com/"))
    with open_url(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"HTTP {status} from Google Trends")
        raw = response.read().decode("utf-8-sig")
    if raw.startswith(")]}'"):
        raw = raw[4:]
        if raw.startswith(","):
            raw = raw[1:]
    return json.loads(raw.lstrip("\n"))


def _configured_keywords() -> tuple[str, ...]:
    raw = os.getenv("GAMEFI_DISCOVERY_GOOGLE_KEYWORDS", "")
    values = tuple(item.strip() for item in raw.split(",") if item.strip()) if raw.strip() else GoogleTrendsProvider.default_keywords
    unique = tuple(dict.fromkeys(values))
    return unique[:5] or GoogleTrendsProvider.default_keywords


def _configured_geo() -> str:
    """Use a bounded regional Explore request instead of the noisier global default."""
    value = os.getenv("GAMEFI_DISCOVERY_GOOGLE_GEO", "US").strip().upper()
    return value if re.fullmatch(r"[A-Z]{2}", value) else "US"


def _google_news_max_age_days() -> int:
    raw = os.getenv("GAMEFI_DISCOVERY_GOOGLE_NEWS_MAX_AGE_DAYS", str(GoogleNewsResearchProvider.default_max_age_days)).strip()
    try:
        return max(1, min(int(raw), 3650))
    except ValueError:
        return GoogleNewsResearchProvider.default_max_age_days


def _is_recent_news(value: str, retrieved_at: datetime, *, max_age_days: int) -> bool:
    try:
        observed = parsedate_to_datetime(value)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=UTC)
    except (TypeError, ValueError, OverflowError):
        try:
            observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=UTC)
        except (TypeError, ValueError, OverflowError):
            return False
    return retrieved_at - timedelta(days=max_age_days) <= observed.astimezone(UTC) <= retrieved_at + timedelta(days=1)


def _google_news_relevant(title: str, keyword: str) -> bool:
    domain_terms = {
        "airdrop", "blockchain", "chain", "coin", "compute", "crypto", "defi",
        "depin", "ethereum", "gamefi", "gpu", "mining", "node", "points",
        "protocol", "solana", "staking", "storage", "token", "web3", "yield",
    }
    keyword_terms = {term.casefold() for term in keyword.split() if len(term) >= 4}
    return any(_contains_term(title, term) for term in (*domain_terms, *keyword_terms))


def _google_news_researchable_title(title: str) -> bool:
    """Reject generic explainers and market-index pages as candidate leads."""
    normalized = title.casefold().strip()
    generic_patterns = (
        r"^what\s+is\s+",
        r"^how\s+(?:does|do|to)\s+",
        r"^top\s+.*\b(?:coins?|tokens?)\b",
        r"^gamefi\s+news\b",
        r"^does\s+gamefi\b",
        r"^what\s+are\s+the\s+top\s+crypto\s+trends\b",
        r"^why\s+gamefi\b",
        r"^inside\s+gamefi\b",
        r"^gamefi\s+set\s+to\b",
        r"^new\s+developments\s+in\s+gamefi\b",
        r"^play\s+to\s+earn\b",
        r"^gamefi\s+(?:2\.0|tokenomics|nfts?)\b",
        r"^depin\s*[-:]",
        r"^depin\s+\d{4}\b",
        r"^decentralized\s+physical\s+infrastructure\b",
        r"^the\s+next\s+big\s+depin\b",
        r"^a\s+bitcoin-mining\s+device\b",
        r"^hashed\s+and\b",
        r"^bitrue\s+announces\b",
        r"^\W*top\s+#?depin\s+projects\b",
        r"^web3\s+is\s+dead\b",
        r"^understanding\s+the\s+crypto\s+investment\s+flywheel\b",
        r"^blockchain\s+depin\s+infrastructure\s+networks?\s+guide\b",
        r"^depin\s+growth\s+powers\b",
        r"^mid-day\s+narrative\s+shift\b",
        r"^depin\s+vs\.\s+big\s+tech\b",
        r"^best\s+depin\s+cryptocurrencies\b",
        r"^learn\s+all\s+crypto\s+topics\b",
        r"^inside\s+solana\s+incubator\s+cohort\b",
        r"\blive\s+prices?\b",
        r"\bmarket\s+cap\b",
        r"\bexplained\b",
        r"\bstate\s+of\b",
        r"\b(?:market|sector|industry)\b",
        r"\b(?:price|liquidity|rally|rallies|rises?|surges?|jumps?|soars?|pullback|bearish|bullish|funding|optimism|dips?)\b",
        r"\b(?:trust\s+wallet|sony\s+bank)\b",
        r"^\d+\s+best\b",
        r"^gamefi\s*[-:]\s*(?:page|news|update)\b",
        r"^gamefi\s*[-:]\s*[a-z0-9.-]+$",
        r"^gamefi\s+(?:is|in\s+\d{4})\b",
        r"^gamefi\s+tokens?\s+(?:fall|rally|rise)\b",
        r"\b\d+%\s+of\s+.*\b(?:dead|failed|collapse)\b",
        r"\bprice\s+prediction\b",
        r"^new\s+npm\s+supply\s+chain\b",
        r"^bitcoin\s+core\b",
        r"^run\s+a\s+bitcoin\s+lightning\s+node\b",
        r"^ethereum\s+nodes?\b",
        r"^u\.s\.\s+military\b",
        r"^america\s+runs\s+a\s+bitcoin\s+node\b",
        r"^node\s+monthly\b",
        r"^cambridge\s+research\b",
        r"^node\.js\b",
        r"^(?:u\.s\.?|us)\s+admiral\b",
        r"^bitcoin\s+clears\b",
        r"^bitcoin\s+",
        r"^buterin\s+says\b",
        r"^visa\s+expands\b",
        r"^ontology\s+forces\b",
        r"\bsecurity\s+flaw\b",
        r"\bmalicious\s+activity\b",
        r"\bgovernment\s+(?:running|runs)\b",
        r"\bvalidator\s+node\s+launch\b",
        r"\b(?:shuts?\s+down|shutdown|failed\s+to\s+scale|failing\s+to\s+scale|ceases?\s+operations?)\b",
    )
    return not any(re.search(pattern, normalized) for pattern in generic_patterns)


def _google_news_candidate_hint(title: str) -> str | None:
    """Extract a project-like name without treating the article title as identity."""
    clean = re.sub(r"\s+[-|]\s+[^-|]+$", "", title).strip()
    clean = re.sub(r"\s+", " ", clean)
    named_ticker = re.search(
        r"\b([A-Z][A-Za-z0-9.-]*(?:\s+[A-Z][A-Za-z0-9.-]*){0,3})\s*\(([A-Z0-9-]{2,})\)",
        clean,
    )
    if named_ticker:
        return f"{named_ticker.group(1).strip()} ({named_ticker.group(2).strip()})"
    ticker = re.search(r"\b([A-Z]{2,}[A-Z0-9-]*)\s*\(([^)]+)\)", clean)
    if ticker:
        return f"{ticker.group(1)} ({ticker.group(2).strip()})"
    target = re.search(
        r"\b(?:integrates|adds|acquires|partners\s+with|announces)\s+(?:the\s+)?([A-Z][A-Za-z0-9.-]*(?:\s+[A-Z][A-Za-z0-9.-]*){0,2})",
        clean,
        flags=re.IGNORECASE,
    )
    if target:
        target_name = re.split(r"\s+(?:as|for|to|in|on|of)\b", target.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
        first_token = target_name.split()[0] if target_name.split() else ""
        if re.fullmatch(r"[A-Z0-9]{2,}", first_token):
            target_name = first_token
        return _clean_google_news_hint(target_name)
    possessive = re.match(r"^([A-Z][A-Za-z0-9.-]+)[’']s\b", clean)
    if possessive:
        return possessive.group(1).strip(" .,:;-")
    leading = re.match(
        r"^(?:from\s+launch\s+to\s+potential:\s*)?(?:can\s+)?([A-Z][A-Za-z0-9.-]*(?:\s+(?:and\s+)?[A-Z][A-Za-z0-9.-]*){0,3})(?:'s|\s+(?:is|launches|raises|shuts|acquires|integrates|jointly|outlines|strengthens|announces|deep\s+dive|position|meets|officially))\b",
        clean,
        flags=re.IGNORECASE,
    )
    if leading:
        return _clean_google_news_hint(leading.group(1))
    procedural = re.match(r"^(?:run|install)\s+(?:a|an|the)\s+([^:]+):", clean, flags=re.IGNORECASE)
    if procedural:
        return _clean_google_news_hint(procedural.group(1))
    deep_dive = re.match(r"^([A-Z][A-Za-z0-9.-]*(?:\s+[A-Z][A-Za-z0-9.-]*){0,2})\s+deep\s+dive\b", clean, flags=re.IGNORECASE)
    return _clean_google_news_hint(deep_dive.group(1)) if deep_dive else None


def _clean_google_news_hint(value: str) -> str:
    cleaned = value.strip(" .,:;-")
    cleaned = re.sub(
        r"^(?:solana|ethereum|bitcoin|web3|crypto)\s+(?:depin\s+)?(?:startup|company|project)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" .,:;-")


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


def _related_query_signals(payload: dict[str, object], *, source_locator: str, retrieved_at: datetime) -> list[dict[str, object]]:
    """Extract Google Trends related searches as research leads, never as demand volume."""
    default = payload.get("default")
    ranked_lists = default.get("rankedList") if isinstance(default, dict) else None
    if not isinstance(ranked_lists, list):
        return []
    signals: list[dict[str, object]] = []
    for ranked_list in ranked_lists:
        if not isinstance(ranked_list, dict):
            continue
        for item in ranked_list.get("rankedKeyword", []):
            if not isinstance(item, dict):
                continue
            query = item.get("query")
            value = item.get("value")
            if not isinstance(query, str) or not query.strip():
                continue
            signals.append({
                "name": "related_query",
                "keyword": query.strip(),
                "value": value if isinstance(value, (int, float, str)) else None,
                "source": "google_trends",
                "source_locator": source_locator,
                "observed_at": retrieved_at.isoformat(),
                "status": "LIVE_RELATED_QUERY",
                "explanation": "Google Trends related-search lead for research only; not proof of product demand, revenue, or ROI.",
            })
    return signals


def _trending_rss_signals(
    *,
    keywords: tuple[str, ...],
    geo: str,
    source_locator: str,
    retrieved_at: datetime,
    timeout: int,
    open_url=urlopen,
) -> list[dict[str, object]]:
    """Read official Google Trends RSS as a bounded research-lead fallback."""
    geos = (geo,) if geo else ("US", "TR")
    domain_terms = {
        "airdrop", "blockchain", "chain", "coin", "compute", "crypto", "defi",
        "depin", "ethereum", "gamefi", "gpu", "mining", "node", "points",
        "protocol", "solana", "staking", "storage", "token", "web3", "yield",
    }
    keyword_terms = {term.casefold() for keyword in keywords for term in keyword.split() if len(term) >= 4}
    signals: list[dict[str, object]] = []
    seen: set[str] = set()
    for current_geo in geos:
        url = f"{source_locator}?geo={quote(current_geo)}"
        request = Request(url, headers={**_trends_headers("https://trends.google.com/trending/rss"), "Accept": "application/rss+xml"})
        with open_url(request, timeout=timeout) as response:
            raw = response.read()
        root = ElementTree.fromstring(raw)
        for item in root.findall(".//item"):
            title = _xml_text(item.find("title"))
            if not title:
                continue
            normalized = title.casefold()
            relevant_terms = (*domain_terms, *keyword_terms)
            if normalized in seen or not any(_contains_term(normalized, term) for term in relevant_terms):
                continue
            seen.add(normalized)
            traffic = _xml_text(item.find("approx_traffic"))
            signals.append({
                "name": "related_query",
                "keyword": title,
                "value": traffic or None,
                "source": "google_trends",
                "source_locator": url,
                "observed_at": retrieved_at.isoformat(),
                "status": "LIVE_RSS_RESEARCH_LEAD",
                "explanation": "Official Google Trends RSS research lead; approximate traffic is not absolute search volume, demand, revenue, or ROI.",
            })
            if len(signals) >= 25:
                return signals
    return signals


def _xml_text(node: ElementTree.Element | None) -> str:
    return (node.text or "").strip() if node is not None and node.text else ""


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


class XDiscoveryProvider:
    """Optional X search adapter; disabled by default so unpaid API credits are not consumed."""

    def probe(self) -> ProviderResult:
        retrieved = datetime.now(UTC)
        if os.getenv("GAMEFI_DISCOVERY_X_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
            return ProviderResult("x_api", "DISABLED", retrieved, limitation="X discovery is disabled; set GAMEFI_DISCOVERY_X_ENABLED=true only when API access is authorized.")
        try:
            from app.distribution.x_intelligence import XIntelligenceCollector

            state = XIntelligenceCollector().collect(now=retrieved)
            if state.get("status") != "LIVE":
                return ProviderResult("x_api", "BLOCKED", retrieved, limitation=str(state.get("limitation") or "X intelligence did not return a live result."))
            signals = tuple(_x_signals(state, retrieved_at=retrieved))
            return ProviderResult("x_api", "LIVE" if signals else "QUERY_EMPTY", retrieved, signals, None if signals else "X returned no usable recent posts.")
        except Exception as exc:
            return ProviderResult("x_api", "BLOCKED", retrieved, limitation=f"Live X discovery failed: {type(exc).__name__}: {exc}")


def _x_signals(state: dict[str, object], *, retrieved_at: datetime) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for post in state.get("top_posts", []) if isinstance(state.get("top_posts"), list) else []:
        if not isinstance(post, dict) or not post.get("text_excerpt"):
            continue
        signals.append({
            "name": "social_momentum",
            "candidate_hint": str(post.get("text_excerpt"))[:280],
            "source_account": post.get("source_account"),
            "value": post.get("engagement_score"),
            "source": "x_api",
            "source_locator": post.get("original_post_url"),
            "observed_at": post.get("discovered_at") or retrieved_at.isoformat(),
            "status": "LIVE_SOCIAL_SIGNAL",
            "explanation": "Recent X engagement signal used only as a research lead; it does not establish official product identity, safety, earnings, or ROI.",
        })
    return signals


class UnavailableProvider:
    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def probe(self) -> ProviderResult:
        return ProviderResult(self.name, "BLOCKED", datetime.now(UTC), limitation=self.reason)
