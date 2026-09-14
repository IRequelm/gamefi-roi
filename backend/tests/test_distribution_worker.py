from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.distribution.x_publisher import XAuthError
from app.publishing.distribution_worker import DistributionWorker, DistributionWorkerConfig


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


class FakeX:
    def __init__(self, *, publishable: list[str] | None = None, awaiting: list[str] | None = None, blocked: list[str] | None = None, error: Exception | None = None):
        self.publishable = publishable or []
        self.awaiting = awaiting or []
        self.blocked = blocked or []
        self.error = error
        self.calls: list[tuple[str, bool, bool]] = []

    def queue_summary(self):
        return {"publishable": self.publishable, "awaiting_human_approval": self.awaiting, "blocked": self.blocked}

    def preview(self, content_id):
        return SimpleNamespace(
            content_checksum="checksum",
            would_publish=True,
            exact_final_copy=f"Post for {content_id}",
            attribution_url=f"https://example.com/{content_id}",
        )

    def publish(self, content_id, *, dry_run, confirm_publish):
        self.calls.append((content_id, dry_run, confirm_publish))
        if self.error:
            raise self.error
        return SimpleNamespace(model_dump=lambda mode="json": {"content_id": content_id})


class FakeYouTube:
    def __init__(self, *, publishable: list[str] | None = None, awaiting: list[str] | None = None, blocked: list[str] | None = None, error: Exception | None = None):
        self.publishable = publishable or []
        self.awaiting = awaiting or []
        self.blocked = blocked or []
        self.error = error
        self.calls: list[str] = []

    def queue_summary(self):
        return {"publishable": self.publishable, "awaiting_human_approval": self.awaiting, "blocked": self.blocked}

    def preview(self, content_id, *, video_path, thumbnail_path):
        if self.error:
            raise self.error
        return SimpleNamespace(package_checksum="package")

    def dry_run(self, content_id, *, video_path, thumbnail_path):
        self.calls.append(f"dry:{content_id}")
        return SimpleNamespace(to_safe_dict=lambda: {"content_id": content_id})

    def upload(self, content_id, *, video_path, thumbnail_path, confirm_publish):
        self.calls.append(f"upload:{content_id}")
        return SimpleNamespace(to_safe_dict=lambda: {"content_id": content_id})


def worker(tmp_path: Path, *, live: bool = False, x=None, youtube=None) -> DistributionWorker:
    config = DistributionWorkerConfig(
        live=live,
        video_directory=tmp_path / "videos",
        state_file=tmp_path / "worker.json",
        failure_cooldown_seconds=3600,
        manual_outbox_file=tmp_path / "outbox.json",
        short_handoff_file=tmp_path / "short-handoff.json",
        autonomous_cap_file=tmp_path / "cap.json",
        heartbeat_file=tmp_path / "heartbeat.json",
    )
    return DistributionWorker(config=config, x_service=x or FakeX(), youtube_distribution=youtube or FakeYouTube(), now=lambda: NOW)


def test_manual_x_mode_exports_exact_green_post_without_network(tmp_path):
    x = FakeX(publishable=["green-x"])
    config = DistributionWorkerConfig(
        x_publishing_mode="manual", video_directory=tmp_path / "videos", state_file=tmp_path / "worker.json",
        manual_outbox_file=tmp_path / "outbox.json", short_handoff_file=tmp_path / "short-handoff.json",
        autonomous_cap_file=tmp_path / "cap.json",
    )
    result = DistributionWorker(config=config, x_service=x, youtube_distribution=FakeYouTube(), now=lambda: NOW).run_once()
    assert result[0]["status"] == "manual_ready"
    assert x.calls == []
    assert json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8"))["item"]["post_text"] == "Post for green-x"


def test_worker_writes_success_heartbeat_after_cycle(tmp_path):
    worker(tmp_path).run_once()
    heartbeat = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["status"] == "ok"
    assert heartbeat["pid"] > 0
    assert heartbeat["updated_at"].endswith("+00:00")
    assert any(item["platform"] == "YouTubeLegacyQueue" for item in heartbeat["platform_statuses"])


def test_green_x_is_dry_run_by_default_and_persists_no_publication(tmp_path):
    x = FakeX(publishable=["green-x"])
    result = worker(tmp_path, x=x).run_once()
    assert result[0]["status"] == "dry_run"
    assert x.calls == [("green-x", True, False)]
    assert not (tmp_path / "worker.json").exists()


def test_yellow_and_red_items_are_not_auto_processed(tmp_path):
    x = FakeX(awaiting=["yellow-x"], blocked=["red-x"])
    youtube = FakeYouTube(awaiting=["yellow-video"], blocked=["red-video"])
    result = worker(tmp_path, x=x, youtube=youtube).run_once()
    assert [item["status"] for item in result] == ["idle", "disabled_for_autonomous_worker", "idle"]
    assert x.calls == []
    assert youtube.calls == []


def test_failed_item_is_cooled_down_and_state_survives_restart(tmp_path):
    x = FakeX(publishable=["bad-x"], error=RuntimeError("auth unavailable"))
    first = worker(tmp_path, x=x).run_once()
    assert first[0]["status"] == "failed"
    state = json.loads((tmp_path / "worker.json").read_text(encoding="utf-8"))
    assert state["records"]["X:bad-x:checksum"]["error_category"] == "RuntimeError"

    second = worker(tmp_path, x=x).run_once()
    assert second[0]["status"] == "cooldown"
    assert len(x.calls) == 1


