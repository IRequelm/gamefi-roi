from __future__ import annotations

from pathlib import Path
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.config.settings import Settings
from app.content_package.generator import build_content_packages
from app.publishing.short_youtube_handoff import (
    ShortHandoffItem,
    ShortHandoffQueue,
    _stored_render_creative_ready,
    audit_handoff,
    approve_handoff_item,
    autonomous_youtube_cap_available,
    load_handoff,
    prepare_short_handoff,
    publish_next,
    reconcile_handoff_state,
    write_handoff,
)
from app.video_render.factory import RENDER_READY, RenderResult


def _settings() -> Settings:
    return Settings(environment="test", database_url="sqlite:///unused", allow_sqlite_for_tests=True, public_base_url="https://gamcryp.com", elevenlabs_api_key="test-key", elevenlabs_model_id="eleven_multilingual_v2", elevenlabs_voice_id="voice", youtube_publish_state_file="data/local/nonexistent-test-publication-state.json")


def _package():
    return next(package for package in build_content_packages() if package.format == "SHORT_FORM" and package.content_family != "FINANCIAL_ROI")


def _render(tmp_path: Path, *, package, **kwargs) -> RenderResult:
    video = tmp_path / "video.mp4"
    caption = tmp_path / "captions.srt"
    audio = tmp_path / "audio.mp3"
    for path in (video, caption, audio):
        path.write_bytes(b"asset")
    quality = {
        "meaningful_scene_count": 6,
        "scene_diversity": ["hook", "identity", "setup", "evidence", "status", "cta"],
        "non_caption_visual_element_count": 6,
        "identity_present": True,
        "identity_mode": "branded_identity_card",
        "caption_safe_area": {"left": 96, "right": 96, "bottom": 220},
        "caption_safe_area_validated": True,
        "text_clipping": False,
        "scene_transitions": True,
        "animated_motion": True,
        "transition_effects": ["fade_in", "fade_out", "moving_accents"],
        "static_background_only": False,
        "caption_only_visuals": False,
        "brand_opening_present": True,
        "brand_closing_present": True,
        "brand_sting_present": True,
        "narration_script_matches_package": True,
        "creative_status": "CREATIVE_QA_PASSED",
        "product_visual_count": 1,
        "product_visual_storytelling": True,
        "product_visual_motion": "ken_burns_crop_and_scanline",
        "hook_qa": {"status": "PASSED", "blockers": []},
        "gamcryp_product_placement": True,
        "frame_qa": {"status": "PASSED", "frames": ["a", "b", "c", "d", "e"]},
        "primary_visual_elements": ["identity_card", "setup_diagram", "mechanics_flow", "evidence_metric_card", "branded_cta"],
        "audio_mode": "music_only",
        "tts_forbidden": True,
    }
    return RenderResult(package.source_inventory_item_id, package.package_id, "SHORT_FORM", RENDER_READY, None, str(video), str(caption), str(audio), 10.0, 1080, 1920, None, None, None, package.evidence_fingerprint, None, quality_metadata=quality, audio_mode="music_only")


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


def test_music_only_short_render_enters_handoff(tmp_path: Path) -> None:
    package = _package()
    queue_path = tmp_path / "handoff.json"
    result = _render(tmp_path, package=package)
    result = replace(result, voice_name=None, voice_id=None, model_id=None, audio_mode="music_only")
    queue = prepare_short_handoff(
        settings=_settings(), queue_path=queue_path, render_root=tmp_path / "render",
        packages=[package], render=lambda package, **kwargs: result,
    )
    assert len(queue.items) == 1
    assert queue.items[0].audio_mode == "music_only"
    assert queue.items[0].narration_provider == "local_music"


def test_creative_approval_requires_explicit_human_review_acknowledgement(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"reviewable-video")
    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    item = ShortHandoffItem(
        package_id="package-short_form-review-gate",
        content_id="content-review-gate",
        title="Review gate",
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
    )
    queue_path = tmp_path / "handoff.json"
    write_handoff(queue_path, ShortHandoffQueue(items=(item,)))

    with pytest.raises(ValueError, match="confirm_reviewed"):
        approve_handoff_item(item.package_id, queue_path)

    approved = approve_handoff_item(
        item.package_id,
        queue_path,
        confirm_reviewed=True,
        reviewed_by="qa-operator",
        review_note="Frames and source claim checked.",
    )

    assert approved.creative_approval_state == "approved"
    assert approved.creative_approval_video_checksum == checksum
    assert approved.creative_reviewed_by == "qa-operator"
    assert approved.creative_review_note == "Frames and source claim checked."


