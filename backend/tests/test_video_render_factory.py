from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace

from app.publishing.elevenlabs import ElevenLabsGenerationResult, ElevenLabsProviderError, NarrationAssetMetadata
from app.video_render.factory import (
    APPROVED_VOICES,
    NOT_READY,
    RENDER_READY,
    RenderResult,
    build_render_job,
    render_package,
    validate_render,
)
from app.video_render.factory import _script_for
from app.content_package.generator import build_content_packages


def _package(fmt: str = "SHORT_FORM"):
    package = next(package for package in build_content_packages() if package.format == "SHORT_FORM" and package.content_family != "FINANCIAL_ROI")
    if fmt == "SHORT_FORM":
        return package
    sections = tuple({"title": f"Section {index}", "text": (f"Evidence-backed detail {index} " * 220).strip(), "evidence_paths": ["opportunity.guidance.how_to_start"]} for index in range(6))
    return replace(package, package_id=package.package_id.replace("short_form", "long_form"), format="LONG_FORM", narration_sections=sections, narration_script_outline=tuple(section["title"] for section in sections), estimated_narration_words=1320, estimated_duration_seconds=528)


def _settings(tmp_path: Path):
    from app.config.settings import Settings

    return Settings(environment="test", database_url="sqlite:///unused", allow_sqlite_for_tests=True, elevenlabs_api_key="test-key", elevenlabs_model_id="eleven_multilingual_v2", elevenlabs_voice_id=APPROVED_VOICES[0][1])


def _provider_factory(tmp_path: Path, calls: list[str], *, fail: bool = False):
    def factory(config):
        class Provider:
            def generate(self, *, content_id, script, now=None):
                calls.append(config.voice_id)
                if fail:
                    raise RuntimeError("mock provider failure")
                path = config.output_directory / f"{content_id}.mp3"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"audio")
                metadata = NarrationAssetMetadata(
                    content_id=content_id,
                    script_fingerprint="script",
                    source_script=script,
                    spoken_text=script,
                    voice_id=config.voice_id,
                    model_id=config.model_id or "model",
                    generated_at="2026-01-01T00:00:00+00:00",
                    audio_path=str(path),
                    audio_checksum="audio",
                )
                return ElevenLabsGenerationResult(metadata=metadata, reused=False)

        return Provider()

    return factory


def _runner(command, **kwargs):
    from subprocess import CompletedProcess

    if command[0] == "ffprobe":
        return CompletedProcess(command, 0, stdout=("600\n" if "package-long_form" in str(command) else "4.25\n"), stderr="")
    if str(command[-1]).endswith(".wav"):
        Path(command[-1]).write_bytes(b"audio" * 50)
    elif str(command[-1]).endswith(".png"):
        checkpoint = float(command[command.index("-ss") + 1])
        Path(command[-1]).write_bytes(b"frame" * (50 + int(checkpoint * 100)))
    else:
        Path(command[-1]).write_bytes(b"video")
    return CompletedProcess(command, 0, stdout="", stderr="")


def test_ready_short_renders_with_captions_and_evidence(tmp_path: Path, monkeypatch) -> None:
    package = _package()
    assets = tmp_path / "assets" / (package.opportunity_id or "gamcryp")
    assets.mkdir(parents=True)
    (assets / "official-product-ui.png").write_bytes(b"approved fixture" * 20)
    monkeypatch.setenv("GAMEFI_SHORT_ASSET_ROOT", str(tmp_path / "assets"))
    calls: list[str] = []
    result = render_package(package, settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, calls), command_runner=_runner)

    assert result.status == RENDER_READY, result.reason
    assert result.width == 1080 and result.height == 1920
    assert Path(result.video_path).is_file()
    assert Path(result.caption_path).is_file()
    assert calls == [APPROVED_VOICES[0][1]]
    assert validate_render(result) == ()
    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["evidence_fingerprint"] == package.evidence_fingerprint


def test_ready_long_uses_landscape_dimensions(tmp_path: Path) -> None:
    package = _package("LONG_FORM")
    result = render_package(package, settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, []), command_runner=_runner)

    assert result.status == RENDER_READY, result.reason
    assert (result.width, result.height) == (1920, 1080)


def test_long_script_uses_distinct_bound_evidence_sections_without_filler() -> None:
    package = _package("LONG_FORM")
    script = _script_for(package)

    assert all(f"Evidence-backed detail {index}" in script for index in range(6))
    assert "Opportunity or method context" not in script


def test_all_approved_voice_failures_are_not_ready_without_fallback(tmp_path: Path) -> None:
    calls: list[str] = []
    result = render_package(_package(), settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, calls, fail=True), command_runner=_runner)

    assert result.status == NOT_READY
    assert len(calls) == len(APPROVED_VOICES)
    assert not list((tmp_path / "render" / "short").glob("*.mp4"))


