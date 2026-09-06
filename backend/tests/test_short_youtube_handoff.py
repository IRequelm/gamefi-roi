from __future__ import annotations

from pathlib import Path
import hashlib
from types import SimpleNamespace

from app.config.settings import Settings
from app.content_package.generator import build_content_packages
from app.publishing.short_youtube_handoff import (
    ShortHandoffItem,
    ShortHandoffQueue,
    autonomous_youtube_cap_available,
    load_handoff,
    prepare_short_handoff,
    publish_next,
)
from app.video_render.factory import RENDER_READY, RenderResult


def _settings() -> Settings:
    return Settings(environment="test", database_url="sqlite:///unused", allow_sqlite_for_tests=True, public_base_url="https://gamcryp.com", elevenlabs_api_key="test-key", elevenlabs_model_id="eleven_multilingual_v2", elevenlabs_voice_id="voice")


def _package():
    return next(package for package in build_content_packages() if package.format == "SHORT_FORM" and package.content_family != "FINANCIAL_ROI")


def _render(tmp_path: Path, *, package, **kwargs) -> RenderResult:
    video = tmp_path / "video.mp4"
    caption = tmp_path / "captions.srt"
    audio = tmp_path / "audio.mp3"
    for path in (video, caption, audio):
        path.write_bytes(b"asset")
    return RenderResult(package.source_inventory_item_id, package.package_id, "SHORT_FORM", RENDER_READY, None, str(video), str(caption), str(audio), 10.0, 1080, 1920, "Sarah", "EXAVITQu4vr4xnSDxMaL", "eleven_multilingual_v2", package.evidence_fingerprint, None)


def test_ready_short_render_enters_handoff_once(tmp_path: Path) -> None:
    package = _package()
    queue_path = tmp_path / "handoff.json"
    render = lambda package, **kwargs: _render(tmp_path, package=package)
    queue = prepare_short_handoff(settings=_settings(), queue_path=queue_path, render_root=tmp_path / "render", packages=[package], render=render)
    again = prepare_short_handoff(settings=_settings(), queue_path=queue_path, render_root=tmp_path / "render", packages=[package], render=render)

    assert len(queue.items) == len(again.items) == 1
    assert queue.items[0].readiness == "GREEN"
    assert queue.items[0].category_id == "28"
    assert queue.items[0].made_for_kids is False
    assert all(item.format == "SHORT_FORM" for item in load_handoff(queue_path).items)


def test_failed_render_does_not_enter_handoff(tmp_path: Path) -> None:
    package = _package()

    def failed(package, **kwargs):
        return RenderResult(package.source_inventory_item_id, package.package_id, "SHORT_FORM", "NOT_READY", "provider failed", None, None, None, None, 1080, 1920, None, None, None, package.evidence_fingerprint, None)

    queue = prepare_short_handoff(settings=_settings(), queue_path=tmp_path / "handoff.json", packages=[package], render=failed)
    assert queue.items == ()


def test_daily_cap_persists_and_resets_next_local_day(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    item = ShortHandoffItem(package_id="package-short_form-test", content_id="content-test", title="Test", description="Source-backed test.", source_url="https://gamcryp.com/test", tags=("GamCryp",), video_path=str(video), caption_path=str(video), narration_path=str(video), narration_provider="elevenlabs", narration_voice_id="EXAVITQu4vr4xnSDxMaL", narration_model_id="eleven_multilingual_v2", evidence_fingerprint="a" * 64, video_checksum=checksum, created_at="2026-09-06T00:00:00+00:00")
    item2 = item.model_copy(update={"package_id": "package-short_form-test-2", "content_id": "content-test-2"})
    queue_path = tmp_path / "handoff.json"
    queue_path.write_text(ShortHandoffQueue(items=(item, item2)).model_dump_json(), encoding="utf-8")
    cap_path = tmp_path / "cap.json"

    class Publisher:
        def upload_video(self, manifest):
            return SimpleNamespace(status="uploaded", video_id="video-id")

        def dry_run_upload(self, manifest):
            return SimpleNamespace(status="ready", video_id=None)

    first = publish_next(publisher=Publisher(), queue_path=queue_path, cap_path=cap_path, now=datetime(2026, 9, 6, 12, tzinfo=UTC), live=True)
    second = publish_next(publisher=Publisher(), queue_path=queue_path, cap_path=cap_path, now=datetime(2026, 9, 6, 13, tzinfo=UTC), live=True)
    next_day = publish_next(publisher=Publisher(), queue_path=queue_path, cap_path=cap_path, now=datetime(2026, 9, 7, 12, tzinfo=UTC), live=True)

    assert first["status"] == "uploaded"
    assert second["status"] == "daily_cap"
    assert next_day["status"] == "uploaded"
    assert autonomous_youtube_cap_available(cap_path, now=datetime(2026, 9, 7, 12, tzinfo=UTC)) is False


def test_non_green_handoff_never_publishes(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    item = ShortHandoffItem(package_id="package-short_form-test", content_id="content-test", title="Test", description="Source-backed test.", source_url="https://gamcryp.com/test", tags=("GamCryp",), readiness="YELLOW", video_path=str(video), caption_path=str(video), narration_path=str(video), narration_provider="elevenlabs", narration_voice_id="EXAVITQu4vr4xnSDxMaL", narration_model_id="eleven_multilingual_v2", evidence_fingerprint="a" * 64, video_checksum=checksum, created_at="2026-09-06T00:00:00+00:00")
    queue_path = tmp_path / "handoff.json"
    queue_path.write_text(ShortHandoffQueue(items=(item,)).model_dump_json(), encoding="utf-8")

    class Publisher:
        def upload_video(self, manifest):
            raise AssertionError("blocked handoff must not publish")

    result = publish_next(publisher=Publisher(), queue_path=queue_path, cap_path=tmp_path / "cap.json", live=True)
    assert result["status"] == "idle"
