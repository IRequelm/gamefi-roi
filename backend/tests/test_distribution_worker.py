from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.distribution.x_publisher import XAuthError
from app.publishing.distribution_worker import DistributionWorker, DistributionWorkerConfig, _approved_short_waiting
from app.publishing.short_youtube_handoff import ShortHandoffItem, ShortHandoffQueue, write_handoff


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
        autonomous_cap_file=tmp_path / "cap.json", heartbeat_file=tmp_path / "heartbeat.json",
    )
    result = DistributionWorker(config=config, x_service=x, youtube_distribution=FakeYouTube(), now=lambda: NOW).run_once()
    assert result[0]["status"] == "manual_ready"
    assert x.calls == []
    assert json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8"))["item"]["post_text"] == "Post for green-x"


def test_manual_x_mode_batches_two_green_posts_without_network(tmp_path):
    x = FakeX(publishable=["green-1", "green-2", "green-3"])
    config = DistributionWorkerConfig(
        x_publishing_mode="manual", video_directory=tmp_path / "videos", state_file=tmp_path / "worker.json",
        manual_outbox_file=tmp_path / "outbox.json", short_handoff_file=tmp_path / "short-handoff.json",
        autonomous_cap_file=tmp_path / "cap.json", heartbeat_file=tmp_path / "heartbeat.json",
    )

    result = DistributionWorker(config=config, x_service=x, youtube_distribution=FakeYouTube(), now=lambda: NOW).run_once()

    assert result[0]["status"] == "manual_ready"
    assert result[0]["content_ids"] == ["green-1", "green-2"]
    payload = json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8"))
    assert [item["content_id"] for item in payload["items"]] == ["green-1", "green-2"]
    assert x.calls == []


def test_worker_writes_success_heartbeat_after_cycle(tmp_path):
    worker(tmp_path).run_once()
    heartbeat = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["status"] == "ok"
    assert heartbeat["pid"] > 0
    assert heartbeat["updated_at"].endswith("+00:00")
    assert any(item["platform"] == "YouTubeLegacyQueue" for item in heartbeat["platform_statuses"])


def test_dynamic_catalog_unavailability_marks_worker_degraded(tmp_path, monkeypatch):
    short_queue = tmp_path / "short-handoff.json"
    short_queue.write_text(json.dumps({"version": "youtube-short-handoff-v1", "items": [], "blocked": {}}), encoding="utf-8")

    def unavailable(_settings):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.publishing.distribution_worker.create_database_engine", unavailable)
    instance = worker(tmp_path)
    result = instance.run_once()

    assert result[2]["catalog_status"] == "unavailable"
    heartbeat = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["status"] == "degraded"


def test_green_x_is_dry_run_by_default_and_persists_no_publication(tmp_path):
    x = FakeX(publishable=["green-x"])
    result = worker(tmp_path, x=x).run_once()
    assert result[0]["status"] == "dry_run"
    assert x.calls == [("green-x", True, False)]
    assert not (tmp_path / "worker.json").exists()


def test_live_x_publishes_two_eligible_posts_per_day(tmp_path):
    x = FakeX(publishable=["green-x-1", "green-x-2", "green-x-3"])
    config = DistributionWorkerConfig(
        live=True,
        x_publishing_mode="live",
        x_daily_post_cap=2,
        x_daily_cap_file=tmp_path / "x-cap.json",
        state_file=tmp_path / "worker.json",
        heartbeat_file=tmp_path / "heartbeat.json",
        short_handoff_file=tmp_path / "short.json",
        autonomous_cap_file=tmp_path / "youtube-cap.json",
    )
    instance = DistributionWorker(config=config, x_service=x, youtube_distribution=FakeYouTube(), now=lambda: NOW)

    result = instance._process_x(NOW)

    assert result["status"] == "published"
    assert result["published_count"] == 2
    assert [item[0] for item in x.calls] == ["green-x-1", "green-x-2"]


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


def test_short_handoff_approval_reactivates_a_prior_dead_letter(tmp_path: Path, monkeypatch):
    video = tmp_path / "reviewed.mp4"
    video.write_bytes(b"reviewed-video")
    import hashlib

    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    item = ShortHandoffItem(
        package_id="package-short_form-reviewed",
        content_id="content-reviewed",
        title="Reviewed Short",
        description="Source-backed description.",
        source_url="https://gamcryp.com/test",
        tags=("GamCryp",),
        video_path=str(video),
        caption_path=str(video),
        narration_path=str(video),
        narration_provider="local_music",
        audio_mode="music_only",
        evidence_fingerprint="a" * 64,
        video_checksum=checksum,
        created_at="2026-09-21T00:00:00+00:00",
        creative_approval_state="approved",
        creative_approval_video_checksum=checksum,
    )
    queue_path = tmp_path / "short-handoff.json"
    write_handoff(queue_path, ShortHandoffQueue(items=(item,)))
    assert _approved_short_waiting(queue_path) is True

    monkeypatch.setattr(
        "app.publishing.distribution_worker.publish_next_short_handoff",
        lambda **kwargs: {"status": "dry_run", "content_id": "content-reviewed"},
    )
    instance = worker(tmp_path, youtube=SimpleNamespace(publisher=object()))
    instance.state.records["YouTubeShortHandoff"] = {"attempts": 3, "dead_letter": True, "error_category": "BLOCKED_VISUAL_QA"}
    result = instance._process_short_handoff(NOW)

    assert result["status"] in {"idle", "not_ready", "dry_run"}
    assert "YouTubeShortHandoff" not in instance.state.records


def test_pending_creative_review_is_not_recorded_as_worker_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "app.publishing.distribution_worker.publish_next_short_handoff",
        lambda **kwargs: {
            "status": "not_ready",
            "detail": "human creative quality approval is required before YouTube use",
        },
    )
    video = tmp_path / "pending.mp4"
    video.write_bytes(b"pending-video")
    import hashlib

    item = ShortHandoffItem(
        package_id="package-short_form-pending",
        content_id="content-pending",
        title="Pending Short",
        description="Source-backed description.",
        source_url="https://gamcryp.com/test",
        tags=("GamCryp",),
        video_path=str(video),
        caption_path=str(video),
        narration_path=str(video),
        narration_provider="local_music",
        audio_mode="music_only",
        evidence_fingerprint="b" * 64,
        video_checksum=hashlib.sha256(video.read_bytes()).hexdigest(),
        created_at="2026-09-21T00:00:00+00:00",
    )
    write_handoff(tmp_path / "short-handoff.json", ShortHandoffQueue(items=(item,)))
    instance = worker(tmp_path, youtube=SimpleNamespace(publisher=object()))

    result = instance._process_short_handoff(NOW)

    assert result["status"] == "awaiting_human_approval"
    assert "YouTubeShortHandoff" not in instance.state.records


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