def test_account_level_elevenlabs_failure_does_not_try_other_voices(tmp_path: Path) -> None:
    calls: list[str] = []

    def provider_factory(config):
        calls.append(config.voice_id)
        raise ElevenLabsProviderError("ElevenLabs account quota or rate limit was reached", account_blocked=True)

    result = render_package(
        _package(), settings=_settings(tmp_path), root=tmp_path / "render",
        narration_provider_factory=provider_factory, command_runner=_runner,
    )

    assert result.status == NOT_READY
    assert "narration is required" in (result.reason or "")
    assert result.voice_id is None
    assert calls == [APPROVED_VOICES[0][1]]


def test_non_ready_package_cannot_become_render_job() -> None:
    package = replace(_package(), content_family="FINANCIAL_ROI")

    try:
        build_render_job(package)
    except RuntimeError as error:
        assert "READY" in str(error) or "unsupported" in str(error)
    else:
        raise AssertionError("blocked package unexpectedly rendered")


def test_guide_only_package_remains_evidence_bound_and_renderable() -> None:
    package = _package()
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id)
    assert opportunity is not None
    assert opportunity.admission_mode == "GUIDE_ONLY"
    assert build_render_job(package).format == "SHORT_FORM"


def _short_result_with_quality(**overrides):
    base = {
        "meaningful_scene_count": 6,
        "scene_diversity": ["hook", "identity", "setup", "evidence", "status", "cta"],
        "non_caption_visual_element_count": 6,
        "identity_present": True,
        "identity_mode": "branded_identity_card",
        "caption_safe_area": {"left": 96, "right": 96, "bottom": 220},
        "caption_safe_area_validated": True,
        "text_clipping": False,
        "scene_transitions": True,
        "static_background_only": False,
        "caption_only_visuals": False,
          "brand_opening_present": True,
          "brand_closing_present": True,
          "brand_sting_present": True,
          "narration_script_matches_package": True,
        "creative_status": "CREATIVE_QA_PASSED",
        "product_visual_count": 1,
        "hook_qa": {"status": "PASSED", "blockers": []},
        "gamcryp_product_placement": True,
        "frame_qa": {"status": "PASSED", "frames": ["a", "b", "c", "d", "e"]},
        "primary_visual_elements": ["identity_card", "setup_diagram", "mechanics_flow", "evidence_metric_card", "branded_cta"],
    }
    base.update(overrides)
    return base


def _quality_result(tmp_path: Path, quality: dict):
    video = tmp_path / "short.mp4"
    caption = tmp_path / "short.srt"
    audio = tmp_path / "short.mp3"
    for path in (video, caption, audio):
        path.write_bytes(b"asset")
    return RenderResult("content", "package", "SHORT_FORM", RENDER_READY, None, str(video), str(caption), str(audio), 30.0, 1080, 1920, "Sarah", APPROVED_VOICES[0][1], "model", "evidence", None, quality_metadata=quality)


def test_static_text_only_short_is_not_ready(tmp_path: Path) -> None:
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(meaningful_scene_count=1, scene_diversity=["same"], non_caption_visual_element_count=0, scene_transitions=False)))
    assert any("fewer than five" in blocker for blocker in blockers)
    assert any("scene diversity" in blocker for blocker in blockers)


def test_subtitle_only_changes_do_not_count_as_scene_diversity(tmp_path: Path) -> None:
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(scene_diversity=["caption", "caption", "caption", "caption", "caption", "caption"])))
    assert any("scene diversity" in blocker for blocker in blockers)


def test_five_plus_meaningful_scenes_pass_quality_gate(tmp_path: Path) -> None:
    result = _quality_result(tmp_path, _short_result_with_quality(meaningful_scene_count=5, scene_diversity=["hook", "identity", "setup", "evidence", "cta"]))
    assert validate_render(result) == ()


def test_reused_narration_must_match_current_package_script(tmp_path: Path) -> None:
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(narration_script_matches_package=False)))
    assert any("narration does not match" in blocker for blocker in blockers)


def test_logo_and_missing_logo_identity_modes_are_explicit(tmp_path: Path) -> None:
    assert _short_result_with_quality(identity_mode="official_logo")["identity_mode"] == "official_logo"
    assert _short_result_with_quality(identity_mode="branded_identity_card")["identity_mode"] == "branded_identity_card"
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(identity_present=False, identity_mode="none")))
    assert any("identity" in blocker for blocker in blockers)


def test_caption_safe_area_is_required(tmp_path: Path) -> None:
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(caption_safe_area={"left": 20, "right": 20, "bottom": 80})))
    assert any("safe-area" in blocker for blocker in blockers)