def test_verified_reused_neural_render_enters_handoff_but_stays_pending(tmp_path: Path) -> None:
    package = _package()
    queue_path = tmp_path / "handoff.json"
    result = _render(tmp_path, package=package)
    quality = dict(result.quality_metadata or {})
    quality.update({"audio_mode": "neural_voice", "narration_reused": True})
    result = replace(
        result,
        voice_name="Sarah",
        voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_multilingual_v2",
        audio_mode="neural_voice",
        quality_metadata=quality,
    )
    queue = prepare_short_handoff(
        settings=_settings(), queue_path=queue_path, render_root=tmp_path / "render",
        packages=[package], render=lambda package, **kwargs: result,
    )
    assert len(queue.items) == 1
    assert queue.items[0].narration_reused is True
    assert queue.items[0].narration_provider == "elevenlabs"
    assert queue.items[0].creative_approval_state == "pending_review"


def test_ambiguous_opportunity_does_not_select_a_second_angle(tmp_path: Path) -> None:
    package = next(package for package in build_content_packages() if package.format == "SHORT_FORM" and package.opportunity_id == "hivemapper")
    asset = tmp_path / "asset.bin"
    asset.write_bytes(b"existing-ambiguous-attempt")
    checksum = hashlib.sha256(asset.read_bytes()).hexdigest()
    prior = ShortHandoffItem(
        package_id="package-short_form-depin_setup-hivemapper",
        content_id="inventory-depin_setup-hivemapper",
        title="Hivemapper prior attempt",
        description="Prior attempt requires reconciliation.",
        source_url="https://gamcryp.com/opportunities/hivemapper",
        tags=("GamCryp",),
        video_path=str(asset),
        caption_path=str(asset),
        narration_path=str(asset),
        narration_provider="elevenlabs",
        narration_voice_id="legacy",
        narration_model_id="legacy",
        audio_mode="neural_voice",
        evidence_fingerprint="a" * 64,
        video_checksum=checksum,
        created_at="2026-09-06T00:00:00+00:00",
        status="ambiguous",
    )
    queue_path = tmp_path / "handoff.json"
    queue_path.write_text(ShortHandoffQueue(items=(prior,)).model_dump_json(), encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("a second angle must not be rendered before reconciliation")

    queue = prepare_short_handoff(settings=_settings(), queue_path=queue_path, packages=[package], render=forbidden)

    assert [item.package_id for item in queue.items] == [prior.package_id]
    assert queue.items[0].status == "ambiguous"


def test_handoff_buffer_is_bounded_and_deterministic(tmp_path: Path) -> None:
    package = _package()
    queue_path = tmp_path / "handoff.json"
    queue_path.write_text(ShortHandoffQueue(buffer_target=35).model_dump_json(), encoding="utf-8")

    queue = prepare_short_handoff(
        settings=_settings(),
        queue_path=queue_path,
        packages=[package],
        render=lambda package, **kwargs: _render(tmp_path, package=package),
    )

    assert queue.buffer_target == 14
    assert load_handoff(queue_path).buffer_target == 14


def test_failed_render_does_not_enter_handoff(tmp_path: Path) -> None:
    package = _package()

    def failed(package, **kwargs):
        return RenderResult(package.source_inventory_item_id, package.package_id, "SHORT_FORM", "NOT_READY", "provider failed", None, None, None, None, 1080, 1920, None, None, None, package.evidence_fingerprint, None)

    queue = prepare_short_handoff(settings=_settings(), queue_path=tmp_path / "handoff.json", packages=[package], render=failed)
    assert queue.items == ()


def test_newly_available_asset_retries_a_dead_lettered_package(tmp_path: Path) -> None:
    package = _package()
    queue_path = tmp_path / "handoff.json"
    blocked = {
        package.package_id: {
            "state": "BLOCKED_PACKAGE",
            "reason": "BLOCKED_MISSING_ASSETS: approved product visual is missing",
            "evidence_fingerprint": package.evidence_fingerprint,
            "policy_version": "approved-reuse-tts-motion-v5",
            "attempts": 3,
        }
    }
    queue_path.write_text(ShortHandoffQueue(blocked=blocked).model_dump_json(), encoding="utf-8")

    queue = prepare_short_handoff(
        settings=_settings(),
        queue_path=queue_path,
        packages=[package],
        render=lambda package, **kwargs: _render(tmp_path, package=package),
    )

    assert len(queue.items) == 1
    assert package.package_id not in queue.blocked


def test_stored_render_rejects_changed_product_visual(tmp_path: Path) -> None:
    package = _package()
    video = tmp_path / "render" / "short" / "video.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    metadata_dir = video.parent.parent / "metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / f"{package.package_id}.json").write_text(
        json.dumps(
            {
                "quality_metadata": {
                    "creative_status": "CREATIVE_QA_PASSED",
                    "hook_qa": {"status": "PASSED"},
                    "product_visual_count": 1,
                    "gamcryp_product_placement": True,
                    "brand_closing_present": True,
                    "asset_plan": {"product_visual_paths": ["old-product.png"]},
                }
            }
        ),
        encoding="utf-8",
    )
    item = ShortHandoffItem(
        package_id=package.package_id,
        content_id=package.source_inventory_item_id,
        title=package.title_candidates[0],
        description="Source-backed description.",
        source_url="https://gamcryp.com",
        tags=("GamCryp",),
        video_path=str(video),
        caption_path=str(video),
        narration_path=str(video),
        evidence_fingerprint=package.evidence_fingerprint,
        video_checksum=hashlib.sha256(video.read_bytes()).hexdigest(),
        created_at="2026-09-21T00:00:00+00:00",
    )

    assert _stored_render_creative_ready(item, package) is False


