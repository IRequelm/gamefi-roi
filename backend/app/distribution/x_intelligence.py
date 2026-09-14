"""Live X discovery and engagement intelligence for the X-only worker path.

The collector is deliberately fail-closed: an unavailable or unpaid X API
never becomes an empty live result and never authorizes a retweet.  Search
results are only actionable after the existing official-source whitelist and
catalog relevance checks pass in ``x_amplification``.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.distribution.x_amplification import XSourcePost
from app.distribution.x_publisher import XPublisherConfig, XPublisherError, XPublishingService


DEFAULT_QUERIES = (
    '(GameFi OR "play to earn" OR "blockchain game") lang:en -is:retweet',
    '(DePIN OR "node rewards" OR "bandwidth sharing") lang:en -is:retweet',
    '(airdrop OR points OR rewards) (crypto OR web3) lang:en -is:retweet',
)
DEFAULT_STATE_FILE = Path("data/local/x/intelligence_state.json")
DEFAULT_FEED_FILE = Path("distribution/inbox/x_signal_feed.json")


class XEngagementMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    like_count: int = Field(default=0, ge=0)
    retweet_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    quote_count: int = Field(default=0, ge=0)
    bookmark_count: int = Field(default=0, ge=0)

    @property
    def score(self) -> int:
        # Reposts and quotes are stronger amplification signals than likes;
        # this is a transparent ranking heuristic, not a financial metric.
        return self.like_count + (2 * self.retweet_count) + self.reply_count + (2 * self.quote_count) + self.bookmark_count


class XEngagementObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    post_id: str
    source_account: str
    original_post_url: str
    posted_at: str
    text_excerpt: str
    metrics: XEngagementMetrics
    engagement_score: int
    source_verified: bool
    discovered_at: str


@dataclass(frozen=True)
class XIntelligenceConfig:
    state_file: Path = DEFAULT_STATE_FILE
    feed_file: Path = DEFAULT_FEED_FILE
    queries: tuple[str, ...] = DEFAULT_QUERIES
    max_results: int = 25
    max_feed_items: int = 50
    freshness_hours: int = 48
    min_engagement_score: int = 10

    @classmethod
    def from_environment(cls) -> "XIntelligenceConfig":
        raw_queries = os.getenv("GAMEFI_X_DISCOVERY_QUERIES", "").strip()
        queries = tuple(item.strip() for item in raw_queries.split(";") if item.strip()) if raw_queries else DEFAULT_QUERIES
        return cls(
            state_file=Path(os.getenv("GAMEFI_X_INTELLIGENCE_STATE_FILE", str(DEFAULT_STATE_FILE))),
            feed_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_FEED_FILE", str(DEFAULT_FEED_FILE))),
            queries=queries,
            max_results=max(10, min(int(os.getenv("GAMEFI_X_DISCOVERY_MAX_RESULTS", "10")), 100)),
            max_feed_items=max(1, min(int(os.getenv("GAMEFI_X_DISCOVERY_MAX_FEED_ITEMS", "50")), 100)),
            freshness_hours=max(1, int(os.getenv("GAMEFI_X_DISCOVERY_FRESHNESS_HOURS", "48"))),
            min_engagement_score=max(0, int(os.getenv("GAMEFI_X_AMPLIFICATION_MIN_ENGAGEMENT", "10"))),
        )


class XIntelligenceCollector:
    def __init__(
        self,
        *,
        service: XPublishingService | None = None,
        config: XIntelligenceConfig | None = None,
    ) -> None:
        self.config = config or XIntelligenceConfig.from_environment()
        self.service = service or XPublishingService(XPublisherConfig.from_environment())

    def collect(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        observations: list[XEngagementObservation] = []
        query_results: list[dict[str, Any]] = []
        try:
            identity = self.service.api_client.authenticated_user()
            user = identity.get("data") or {}
            if not user.get("id") or not user.get("username"):
                raise XPublisherError("X authenticated-user response did not contain an id and username")
            for query in self.config.queries:
                payload = self.service.api_client.search_recent(query, max_results=self.config.max_results)
                query_results.append({"query": query, "result_count": (payload.get("meta") or {}).get("result_count", 0)})
                observations.extend(self._observations_from_payload(payload, retrieved_at=current))
            deduplicated = {item.post_id: item for item in observations}
            ranked = sorted(deduplicated.values(), key=lambda item: (-item.engagement_score, item.posted_at, item.post_id))
            feed_items = [self._feed_post(item) for item in ranked[: self.config.max_feed_items]]
            self._write_feed(feed_items, generated_at=current)
            return self._write_state(
                {
                    "status": "LIVE",
                    "generated_at": current.isoformat(),
                    "authenticated_username": str(user["username"]),
                    "queries": query_results,
                    "observation_count": len(ranked),
                    "high_engagement_count": sum(item.engagement_score >= self.config.min_engagement_score for item in ranked),
                    "top_posts": [item.model_dump(mode="json") for item in ranked[:10]],
                    "limitation": None,
                }
            )
        except (XPublisherError, OSError, ValueError) as exc:
            # Preserve any previous feed; the worker will refuse to process it
            # unless this cycle is LIVE.  This avoids stale or invented reposts.
            return self._write_state(
                {
                    "status": "BLOCKED",
                    "generated_at": current.isoformat(),
                    "authenticated_username": None,
                    "queries": query_results,
                    "observation_count": 0,
                    "high_engagement_count": 0,
                    "top_posts": [],
                    "limitation": f"Live X intelligence failed: {type(exc).__name__}: {exc}",
                }
            )

    def _observations_from_payload(self, payload: dict[str, Any], *, retrieved_at: datetime) -> list[XEngagementObservation]:
        users = {str(user.get("id")): user for user in (payload.get("includes") or {}).get("users", []) if user.get("id")}
        result: list[XEngagementObservation] = []
        for post in payload.get("data") or []:
            if not isinstance(post, dict) or not post.get("id") or not post.get("created_at"):
                continue
            metrics = XEngagementMetrics.model_validate(post.get("public_metrics") or {})
            author = users.get(str(post.get("author_id")), {})
            account = str(author.get("username") or post.get("author_id") or "unknown")
            result.append(
                XEngagementObservation(
                    post_id=str(post["id"]),
                    source_account=account,
                    original_post_url=f"https://x.com/{account}/status/{post['id']}",
                    posted_at=str(post["created_at"]),
                    text_excerpt=" ".join(str(post.get("text", "")).split())[:280],
                    metrics=metrics,
                    engagement_score=metrics.score,
                    source_verified=bool(author.get("verified", False)),
                    discovered_at=retrieved_at.isoformat(),
                )
            )
        return result

    def _feed_post(self, item: XEngagementObservation) -> dict[str, Any]:
        return XSourcePost(
            source_account=item.source_account,
            source_verified=item.source_verified,
            source_type="x_live_search",
            original_url=item.original_post_url,
            post_id=item.post_id,
            posted_at=item.posted_at,
            text=item.text_excerpt,
            like_count=item.metrics.like_count,
            retweet_count=item.metrics.retweet_count,
            reply_count=item.metrics.reply_count,
            quote_count=item.metrics.quote_count,
            bookmark_count=item.metrics.bookmark_count,
            engagement_score=item.engagement_score,
        ).model_dump(mode="json")

    def _write_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        _atomic_write(self.config.state_file, payload)
        return payload

    def _write_feed(self, items: list[dict[str, Any]], *, generated_at: datetime) -> None:
        _atomic_write(self.config.feed_file, {"version": 2, "generated_at": generated_at.isoformat(), "provider": "x_api", "posts": items})


def load_intelligence_state(path: Path = DEFAULT_STATE_FILE) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def intelligence_is_live_and_fresh(path: Path = DEFAULT_STATE_FILE, *, now: datetime | None = None, max_age_hours: int = 48) -> bool:
    payload = load_intelligence_state(path)
    if not payload or payload.get("status") != "LIVE" or not payload.get("generated_at"):
        return False
    try:
        generated = datetime.fromisoformat(str(payload["generated_at"]).replace("Z", "+00:00"))
        current = (now or datetime.now(UTC)).astimezone(UTC)
        return timedelta(0) <= current - generated.astimezone(UTC) <= timedelta(hours=max_age_hours)
    except (TypeError, ValueError):
        return False


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
