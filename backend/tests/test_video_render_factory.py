from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace

from app.publishing.elevenlabs import ElevenLabsGenerationResult, NarrationAssetMetadata
from app.video_render.factory import (
    APPROVED_VOICES,
    NOT_READY,
    RENDER_READY,
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
    Path(command[-1]).write_bytes(b"video")
    return CompletedProcess(command, 0, stdout="", stderr="")


def test_ready_short_renders_with_captions_and_evidence(tmp_path: Path) -> None:
    calls: list[str] = []
    result = render_package(_package(), settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=_provider_factory(tmp_path, calls), command_runner=_runner)

    assert result.status == RENDER_READY, result.reason
    assert result.width == 1080 and result.height == 1920
    assert Path(result.video_path).is_file()
    assert Path(result.caption_path).is_file()
    assert calls == [APPROVED_VOICES[0][1]]
    assert validate_render(result) == ()
    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["evidence_fingerprint"] == _package().evidence_fingerprint


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


def test_non_ready_package_cannot_become_render_job() -> None:
    package = replace(_package(), content_family="FINANCIAL_ROI")

    try:
        build_render_job(package)
    except RuntimeError as error:
        assert "READY" in str(error) or "unsupported" in str(error)
    else:
        raise AssertionError("blocked package unexpectedly rendered")
