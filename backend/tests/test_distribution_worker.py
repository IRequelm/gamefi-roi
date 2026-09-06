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
    )
    return DistributionWorker(config=config, x_service=x or FakeX(), youtube_distribution=youtube or FakeYouTube(), now=lambda: NOW)


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
    assert [item["status"] for item in result] == ["idle", "idle", "idle"]
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
    assert result[1] == {
        "platform": "YouTube",
        "content_id": "video-1",
        "status": "blocked",
        "detail": "video asset is missing",
    }


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
    assert result[1]["status"] == "failed"
    assert result[2]["status"] == "dry_run"
    assert youtube.calls == ["dry:good-video"]


def test_x_auth_failure_does_not_block_youtube_queue_processing(tmp_path):
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "good-video.mp4").write_bytes(b"video")
    x = FakeX(publishable=["bad-x"], error=RuntimeError("auth unavailable"))
    youtube = FakeYouTube(publishable=["good-video"])

    result = worker(tmp_path, x=x, youtube=youtube).run_once()

    assert result[0]["status"] == "failed"
    assert result[1]["status"] == "dry_run"
    assert youtube.calls == ["dry:good-video"]


def test_x_auth_failure_exports_one_manual_ready_item_without_blocking_youtube(tmp_path):
    x = FakeX(publishable=["bad-x"], error=XAuthError("credentials unavailable"))
    youtube = FakeYouTube()
    first = worker(tmp_path, x=x, youtube=youtube).run_once()
    outbox = json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8"))
    second = worker(tmp_path, x=x, youtube=youtube).run_once()

    assert first[0]["status"] == "manual_ready"
    assert first[1]["status"] == "idle"
    assert outbox["item"]["status"] == "MANUAL_READY"
    assert outbox["item"]["published"] is False
    assert second[0]["status"] == "cooldown"
    assert json.loads((tmp_path / "outbox.json").read_text(encoding="utf-8")) == outbox