def test_daily_cap_persists_and_resets_next_local_day(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    item = ShortHandoffItem(package_id="package-short_form-test", content_id="content-test", title="Test", description="Source-backed test.", source_url="https://gamcryp.com/test", tags=("GamCryp",), video_path=str(video), caption_path=str(video), narration_path=str(video), narration_provider="local_music", narration_voice_id="", narration_model_id="", audio_mode="music_only", evidence_fingerprint="a" * 64, video_checksum=checksum, created_at="2026-09-06T00:00:00+00:00", creative_approval_state="approved", creative_approval_video_checksum=checksum)
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


def test_reconciliation_preserves_missing_upload_as_ambiguous(tmp_path: Path) -> None:
    package = _package()
    item = _render(tmp_path, package=package)
    queue_path = tmp_path / "handoff.json"
    render = lambda package, **kwargs: item
    prepare_short_handoff(settings=_settings(), queue_path=queue_path, packages=[package], render=render)
    queue = load_handoff(queue_path)
    from app.publishing.short_youtube_handoff import write_handoff
    write_handoff(queue_path, queue.model_copy(update={"items": (queue.items[0].model_copy(update={"status": "uploaded"}),)}))
    assert reconcile_handoff_state(set(), queue_path) == 1
    assert load_handoff(queue_path).items[0].status == "ambiguous"


def test_audit_flags_legacy_upload_without_current_quality_approval(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    item = ShortHandoffItem(
        package_id="package-short_form-legacy",
        content_id="content-legacy",
        title="Legacy",
        description="Legacy source.",
        source_url="http://localhost:8000/opportunities/legacy",
        tags=("GamCryp",),
        video_path=str(video),
        caption_path=str(video),
        narration_path=str(video),
        narration_provider="elevenlabs",
        narration_voice_id="legacy",
        narration_model_id="legacy",
        audio_mode="neural_voice",
        evidence_fingerprint="a" * 64,
        video_checksum=checksum,
        created_at="2026-09-06T00:00:00+00:00",
        status="uploaded",
    )
    queue_path = tmp_path / "handoff.json"
    queue_path.write_text(ShortHandoffQueue(items=(item,)).model_dump_json(), encoding="utf-8")

    audit = audit_handoff(queue_path)

    assert audit["audit_status"] == "review_required"
    assert audit["items"][0]["content_id"] == "content-legacy"
    assert any("local development host" in blocker for blocker in audit["items"][0]["blockers"])
    assert any("checksum-bound creative approval" in blocker for blocker in audit["items"][0]["blockers"])