def test_missing_youtube_asset_fails_closed(tmp_path):
    result = worker(tmp_path, youtube=FakeYouTube(publishable=["video-1"])).run_once()
    assert result[1] == {"platform": "YouTubeLegacyQueue", "status": "disabled_for_autonomous_worker"}


def test_youtube_queue_continues_after_one_item_failure(tmp_path):
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "bad-video.mp4").write_bytes(b"video")
    (video_dir / "good-video.mp4").write_bytes(b"video")
    youtube = FakeYouTube(publishable=["bad-video", "good-video"])

    class PreviewFails(FakeYouTube):
        def preview(self, content_id, *, video_path, thumbnail_path):
            if content_id == "bad-video":
                raise ValueError("invalid package")
            return super().preview(content_id, video_path=video_path, thumbnail_path=thumbnail_path)

    youtube = PreviewFails(publishable=youtube.publishable)
    result = worker(tmp_path, youtube=youtube).run_once()
    assert result[1]["status"] == "disabled_for_autonomous_worker"
    assert result[2]["status"] == "idle"
    assert youtube.calls == []


def test_x_auth_failure_does_not_block_youtube_queue_processing(tmp_path):
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "good-video.mp4").write_bytes(b"video")
    x = FakeX(publishable=["bad-x"], error=RuntimeError("auth unavailable"))
    youtube = FakeYouTube(publishable=["good-video"])

    result = worker(tmp_path, x=x, youtube=youtube).run_once()

    assert result[0]["status"] == "failed"
    assert result[1]["status"] == "disabled_for_autonomous_worker"
    assert result[2]["status"] == "idle"
    assert youtube.calls == []


def test_x_auth_failure_exports_one_manual_ready_item_without_blocking_youtube(tmp_path):
    x = FakeX(publishable=["bad-x"], error=XAuthError("credentials unavailable"))
    youtube = FakeYouTube()
    first = worker(tmp_path, x=x, youtube=youtube).run_once()
    outbox = json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8"))
    second = worker(tmp_path, x=x, youtube=youtube).run_once()

    assert first[0]["status"] == "manual_ready"
    assert first[1]["status"] == "disabled_for_autonomous_worker"
    assert outbox["item"]["status"] == "MANUAL_READY"
    assert outbox["item"]["published"] is False
    assert second[0]["status"] == "cooldown"
    assert json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8")) == outbox


def test_live_x_repost_is_idempotent_and_requires_fresh_intelligence(tmp_path: Path):
    class FakeApi:
        def __init__(self):
            self.retweet_calls = []

        def authenticated_user(self):
            return {"data": {"id": "42", "username": "GamCryp"}}

        def create_retweet(self, user_id, tweet_id):
            self.retweet_calls.append((user_id, tweet_id))
            return tweet_id

    class FakeIntel:
        class Config:
            freshness_hours = 48

        def __init__(self, state_file, feed_file):
            self.config = self.Config()
            self.state_file = state_file
            self.feed_file = feed_file

        def collect(self, *, now):
            self.state_file.write_text(json.dumps({"status": "LIVE", "generated_at": now.isoformat()}), encoding="utf-8")
            self.feed_file.write_text(json.dumps({"version": 2, "posts": [{
                "source_account": "OfficialSource", "source_verified": True, "source_type": "x_live_search",
                "original_url": "https://x.com/OfficialSource/status/12345", "post_id": "12345",
                "posted_at": (now.replace(hour=now.hour - 1)).isoformat(),
                "text": "GEODNET network update: new coverage is live.", "engagement_score": 20,
            }]}), encoding="utf-8")
            return {"status": "LIVE"}

    class FakeRefill:
        def run(self, *, now):
            return {"status": "disabled"}

    api = FakeApi()
    x = FakeX()
    x.api_client = api
    feed = tmp_path / "feed.json"
    whitelist = tmp_path / "whitelist.json"
    whitelist.write_text(json.dumps({"sources": [{
        "source_account": "OfficialSource", "source_type": "project_official", "verified": True,
        "official_source_url": "https://geodnet.com",
    }]}), encoding="utf-8")
    config = DistributionWorkerConfig(
        live=True,
        x_publishing_mode="live",
        x_amplification_auto_repost=True,
        x_amplification_feed_file=feed,
        x_amplification_whitelist_file=whitelist,
        x_amplification_outbox_file=tmp_path / "outbox.json",
        x_amplification_history_file=tmp_path / "history.json",
        x_intelligence_state_file=tmp_path / "intelligence.json",
        x_daily_cap_file=tmp_path / "x-daily-cap.json",
        state_file=tmp_path / "worker.json",
        heartbeat_file=tmp_path / "heartbeat.json",
        short_handoff_file=tmp_path / "short.json",
        autonomous_cap_file=tmp_path / "cap.json",
    )
    intelligence = FakeIntel(config.x_intelligence_state_file, feed)
    worker_instance = DistributionWorker(config=config, x_service=x, youtube_distribution=FakeYouTube(), refiller=FakeRefill(), x_intelligence=intelligence, now=lambda: NOW)

    first = worker_instance.run_once()
    second = worker_instance.run_once()
    assert next(item for item in first if item["platform"] == "XAmplification")["status"] == "reposted"
    assert next(item for item in second if item["platform"] == "XAmplification")["reposted"] == 0
    assert api.retweet_calls == [("42", "12345")]
