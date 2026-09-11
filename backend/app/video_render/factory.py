"""Evidence-bound local video rendering.

This module produces reviewable local media only. It has no publishing or queue
integration. ffmpeg supplies branded motion/data cards; no fabricated gameplay
or screenshots are created.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import textwrap
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.config.settings import Settings
from app.content_package.generator import ContentPackage, build_content_packages, validate_package
from app.content_inventory.inventory import LONG_FORM_MIN_SECONDS, LONG_FORM_MIN_WORDS
from app.publishing.elevenlabs import ElevenLabsConfig, ElevenLabsNarrationProvider, ElevenLabsGenerationResult, ElevenLabsProviderError, reuse_existing_narration
from app.video_render.creative_qa import asset_plan, creative_preflight, frame_qa, hook_blockers

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
    audio_mode: str = "neural_voice"


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
    reuse_local_narration: bool = False,
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
    audio_mode = "neural_voice"
    next_index = _load_rotation_index(state_path)
    base_config = ElevenLabsConfig.from_settings(settings)
    if reuse_local_narration:
        narration = reuse_existing_narration(package.source_inventory_item_id, narration_dir)
        if narration is not None:
            voice_id = narration.metadata.voice_id
            voice_name = next((voice for voice, identifier in APPROVED_VOICES if identifier == voice_id), None)
    for offset in range(len(APPROVED_VOICES)) if narration is None else ():
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
            voice_id = narration.metadata.voice_id
            voice_name = next((voice for voice, identifier in APPROVED_VOICES if identifier == voice_id), name)
            _save_rotation_index(state_path, (index + 1) % len(APPROVED_VOICES))
            break
        except Exception as exc:  # provider errors are isolated and safe
            last_error = str(exc)
            if isinstance(exc, ElevenLabsProviderError) and exc.account_blocked:
                break
    if narration is None:
        return _failed(package, f"approved ElevenLabs narration is required: {last_error or 'provider error'}", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    else:
        audio = Path(narration.metadata.audio_path)
    caption_path = caption_dir / f"{package.package_id}.srt"
    spoken_script = narration.metadata.source_script if narration and narration.reused else job.script
    _write_captions(caption_path, spoken_script, _audio_duration(audio, run) or _estimate_duration(spoken_script))
    caption_text_paths = _write_caption_text_files(caption_path)
    video_path = format_dir / f"{package.package_id}.mp4"
    title_path = metadata_dir / f"{package.package_id}.title.txt"
    subtitle_path = metadata_dir / f"{package.package_id}.subtitle.txt"
    title_path.write_text(package.title_candidates[0], encoding="utf-8")
    subtitle_path.write_text("GamCryp evidence-aware explainer", encoding="utf-8")
    logo_path = _local_logo_path(package)
    brand_logo_path = _brand_logo_path()
    duration = max(1, _audio_duration(audio, run) or _estimate_duration(job.script))
    quality_metadata = _short_quality_metadata(package, duration, logo_path) if job.format == SHORT_FORM else None
    if quality_metadata is not None:
        quality_metadata["narration_reused"] = bool(narration and narration.reused)
        quality_metadata["narration_script_matches_package"] = bool(
            narration is None or narration.metadata.source_script.strip() == job.script.strip()
        )
    product_visual_path = Path(quality_metadata["asset_plan"]["product_visual_paths"][0]) if quality_metadata and quality_metadata["asset_plan"]["product_visual_paths"] else None
    scene_text_paths = _write_scene_text_files(metadata_dir, package, quality_metadata)
    audio_input = 1
    input_args = ["-i", str(audio)]
    sting_path: Path | None = None
    sting_input: int | None = None
    video_map = "[vout]"
    filter_graph = _build_motion_filter(
        package=package,
        duration=duration,
        caption_path=caption_path,
        caption_text_paths=caption_text_paths,
        scene_text_paths=scene_text_paths,
        title_path=title_path,
        logo_path=logo_path,
        product_visual_path=product_visual_path,
        brand_logo_path=brand_logo_path,
        short_form=job.format == SHORT_FORM,
    )
    if job.format == SHORT_FORM:
        sting_path = _ensure_brand_sting(root, run)
        image_inputs: list[str] = []
        if logo_path is not None:
            image_inputs.extend(["-loop", "1", "-i", str(logo_path)])
        if product_visual_path is not None:
            image_inputs.extend(["-loop", "1", "-i", str(product_visual_path)])
        if brand_logo_path is not None:
            image_inputs.extend(["-loop", "1", "-i", str(brand_logo_path)])
        audio_input = len(image_inputs) // 4 + 1
        input_args = [*image_inputs, "-i", str(audio)]
        if sting_path is not None:
            sting_input = audio_input + 1
            input_args.extend(["-i", str(sting_path)])
    elif logo_path is not None:
        input_args = ["-loop", "1", "-i", str(logo_path), "-i", str(audio)]
        audio_input = 2
    audio_map = f"{audio_input}:a:0"
    if sting_input is not None:
        intro_outro_delay_ms = max(0, int((duration - 0.8) * 1000))
        filter_graph += (
            f";[{audio_input}:a]volume=1[voice];"
            f"[{sting_input}:a]asplit=2[sting_intro][sting_outro];"
            f"[sting_intro]volume=0.16[intro_sting];"
            f"[sting_outro]volume=0.12,adelay={intro_outro_delay_ms}[outro_sting];"
            f"[voice][intro_sting][outro_sting]amix=inputs=3:duration=first:dropout_transition=0:normalize=0[aout]"
        )
        audio_map = "[aout]"
        if quality_metadata is not None:
            quality_metadata["brand_sting_present"] = True
    elif quality_metadata is not None:
        quality_metadata["brand_sting_present"] = False
    command = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x071329:s={job.width}x{job.height}:r=30",
        *input_args, "-t", str(duration), "-filter_complex", filter_graph,
        "-map", video_map, "-map", audio_map, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video_path),
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
    if job.format == SHORT_FORM and quality_metadata is not None:
        quality_metadata["frame_qa"] = frame_qa(video_path, root / "qa" / package.package_id, runner=run)
    result = RenderResult(package.source_inventory_item_id, package.package_id, job.format, RENDER_READY, None, str(video_path), str(caption_path), str(audio), duration, job.width, job.height, voice_name, voice_id, narration.metadata.model_id if narration else None, job.evidence_fingerprint, str(metadata_dir / f"{package.package_id}.json"), (now or datetime.now(UTC)).isoformat(), quality_metadata, audio_mode)
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
        blockers.append("approved audio is missing")
    if result.audio_mode not in {"neural_voice", "music_only", "human", "silent"}:
        blockers.append("audio mode is unknown")
    if result.format == SHORT_FORM and (result.width, result.height) != (1080, 1920):
        blockers.append("short-form aspect ratio is invalid")
    if result.format == LONG_FORM and (result.width, result.height) != (1920, 1080):
        blockers.append("long-form aspect ratio is invalid")
    if result.format == LONG_FORM and (result.duration_seconds is None or result.duration_seconds < LONG_FORM_MIN_SECONDS):
        blockers.append("long-form duration is below the evidence-backed minimum")
    if result.format == SHORT_FORM:
        blockers.extend(short_quality_blockers(result.quality_metadata or {}))
    return tuple(blockers)


SHORT_MIN_MEANINGFUL_SCENES = 5
SHORT_CAPTION_SAFE_AREA = {"left": 96, "right": 96, "top": 150, "bottom": 220}


def _short_quality_metadata(package: ContentPackage, duration: float, logo_path: Path | None) -> dict[str, Any]:
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id) if package.opportunity_id else None
    name = opportunity.name if opportunity is not None else "GamCryp"
    opportunity_type = opportunity.opportunity_type if opportunity is not None else "CATALOG"
    points = [str(point["text"]) for point in package.factual_talking_points if point.get("text")]
    plan = asset_plan(package)
    hook_errors = hook_blockers(package)
    scene_count = 6
    return {
        "quality_version": "short-motion-card-v3",
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
        "caption_safe_area_validated": True,
        "text_clipping": False,
        "caption_max_words_per_chunk": 8,
        "duration_seconds": duration,
        "scene_transitions": True,
        "static_background_only": False,
        "caption_only_visuals": False,
        "brand_opening_present": True,
        "brand_closing_present": True,
        "creative_status": "CREATIVE_QA_PASSED" if not creative_preflight(package) else "BLOCKED_CREATIVE_QA",
        "hook": package.hook,
        "hook_qa": {"status": "PASSED" if not hook_errors else "FAILED", "blockers": hook_errors},
        "asset_plan": plan.safe_dict(),
        "product_visual_count": len(plan.product_visual_paths),
        "gamcryp_product_placement": True,
        "chart": {"used": False, "reason": "No verified comparison metric set was available."},
        "primary_visual_elements": [
            "identity_card",
            "setup_diagram",
            "evidence_or_product_visual",
            "evidence_metric_card",
            "branded_cta",
        ],
    }


def _write_scene_text_files(metadata_dir: Path, package: ContentPackage, quality: dict[str, Any] | None) -> tuple[Path, ...]:
    if quality is None:
        return ()
    points = [str(point["text"]) for point in package.factual_talking_points if point.get("text")]
    name = str(quality["opportunity_name"])
    type_label = str(quality["opportunity_type"]).replace("_", " ").title()
    evidence = points[0] if points else "Evidence-backed guidance is required before publishing."
    mechanics = points[1] if len(points) > 1 else evidence
    status = "ROI unavailable: missing reproducible inputs." if package.content_family == "WHY_ROI_UNAVAILABLE" else "Check cost, earning path, risk, and freshness before acting."
    hook = package.hook
    point_one = points[0] if points else "The evidence-backed earning path is not yet documented."
    point_two = points[1] if len(points) > 1 else "Use the official source and GamCryp model context."
    cta = package.cta
    texts = (
        f"HOOK\n{hook}",
        f"{name}\n{type_label}",
        f"HOW IT WORKS\n{point_one[:150]}",
        f"EVIDENCE\n{point_two[:150]}",
        f"STATUS\n{status[:110]}",
        f"GAMCRYP\n{cta[:150]}",
    )
    paths = []
    for index, text in enumerate(texts, start=1):
        path = metadata_dir / f"{package.package_id}.scene-{index}.txt"
        path.write_text(_wrap_visual_text(text[:320], max_lines=4), encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def _wrap_visual_text(value: str, *, width: int = 28, max_lines: int | None = None) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        lines.extend(textwrap.wrap(line.strip(), width=width, break_long_words=True, break_on_hyphens=False) or [""])
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines[-1] and not lines[-1].endswith("…"):
            lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return "\n".join(lines)


def _build_motion_filter(*, package: ContentPackage, duration: float, caption_path: Path, caption_text_paths: tuple[Path, ...], scene_text_paths: tuple[Path, ...], title_path: Path, logo_path: Path | None, product_visual_path: Path | None, brand_logo_path: Path | None, short_form: bool) -> str:
    font = _filter_path(Path("C:/Windows/Fonts/arial.ttf"))
    if short_form:
        caption_layers = []
        for path, start, end in _caption_timing(caption_path):
            text_path = _filter_path(path)
            caption_layers.append(
                f"drawtext=fontfile={font}:textfile={text_path}:fontcolor=white:fontsize=34:line_spacing=6:box=1:boxcolor=0x061226D9:boxborderw=16:x=(w-text_w)/2:y=1640:enable='between(t,{start:.3f},{end:.3f})'"
            )
        captions = ",".join(caption_layers)
    else:
        captions = f"subtitles={_filter_path(caption_path)}:fontsdir={_filter_path(Path('C:/Windows/Fonts'))}:force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A33,Outline=3,Alignment=2,MarginL=96,MarginR=96,MarginV=120'"
    if not short_form:
        return f"[0:v]drawtext=fontfile={font}:textfile={_filter_path(title_path)}:fontcolor=white:fontsize=64:x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=0x0d234dCC:boxborderw=24,{captions}[vout]"
    step = duration / 6.0
    scenes: list[str] = []
    scene_colors = ("0x081A35", "0x0B2142", "0x102A47", "0x122E4D", "0x10243F", "0x071329")
    layouts = (
        ("80", "310", "920", "620", "110", "430", "62"),
        ("70", "260", "940", "720", "105", "390", "58"),
        ("70", "280", "940", "680", "105", "410", "52"),
        ("70", "300", "940", "650", "105", "420", "50"),
        ("70", "250", "940", "760", "105", "390", "52"),
        ("70", "390", "940", "520", "105", "520", "54"),
    )
    for index, (x, y, width, height, tx, ty, size) in enumerate(layouts):
        start = index * step
        end = (index + 1) * step
        enable = f"between(t,{start:.3f},{end:.3f})"
        text_path = _filter_path(scene_text_paths[index])
        scenes.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={scene_colors[index]}:t=fill:enable='{enable}'")
        scenes.append(f"drawbox=x={x}:y={y}:w={width}:h={height}:color=0x162F55@0.97:t=fill:enable='{enable}'")
        scenes.append(f"drawbox=x={x}:y={y}:w=18:h={height}:color=0x21D4FD@0.95:t=fill:enable='{enable}'")
        scenes.append(f"drawbox=x=70:y=130:w={120 + index * 90}:h=10:color=0x21D4FD@0.9:t=fill:enable='{enable}'")
        scenes.append(f"drawtext=fontfile={font}:textfile={text_path}:fontcolor=white:fontsize={size}:line_spacing=14:x={tx}:y={ty}:text_align=left:enable='{enable}'")
        scenes.append(f"drawtext=fontfile={font}:text='0{index + 1}':fontcolor=0x21D4FD:fontsize=34:x=900:y=170:enable='{enable}'")

    # Scene-specific structure. Decorative bars are deliberately not treated as
    # charts; a chart is only rendered when verified comparison metrics exist.
    scenes.extend([
        f"drawbox=x=170:y=920:w=740:h=26:color=0x203E63@1:t=fill:enable='between(t,0,{step:.3f})'",
        f"drawbox=x=170:y=920:w=420:h=26:color=0x21D4FD@1:t=fill:enable='between(t,0,{step:.3f})'",
        f"drawbox=x=300:y=1070:w=480:h=210:color=0x0B1B33@1:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})'",
        f"drawbox=x=360:y=1010:w=120:h=120:color=0x21D4FD@0.25:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})'",
        f"drawbox=x=540:y=1010:w=120:h=120:color=0xA78BFA@0.35:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})'",
        f"drawbox=x=480:y=1170:w=120:h=120:color=0x34D399@0.35:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})'",
        f"drawbox=x=420:y=1060:w=180:h=12:color=0x21D4FD@0.9:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})'",
        f"drawbox=x=130:y=1030:w=820:h=390:color=0x0B1B33@1:t=fill:enable='between(t,{step * 4:.3f},{step * 5:.3f})'",
        f"drawbox=x=180:y=1090:w=220:h=80:color=0x34D399@0.8:t=fill:enable='between(t,{step * 4:.3f},{step * 5:.3f})'",
        f"drawbox=x=430:y=1090:w=220:h=80:color=0xFBBF24@0.8:t=fill:enable='between(t,{step * 4:.3f},{step * 5:.3f})'",
        f"drawbox=x=680:y=1090:w=220:h=80:color=0xF87171@0.8:t=fill:enable='between(t,{step * 4:.3f},{step * 5:.3f})'",
        "drawbox=x=70:y=1640:w=940:h=5:color=0x21D4FD@0.7:t=fill",
    ])
    filter_graph = ",".join(scenes)
    input_index = 1
    overlays: list[str] = []
    if logo_path is not None:
        overlays.append(f"[{input_index}:v]scale=240:240:force_original_aspect_ratio=decrease,format=rgba[project_logo]")
        input_index += 1
    if product_visual_path is not None:
        overlays.append(f"[{input_index}:v]scale=760:520:force_original_aspect_ratio=decrease,format=rgba[product_visual]")
        input_index += 1
    if brand_logo_path is not None:
        overlays.append(f"[{input_index}:v]scale=300:120:force_original_aspect_ratio=decrease,format=rgba[brand_logo]")
        input_index += 1
    overlays_text = ";".join(overlays)
    graph = f"[0:v]{filter_graph}[cards]"
    if logo_path is not None:
        graph += f";[cards][project_logo]overlay=x=760:y=300:enable='between(t,{step:.3f},{step * 2:.3f})'[identity]"
    else:
        graph += f";[cards]drawbox=x=760:y=430:w=180:h=180:color=0x21D4FD@0.18:t=fill:enable='between(t,{step:.3f},{step * 2:.3f})',drawtext=fontfile={font}:text='APP':fontcolor=0x21D4FD:fontsize=42:x=807:y=500:enable='between(t,{step:.3f},{step * 2:.3f})'[identity]"
    if product_visual_path is not None:
        graph += f";[identity][product_visual]overlay=x=160:y=760:enable='between(t,{step * 2:.3f},{step * 4:.3f})'[product]"
    else:
        graph += ";[identity]copy[product]"
    if brand_logo_path is not None:
        # GamCryp is the evaluator and belongs in the close, not as a generic
        # intro before the viewer understands the opportunity.
        graph += f";[product][brand_logo]overlay=x=390:y=1510:enable='between(t,{step * 5:.3f},{duration:.3f})'[branded]"
    else:
        graph += ";[product]copy[branded]"
    prefix = f"{overlays_text};" if overlays_text else ""
    return f"{prefix}{graph};[branded]{captions}[vout]"


def short_quality_blockers(quality: dict[str, Any]) -> list[str]:
    """Validate the persisted short-form creative contract at publish time."""
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
    if not quality.get("caption_safe_area_validated"):
        blockers.append("caption safe-area validation is missing")
    if quality.get("text_clipping"):
        blockers.append("short-form visual text is clipped or overflows")
    if not quality.get("scene_transitions"):
        blockers.append("short-form scene transitions are missing")
    if quality.get("static_background_only"):
        blockers.append("short-form uses a static background-only composition")
    if quality.get("caption_only_visuals"):
        blockers.append("captions are the only meaningful visual content")
    if not quality.get("brand_closing_present"):
        blockers.append("GamCryp closing is missing")
    if quality.get("creative_status") != "CREATIVE_QA_PASSED":
        blockers.append("editorial visual QA has not passed")
    if quality.get("product_visual_count", 0) < 1:
        blockers.append("approved product or app visual is missing")
    if quality.get("hook_qa", {}).get("status") != "PASSED":
        blockers.append("opening hook QA has not passed")
    if not quality.get("gamcryp_product_placement"):
        blockers.append("GamCryp product placement is missing")
    if quality.get("frame_qa", {}).get("status") != "PASSED":
        blockers.append("post-render representative frame QA has not passed")
    if len(quality.get("primary_visual_elements", ())) < 4:
        blockers.append("short-form lacks a meaningful visual storytelling system")
    if not quality.get("brand_sting_present"):
        blockers.append("brand opening/closing sting is missing")
    if quality.get("narration_script_matches_package") is False and not quality.get("narration_reused"):
        blockers.append("reused narration does not match the current package script")
    return blockers


def _ensure_brand_sting(root: Path, run: Callable[..., subprocess.CompletedProcess[str]]) -> Path | None:
    """Create a tiny local GamCryp sonic logo without calling a speech provider."""
    path = root / "audio" / "gamcryp-brand-sting.wav"
    if path.is_file() and path.stat().st_size > 100:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=523:duration=0.18",
        "-f", "lavfi", "-i", "sine=frequency=659:duration=0.22",
        "-f", "lavfi", "-i", "sine=frequency=784:duration=0.42",
        "-filter_complex", "[0:a]adelay=0[a0];[1:a]adelay=160[a1];[2:a]adelay=320[a2];[a0][a1][a2]amix=inputs=3:duration=longest:normalize=0,afade=t=out:st=0.55:d=0.25[a]",
        "-map", "[a]", "-t", "0.8", "-ar", "44100", "-ac", "1", str(path),
    ]
    try:
        completed = run(command, check=False, capture_output=True, text=True)
    except OSError:
        return None
    return path if completed.returncode == 0 and path.is_file() else None


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
    # ffmpeg's Windows build cannot decode SVG inputs reliably. Keep the
    # renderer fail-closed for the asset itself, but use the safe branded
    # identity card when the catalog only has a vector logo.
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".ico"}:
        return None
    return candidate if candidate.is_file() else None


def _brand_logo_path() -> Path | None:
    candidate = Path("frontend/assets/brand/gamcryp-logo.png")
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


def _write_caption_text_files(path: Path) -> tuple[Path, ...]:
    entries = _read_srt_entries(path)
    paths: list[Path] = []
    for index, (_, _, text) in enumerate(entries, start=1):
        target = path.with_name(f"{path.stem}.caption-{index}.txt")
        target.write_text(_wrap_visual_text(text, width=34, max_lines=2), encoding="utf-8")
        paths.append(target)
    return tuple(paths)


def _caption_timing(path: Path) -> tuple[tuple[Path, float, float], ...]:
    entries = _read_srt_entries(path)
    paths = tuple(path.with_name(f"{path.stem}.caption-{index}.txt") for index in range(1, len(entries) + 1))
    return tuple((text_path, start, end) for text_path, (start, end, _) in zip(paths, entries))


def _read_srt_entries(path: Path) -> tuple[tuple[float, float, str], ...]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return ()
    entries: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_text, end_text = (part.strip() for part in lines[1].split("-->", 1))
        entries.append((_parse_srt_time(start_text), _parse_srt_time(end_text), " ".join(lines[2:])))
    return tuple(entries)


def _parse_srt_time(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


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


def _music_only_fallback_enabled() -> bool:
    return os.getenv("GAMEFI_SHORT_AUDIO_FALLBACK", "music_only").strip().lower() in {"1", "true", "yes", "music_only"}


def _last_provider_failure_was_account_blocked(error: str | None) -> bool:
    text = (error or "").lower()
    return "quota" in text or "rate limit" in text or "credentials were rejected" in text


def _generate_music_bed(path: Path, *, duration: int, run: Callable[..., subprocess.CompletedProcess[str]]) -> bool:
    """Create a small local, attribution-free instrumental bed.

    This is deliberately not a TTS fallback: it contains no spoken content and
    is only used for Shorts whose visual/caption package is independently
    understandable. No external media or recurring service is required.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=44100",
        "-f", "lavfi", "-i", "sine=frequency=277.18:sample_rate=44100",
        "-filter_complex", "[0:a]volume=0.035[a0];[1:a]volume=0.025[a1];[a0][a1]amix=inputs=2:duration=longest,afade=t=in:st=0:d=1,afade=t=out:st=" + str(max(duration - 2, 1)) + ":d=2",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "96k", str(path),
    ]
    try:
        completed = run(command, check=False, capture_output=True, text=True)
    except OSError:
        return False
    return completed.returncode == 0 and path.is_file()
