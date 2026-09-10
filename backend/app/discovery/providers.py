"""Provider adapters for discovery. Failures are explicit and never become fake signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    status: str
    retrieved_at: datetime
    signals: tuple[dict[str, object], ...] = ()
    limitation: str | None = None


class GoogleTrendsProvider:
    homepage = "https://trends.google.com/"

    def probe(self, *, timeout: int = 15) -> ProviderResult:
        retrieved = datetime.now(UTC)
        try:
            request = Request(self.homepage, headers={"User-Agent": "GamCryp-discovery/1.0"})
            with urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    return ProviderResult("google_trends", "BLOCKED", retrieved, limitation=f"HTTP {status} from trends.google.com")
            return ProviderResult("google_trends", "REACHABLE_NEEDS_QUERY_API", retrieved, limitation="Homepage reachable; no relative-index values were inferred without a supported query response.")
        except Exception as exc:
            return ProviderResult("google_trends", "BLOCKED", retrieved, limitation=f"Live retrieval failed: {type(exc).__name__}: {exc}")


class UnavailableProvider:
    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def probe(self) -> ProviderResult:
        return ProviderResult(self.name, "BLOCKED", datetime.now(UTC), limitation=self.reason)
