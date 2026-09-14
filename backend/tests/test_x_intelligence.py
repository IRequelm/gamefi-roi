from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.distribution.x_amplification import AmplificationDecision, XSourcePost, XSourceWhitelistEntry, classify_candidate
from app.distribution.x_intelligence import XEngagementMetrics, XIntelligenceCollector, XIntelligenceConfig, intelligence_is_live_and_fresh
from app.distribution.x_publisher import XPublisherError


NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


class FakeApi:
    def __init__(self, payload: dict | None = None, error: Exception | None = None):
        self.payload = payload or {}
        self.error = error

    def authenticated_user(self):
        if self.error:
            raise self.error
        return {"data": {"id": "1", "username": "GamCryp"}}

    def search_recent(self, query: str, *, max_results: int):
        if self.error:
            raise self.error
        return self.payload


class FakeService:
    def __init__(self, api):
        self.api_client = api


def _payload():
    return {
        "data": [
            {
                "id": "123",
                "author_id": "42",
                "created_at": (NOW - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                "text": "GEODNET coverage update is live.",
                "public_metrics": {"like_count": 20, "retweet_count": 5, "reply_count": 2, "quote_count": 1, "bookmark_count": 3},
            }
        ],
        "includes": {"users": [{"id": "42", "username": "GeoOfficial", "verified": True}]},
        "meta": {"result_count": 1},
    }


def test_engagement_score_is_transparent():
    metrics = XEngagementMetrics(like_count=20, retweet_count=5, reply_count=2, quote_count=1, bookmark_count=3)
    assert metrics.score == 37


def test_live_collection_persists_ranked_feed_and_state(tmp_path: Path):
    config = XIntelligenceConfig(state_file=tmp_path / "state.json", feed_file=tmp_path / "feed.json", queries=("GameFi",))
    payload = XIntelligenceCollector(service=FakeService(FakeApi(_payload())), config=config).collect(now=NOW)

    assert payload["status"] == "LIVE"
    assert payload["observation_count"] == 1
    assert payload["top_posts"][0]["engagement_score"] == 37
    assert intelligence_is_live_and_fresh(config.state_file, now=NOW, max_age_hours=48)
    feed = json.loads(config.feed_file.read_text(encoding="utf-8"))
    assert feed["provider"] == "x_api"
    assert feed["posts"][0]["source_account"] == "GeoOfficial"


def test_provider_failure_is_blocked_and_does_not_create_fake_feed(tmp_path: Path):
    feed = tmp_path / "feed.json"
    feed.write_text(json.dumps({"version": 2, "posts": [{"id": "old"}]}), encoding="utf-8")
    config = XIntelligenceConfig(state_file=tmp_path / "state.json", feed_file=feed, queries=("GameFi",))
    payload = XIntelligenceCollector(service=FakeService(FakeApi(error=XPublisherError("credits depleted"))), config=config).collect(now=NOW)

    assert payload["status"] == "BLOCKED"
    assert "credits depleted" in payload["limitation"]
    assert json.loads(feed.read_text(encoding="utf-8"))["posts"][0]["id"] == "old"


def test_low_engagement_live_candidate_requires_review():
    post = XSourcePost(
        source_account="OfficialSource",
        source_verified=True,
        original_url="https://x.com/OfficialSource/status/12345",
        post_id="12345",
        posted_at=(NOW - timedelta(hours=2)).isoformat(),
        text="GEODNET network update: new coverage is live.",
        engagement_score=2,
    )
    whitelist = {"officialsource": XSourceWhitelistEntry(source_account="OfficialSource", source_type="project_official", verified=True, official_source_url="https://geodnet.com")}
    result = classify_candidate(post, whitelist, now=NOW, min_engagement_score=10)
    assert result.decision == AmplificationDecision.MANUAL_REVIEW
