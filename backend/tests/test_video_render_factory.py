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
from app.video_render.factory import _build_motion_filter, _script_for, _select_product_visual, _visual_scene_timings
from app.content_package.generator import build_content_packages


def test_visual_scene_timings_follow_caption_groups() -> None:
    captions = tuple((Path(f"caption-{index}.txt"), float(index * 6), float((index + 1) * 6)) for index in range(7))
    assert _visual_scene_timings(captions, 45.0) == (
        (0.0, 6.0),
        (6.0, 12.0),
        (12.0, 18.0),
        (18.0, 30.0),
        (30.0, 36.0),
        (36.0, 42.0),
    )


def test_product_visual_rotation_is_deterministic_and_uses_approved_captures(tmp_path: Path) -> None:
    paths = tuple(tmp_path / name for name in ("official-a.png", "official-b.png", "official-c.png"))

    first = _select_product_visual(paths, "package-a")
    second = _select_product_visual(paths, "package-a")

    assert first == second
    assert first in paths
    assert _select_product_visual((), "package-a") is None


def test_product_scene_uses_asset_led_product_view_composition(tmp_path: Path) -> None:
    caption = tmp_path / "captions.srt"
    caption.write_text("1\n00:00:00,000 --> 00:00:05,000\nEvidence\n", encoding="utf-8")
    scenes = []
    for index in range(6):
        path = tmp_path / f"scene-{index}.txt"
        text = "EVIDENCE\nA supported host, storage, provider software, and\nnetwork access are required.\nAdditional collateral is required.\nOperational funds may be needed.\n"
        path.write_text(text if index == 3 else "Scene\ncopy\n", encoding="utf-8")
        scenes.append(path)
    graph = _build_motion_filter(
        package=None,  # type: ignore[arg-type]
        duration=5,
        caption_path=caption,
        caption_text_paths=(),
        scene_text_paths=tuple(scenes),
        title_path=tmp_path / "title.txt",
        logo_path=None,
        product_visual_path=tmp_path / "product.png",
        brand_logo_path=None,
        short_form=True,
    )
    assert "fontsize=30:line_spacing=6" in graph
    assert "text='OFFICIAL PRODUCT VIEW'" in graph
    assert "overlay=x=30+sin(t*0.6)*12:y=350" in graph
    assert "scale=1020:660:force_original_aspect_ratio=decrease" in graph
    assert "drawbox=x=30:y=350+abs(sin(t*0.85)*620)" in graph
    assert "SOURCE-BOUND / VERIFY BEFORE ACTION" in graph


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
    result = render_package(package, settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, calls), command_runner=_runner, allow_narration_generation=True)

    assert result.status == RENDER_READY, result.reason
    assert result.width == 1080 and result.height == 1920
    assert Path(result.video_path).is_file()
    assert Path(result.caption_path).is_file()
    assert calls == []
    assert result.audio_mode == "music_only"
    assert validate_render(result) == ()
    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["evidence_fingerprint"] == package.evidence_fingerprint


def test_ready_long_uses_landscape_dimensions(tmp_path: Path) -> None:
    package = _package("LONG_FORM")
    result = render_package(package, settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, []), command_runner=_runner, allow_narration_generation=True, creative_approval=True)

    assert result.status == RENDER_READY, result.reason
    assert (result.width, result.height) == (1920, 1080)


def test_long_script_uses_distinct_bound_evidence_sections_without_filler() -> None:
    package = _package("LONG_FORM")
    script = _script_for(package)

    assert all(f"Evidence-backed detail {index}" in script for index in range(6))
    assert "Opportunity or method context" not in script


def test_short_never_calls_tts_provider_when_narration_is_missing(tmp_path: Path) -> None:
    calls: list[str] = []
    result = render_package(_package(), settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, calls, fail=True), command_runner=_runner, allow_narration_generation=True)

    assert result.status == NOT_READY
    assert calls == []
    assert "product or app visual is missing" in (result.reason or "")


def test_short_does_not_call_elevenlabs_even_when_provider_would_fail(tmp_path: Path) -> None:
    calls: list[str] = []

    def provider_factory(config):
        calls.append(config.voice_id)
        raise ElevenLabsProviderError("ElevenLabs account quota or rate limit was reached", account_blocked=True)

    result = render_package(
        _package(), settings=_settings(tmp_path), root=tmp_path / "render",
        narration_provider_factory=provider_factory, command_runner=_runner,
        allow_narration_generation=True,
    )

    assert result.status == NOT_READY
    assert result.voice_id is None
    assert calls == []


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
    base.update(overrides)
    return base


def _quality_result(tmp_path: Path, quality: dict):
    video = tmp_path / "short.mp4"
    caption = tmp_path / "short.srt"
    audio = tmp_path / "short.mp3"
    for path in (video, caption, audio):
        path.write_bytes(b"asset")
    return RenderResult("content", "package", "SHORT_FORM", RENDER_READY, None, str(video), str(caption), str(audio), 30.0, 1080, 1920, None, None, None, "evidence", None, quality_metadata=quality, audio_mode="music_only")


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


def test_static_product_capture_is_not_ready(tmp_path: Path) -> None:
    quality = _short_result_with_quality(product_visual_motion="static_capture")
    blockers = validate_render(_quality_result(tmp_path, quality))
    assert any("product visual lacks motion" in blocker for blocker in blockers)


def test_reused_narration_must_match_current_package_script(tmp_path: Path) -> None:
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(narration_script_matches_package=False)))
    assert any("narration does not match" in blocker for blocker in blockers)


def test_reused_narration_does_not_bypass_script_validation(tmp_path: Path) -> None:
    quality = _short_result_with_quality(narration_script_matches_package=False)
    quality["narration_reused"] = True
    blockers = validate_render(_quality_result(tmp_path, quality))
    assert any("narration does not match" in blocker for blocker in blockers)


def test_logo_and_missing_logo_identity_modes_are_explicit(tmp_path: Path) -> None:
    assert _short_result_with_quality(identity_mode="official_logo")["identity_mode"] == "official_logo"
    assert _short_result_with_quality(identity_mode="branded_identity_card")["identity_mode"] == "branded_identity_card"
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(identity_present=False, identity_mode="none")))
    assert any("identity" in blocker for blocker in blockers)


def test_caption_safe_area_is_required(tmp_path: Path) -> None:
    blockers = validate_render(_quality_result(tmp_path, _short_result_with_quality(caption_safe_area={"left": 20, "right": 20, "bottom": 80})))
    assert any("safe-area" in blocker for blocker in blockers)
