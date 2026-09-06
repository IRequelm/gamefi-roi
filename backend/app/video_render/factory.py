"""Evidence-bound local video rendering.

This module produces reviewable local media only. It has no publishing or queue
integration. ffmpeg supplies branded motion/data cards; no fabricated gameplay
or screenshots are created.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.config.settings import Settings
from app.content_package.generator import ContentPackage, build_content_packages, validate_package
from app.publishing.elevenlabs import ElevenLabsConfig, ElevenLabsNarrationProvider, ElevenLabsGenerationResult

SHORT_FORM = "SHORT_FORM"
LONG_FORM = "LONG_FORM"
RENDER_READY = "RENDER_READY"
NOT_READY = "NOT_READY"
APPROVED_VOICES = (
    ("Sarah", "EXAVITQu4vr4xnSDxMaL"),
    ("Bella", "FGY2WhTYpPnrIDTdsKH5"),
    ("Laura", "hpp4J3VqNfWAUOO0d1Us"),
)


@dataclass(frozen=True)
class RenderJob:
    package: ContentPackage
    script: str
    format: str
    width: int
    height: int
    duration_target_seconds: int
    evidence_fingerprint: str


@dataclass(frozen=True)
class RenderResult:
    content_id: str
    package_id: str
    format: str
    status: str
    reason: str | None
    video_path: str | None
    caption_path: str | None
    narration_path: str | None
    duration_seconds: float | None
    width: int
    height: int
    voice_name: str | None
    voice_id: str | None
    model_id: str | None
    evidence_fingerprint: str
    metadata_path: str | None
    rendered_at: str | None = None


class RenderError(RuntimeError):
    """A safe local rendering failure."""


def build_render_job(package: ContentPackage) -> RenderJob:
    if package.generation_status != "READY_FOR_REVIEW":
        raise RenderError("content package is not READY_FOR_REVIEW")
    if package.content_family == "FINANCIAL_ROI":
        raise RenderError("unsupported financial content cannot render")
    if not validate_package(package):
        raise RenderError("content package evidence validation failed")
    if package.format not in {SHORT_FORM, LONG_FORM}:
        raise RenderError("unsupported render format")
    script = _script_for(package)
    if not script:
        raise RenderError("content package has no supported narration text")
    width, height = (1080, 1920) if package.format == SHORT_FORM else (1920, 1080)
    target = 45 if package.format == SHORT_FORM else 600
    return RenderJob(package, script, package.format, width, height, target, package.evidence_fingerprint)


def render_package(
    package: ContentPackage,
    *,
    settings: Settings,
    root: Path = Path("data/local/video_render"),
    now: datetime | None = None,
    narration_provider_factory: Callable[[ElevenLabsConfig], ElevenLabsNarrationProvider] | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> RenderResult:
    try:
        job = build_render_job(package)
    except RenderError as exc:
        return _failed(package, str(exc))

    run = command_runner or subprocess.run
    root = Path(root)
    format_dir = root / ("short" if job.format == SHORT_FORM else "long")
    caption_dir = root / "captions"
    metadata_dir = root / "metadata"
    narration_dir = root / "narration"
    for directory in (format_dir, caption_dir, metadata_dir, narration_dir):
        directory.mkdir(parents=True, exist_ok=True)

    script_fingerprint = hashlib.sha256(job.script.encode("utf-8")).hexdigest()
    state_path = narration_dir / "voice_rotation.json"
    provider_factory = narration_provider_factory or ElevenLabsNarrationProvider
    narration: ElevenLabsGenerationResult | None = None
    voice_name: str | None = None
    voice_id: str | None = None
    last_error: str | None = None
    next_index = _load_rotation_index(state_path)
    base_config = ElevenLabsConfig.from_settings(settings)
    for offset in range(len(APPROVED_VOICES)):
        index = (next_index + offset) % len(APPROVED_VOICES)
        name, candidate_id = APPROVED_VOICES[index]
        try:
            config = ElevenLabsConfig(
                api_key=base_config.api_key,
                voice_id=candidate_id,
                model_id=base_config.model_id,
                output_directory=narration_dir,
                output_format=base_config.output_format,
                timeout_seconds=base_config.timeout_seconds,
            )
            narration = provider_factory(config).generate(content_id=package.source_inventory_item_id, script=job.script, now=now)
            voice_name, voice_id = name, candidate_id
            _save_rotation_index(state_path, (index + 1) % len(APPROVED_VOICES))
            break
        except Exception as exc:  # provider errors are isolated and safe
            last_error = str(exc)
    if narration is None:
        return _failed(package, f"all approved neural voices failed: {last_error or 'provider error'}", evidence=job.evidence_fingerprint, width=job.width, height=job.height)

    audio = Path(narration.metadata.audio_path)
    caption_path = caption_dir / f"{package.package_id}.srt"
    _write_captions(caption_path, job.script, _audio_duration(audio, run) or _estimate_duration(job.script))
    video_path = format_dir / f"{package.package_id}.mp4"
    title_path = metadata_dir / f"{package.package_id}.title.txt"
    subtitle_path = metadata_dir / f"{package.package_id}.subtitle.txt"
    title_path.write_text(package.title_candidates[0], encoding="utf-8")
    subtitle_path.write_text("GamCryp evidence-aware explainer", encoding="utf-8")
    command = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x071329:s={job.width}x{job.height}:r=30",
        "-i", str(audio), "-t", str(max(1, _audio_duration(audio, run) or _estimate_duration(job.script))),
        "-vf", f"drawtext=fontfile={_filter_path(Path('C:/Windows/Fonts/arial.ttf'))}:textfile={_filter_path(title_path)}:fontcolor=white:fontsize={72 if job.format == SHORT_FORM else 64}:x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=0x0d234dCC:boxborderw=24,subtitles={_filter_path(caption_path)}:fontsdir={_filter_path(Path('C:/Windows/Fonts'))}:force_style='FontName=Arial,FontSize={20 if job.format == SHORT_FORM else 18},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=120'",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video_path),
    ]
    try:
        completed = run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        return _failed(package, "ffmpeg is unavailable", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    if completed.returncode != 0 or not video_path.is_file():
        return _failed(package, f"video render failed: {_safe_process_reason(completed.stderr)}", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    duration = _probe_video(video_path, run)
    if duration is None:
        return _failed(package, "rendered video is not decodable", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    result = RenderResult(package.source_inventory_item_id, package.package_id, job.format, RENDER_READY, None, str(video_path), str(caption_path), str(audio), duration, job.width, job.height, voice_name, voice_id, narration.metadata.model_id, job.evidence_fingerprint, str(metadata_dir / f"{package.package_id}.json"), (now or datetime.now(UTC)).isoformat())
    Path(result.metadata_path).write_text(json.dumps({**asdict(result), "asset_checksums": {"video": _sha256(video_path), "audio": _sha256(audio), "captions": _sha256(caption_path)}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def validate_render(result: RenderResult) -> tuple[str, ...]:
    blockers: list[str] = []
    if result.status != RENDER_READY:
        blockers.append(result.reason or "render is not ready")
    if result.video_path is None or not Path(result.video_path).is_file():
        blockers.append("rendered video is missing")
    if result.caption_path is None or not Path(result.caption_path).is_file():
        blockers.append("captions are missing")
    if result.narration_path is None or not Path(result.narration_path).is_file():
        blockers.append("approved narration is missing")
    if result.format == SHORT_FORM and (result.width, result.height) != (1080, 1920):
        blockers.append("short-form aspect ratio is invalid")
    if result.format == LONG_FORM and (result.width, result.height) != (1920, 1080):
        blockers.append("long-form aspect ratio is invalid")
    return tuple(blockers)


def _script_for(package: ContentPackage) -> str:
    parts = [package.hook]
    parts.extend(str(point["text"]) for point in package.factual_talking_points if point.get("text"))
    parts.append(package.cta)
    return " ".join(part.strip() for part in parts if part.strip())


def _failed(package: ContentPackage, reason: str, *, evidence: str = "", width: int = 0, height: int = 0) -> RenderResult:
    return RenderResult(package.source_inventory_item_id, package.package_id, package.format, NOT_READY, reason, None, None, None, None, width, height, None, None, None, evidence or package.evidence_fingerprint, None, None)


def _load_rotation_index(path: Path) -> int:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return int(value.get("next_index", 0)) % len(APPROVED_VOICES)
    except (OSError, ValueError, TypeError):
        return 0


def _save_rotation_index(path: Path, value: int) -> None:
    path.write_text(json.dumps({"next_index": value, "version": 1}, sort_keys=True) + "\n", encoding="utf-8")


def _write_captions(path: Path, text: str, duration: float) -> None:
    words = text.split()
    chunks = [" ".join(words[index:index + 8]) for index in range(0, len(words), 8)] or [text]
    step = max(duration / len(chunks), 0.5)
    lines = []
    for index, chunk in enumerate(chunks):
        lines.append(f"{index + 1}\n{_srt_time(index * step)} --> {_srt_time((index + 1) * step)}\n{chunk}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def _srt_time(seconds: float) -> str:
    millis = int(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _audio_duration(path: Path, run: Callable[..., subprocess.CompletedProcess[str]]) -> float | None:
    try:
        completed = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], check=False, capture_output=True, text=True)
        return float(completed.stdout.strip()) if completed.returncode == 0 else None
    except (OSError, ValueError):
        return None


def _probe_video(path: Path, run: Callable[..., subprocess.CompletedProcess[str]]) -> float | None:
    return _audio_duration(path, run)


def _estimate_duration(text: str) -> float:
    return max(3.0, len(text.split()) / 2.4)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _filter_path(path: Path) -> str:
    """Use a drive-safe path in ffmpeg filter arguments on Windows."""

    relative = os.path.relpath(path, Path.cwd())
    return relative.replace("\\", "/").replace(":", "\\:")


def _safe_process_reason(stderr: str | None) -> str:
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    return lines[-1][:240] if lines else "unknown ffmpeg error"
