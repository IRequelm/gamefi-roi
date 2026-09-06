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
import textwrap
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.config.settings import Settings
from app.content_package.generator import ContentPackage, build_content_packages, validate_package
from app.content_inventory.inventory import LONG_FORM_MIN_SECONDS, LONG_FORM_MIN_WORDS
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
    quality_metadata: dict[str, Any] | None = None


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
    if package.format == LONG_FORM and (package.estimated_narration_words < LONG_FORM_MIN_WORDS or package.estimated_duration_seconds < LONG_FORM_MIN_SECONDS):
        raise RenderError("long-form evidence-backed narration budget is insufficient")
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
    logo_path = _local_logo_path(package)
    duration = max(1, _audio_duration(audio, run) or _estimate_duration(job.script))
    quality_metadata = _short_quality_metadata(package, duration, logo_path) if job.format == SHORT_FORM else None
    scene_text_paths = _write_scene_text_files(metadata_dir, package, quality_metadata)
    audio_input = 1
    input_args = ["-i", str(audio)]
    video_map = "[vout]"
    filter_graph = _build_motion_filter(
        package=package,
        duration=duration,
        caption_path=caption_path,
        scene_text_paths=scene_text_paths,
        title_path=title_path,
        logo_path=logo_path,
        short_form=job.format == SHORT_FORM,
    )
    if logo_path is not None:
        input_args = ["-loop", "1", "-i", str(logo_path), "-i", str(audio)]
        audio_input = 2
    command = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x071329:s={job.width}x{job.height}:r=30",
        *input_args, "-t", str(duration), "-filter_complex", filter_graph,
        "-map", video_map, "-map", f"{audio_input}:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video_path),
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
    if job.format == LONG_FORM and duration < LONG_FORM_MIN_SECONDS:
        return _failed(package, "rendered long-form video is shorter than the evidence-backed minimum", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    result = RenderResult(package.source_inventory_item_id, package.package_id, job.format, RENDER_READY, None, str(video_path), str(caption_path), str(audio), duration, job.width, job.height, voice_name, voice_id, narration.metadata.model_id, job.evidence_fingerprint, str(metadata_dir / f"{package.package_id}.json"), (now or datetime.now(UTC)).isoformat(), quality_metadata)
    blockers = validate_render(result)
    if blockers:
        return _failed(package, "; ".join(blockers), evidence=job.evidence_fingerprint, width=job.width, height=job.height)
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
    if result.format == LONG_FORM and (result.duration_seconds is None or result.duration_seconds < LONG_FORM_MIN_SECONDS):
        blockers.append("long-form duration is below the evidence-backed minimum")
    if result.format == SHORT_FORM:
        blockers.extend(_short_quality_blockers(result))
    return tuple(blockers)


SHORT_MIN_MEANINGFUL_SCENES = 5
SHORT_CAPTION_SAFE_AREA = {"left": 96, "right": 96, "top": 150, "bottom": 220}


def _short_quality_metadata(package: ContentPackage, duration: float, logo_path: Path | None) -> dict[str, Any]:
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id) if package.opportunity_id else None
    name = opportunity.name if opportunity is not None else "GamCryp"
    opportunity_type = opportunity.opportunity_type if opportunity is not None else "CATALOG"
    points = [str(point["text"]) for point in package.factual_talking_points if point.get("text")]
    scene_count = 6
    return {
        "quality_version": "short-motion-card-v2",
        "meaningful_scene_count": scene_count,
        "minimum_meaningful_scene_count": SHORT_MIN_MEANINGFUL_SCENES,
        "scene_diversity": ["hook", "identity", "setup", "evidence", "status", "cta"],
        "non_caption_visual_element_count": scene_count,
        "identity_present": bool(package.opportunity_id or package.title_candidates),
        "identity_mode": "official_logo" if logo_path is not None else "branded_identity_card",
        "logo_asset": str(logo_path) if logo_path is not None else None,
        "opportunity_name": name,
        "opportunity_type": opportunity_type,
        "content_family": package.content_family,
        "evidence_point_count": len(points),
        "caption_safe_area": dict(SHORT_CAPTION_SAFE_AREA),
        "caption_max_words_per_chunk": 8,
        "duration_seconds": duration,
        "scene_transitions": True,
    }


def _write_scene_text_files(metadata_dir: Path, package: ContentPackage, quality: dict[str, Any] | None) -> tuple[Path, ...]:
    if quality is None:
        return ()
    points = [str(point["text"]) for point in package.factual_talking_points if point.get("text")]
    name = str(quality["opportunity_name"])
    type_label = str(quality["opportunity_type"]).replace("_", " ").title()
    evidence = points[0] if points else "Evidence-backed guidance is required before publishing."
    mechanics = points[1] if len(points) > 1 else evidence
    status = "ROI unavailable: missing reproducible inputs." if package.content_family == "WHY_ROI_UNAVAILABLE" else "Use the source-backed evidence and current model context."
    texts = (
        package.hook,
        f"{name}\n{type_label}",
        f"How it works\n{mechanics}",
        f"Evidence\n{evidence}",
        status,
        f"Review the evidence\n{package.canonical_source_url}",
    )
    paths = []
    for index, text in enumerate(texts, start=1):
        path = metadata_dir / f"{package.package_id}.scene-{index}.txt"
        path.write_text(_wrap_visual_text(text[:320]), encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def _wrap_visual_text(value: str, *, width: int = 28) -> str:
    return "\n".join(textwrap.fill(line.strip(), width=width, break_long_words=True, break_on_hyphens=False) for line in value.splitlines())


def _build_motion_filter(*, package: ContentPackage, duration: float, caption_path: Path, scene_text_paths: tuple[Path, ...], title_path: Path, logo_path: Path | None, short_form: bool) -> str:
    font = _filter_path(Path("C:/Windows/Fonts/arial.ttf"))
    captions = f"subtitles={_filter_path(caption_path)}:fontsdir={_filter_path(Path('C:/Windows/Fonts'))}:force_style='FontName=Arial,FontSize={20 if short_form else 18},PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A33,Outline=3,Alignment=2,MarginL=96,MarginR=96,MarginV=220'"
    if not short_form:
        return f"[0:v]drawtext=fontfile={font}:textfile={_filter_path(title_path)}:fontcolor=white:fontsize=64:x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=0x0d234dCC:boxborderw=24,{captions}[vout]"
    step = duration / 6.0
    scenes: list[str] = []
    layouts = (
        ("70", "220", "940", "390", "0x153766@0.96", "92", "330", "60"),
        ("70", "220", "940", "520", "0x102B52@0.96", "86", "310", "58"),
        ("70", "820", "940", "470", "0x162D4A@0.96", "100", "920", "50"),
        ("70", "820", "940", "470", "0x1A3158@0.96", "100", "930", "48"),
        ("70", "410", "940", "520", "0x202D55@0.96", "100", "530", "56"),
        ("70", "1160", "940", "330", "0x153766@0.98", "100", "1260", "52"),
    )
    for index, (x, y, width, height, color, tx, ty, size) in enumerate(layouts):
        start = index * step
        end = (index + 1) * step
        enable = f"between(t,{start:.3f},{end:.3f})"
        text_path = _filter_path(scene_text_paths[index])
        scenes.append(f"drawbox=x={x}:y={y}:w={width}:h={height}:color={color}:t=fill:enable='{enable}'")
        scenes.append(f"drawbox=x={x}:y={y}:w=16:h={height}:color=0x21D4FD@0.95:t=fill:enable='{enable}'")
        scenes.append(f"drawtext=fontfile={font}:textfile={text_path}:fontcolor=white:fontsize={size}:line_spacing=14:x={tx}:y={ty}:text_align=left:enable='{enable}'")
        scenes.append(f"drawtext=fontfile={font}:text='0{index + 1}':fontcolor=0x21D4FD:fontsize=34:x=870:y=180:enable='{enable}'")
    filter_graph = ",".join(scenes)
    if logo_path is not None:
        logo_overlay = f"[1:v]scale=240:240:force_original_aspect_ratio=decrease,format=rgba[logo];[0:v]{filter_graph}[cards];[cards][logo]overlay=x=760:y=270:enable='between(t,{step:.3f},{step * 2:.3f})'[composed];[composed]{captions}[vout]"
    else:
        filter_graph = f"{filter_graph},drawbox=x=760:y=500:w=190:h=190:color=0x21D4FD@0.18:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})',drawtext=fontfile={font}:text='G':fontcolor=0x21D4FD:fontsize=120:x=825:y=525:enable='between(t,{step:.3f},{step * 2:.3f})'"
        logo_overlay = f"[0:v]{filter_graph}[cards];[cards]{captions}[vout]"
    return logo_overlay


def _short_quality_blockers(result: RenderResult) -> list[str]:
    if result.format != SHORT_FORM:
        return []
    quality = result.quality_metadata or {}
    blockers: list[str] = []
    if int(quality.get("meaningful_scene_count", 0)) < SHORT_MIN_MEANINGFUL_SCENES:
        blockers.append("short-form render has fewer than five meaningful scenes")
    if len(set(quality.get("scene_diversity", ()))) < SHORT_MIN_MEANINGFUL_SCENES:
        blockers.append("short-form scene diversity is insufficient")
    if int(quality.get("non_caption_visual_element_count", 0)) < SHORT_MIN_MEANINGFUL_SCENES:
        blockers.append("short-form render has insufficient non-caption visual elements")
    if not quality.get("identity_present"):
        blockers.append("project or opportunity identity is missing")
    if quality.get("identity_mode") not in {"official_logo", "branded_identity_card"}:
        blockers.append("project identity cannot be represented safely")
    safe_area = quality.get("caption_safe_area", {})
    if safe_area.get("bottom", 0) < 180 or safe_area.get("left", 0) < 80 or safe_area.get("right", 0) < 80:
        blockers.append("captions do not meet the mobile safe-area contract")
    if not quality.get("scene_transitions"):
        blockers.append("short-form scene transitions are missing")
    return blockers


def _script_for(package: ContentPackage) -> str:
    parts = [package.hook]
    if package.format == LONG_FORM and package.narration_sections:
        parts.extend(str(section["text"]) for section in package.narration_sections if section.get("text"))
    else:
        parts.extend(str(point["text"]) for point in package.factual_talking_points if point.get("text"))
    parts.append(package.cta)
    return " ".join(part.strip() for part in parts if part.strip())


def _local_logo_path(package: ContentPackage) -> Path | None:
    if package.opportunity_id is None:
        return None
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id)
    if opportunity is None or not opportunity.logo_asset:
        return None
    candidate = Path("frontend") / opportunity.logo_asset.lstrip("/")
    return candidate if candidate.is_file() else None


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
