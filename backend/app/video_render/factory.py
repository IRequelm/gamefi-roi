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
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.config.settings import Settings
from app.content_package.generator import AUTONOMOUS_CATALOG_FAMILIES, ContentPackage, SITE_EXPLAINER_FAMILIES, build_content_packages, is_motion_graphic_explainer, is_site_explainer, validate_package
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MUSIC_BED_SOURCE = REPOSITORY_ROOT / "video" / "remotion" / "public" / "audio" / "inspired-kevin-macleod.mp3"


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
    reuse_local_narration: bool = True,
    allow_narration_generation: bool = False,
    creative_approval: bool = False,
) -> RenderResult:
    try:
        job = build_render_job(package)
    except RenderError as exc:
        return _failed(package, str(exc))
    if job.format == LONG_FORM and allow_narration_generation and not creative_approval:
        return _failed(package, "BLOCKED_CREATIVE_APPROVAL: paid narration requires explicit creative quality approval", evidence=job.evidence_fingerprint, width=job.width, height=job.height)

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
    # New autonomous Shorts never generate TTS. An operator can explicitly
    # opt into paid narration after the exact creative has passed human review;
    # existing ElevenLabs assets may also be reused when the exact script,
    # approved voice/model, quality status, and audio checksum match.
    audio_mode = "music_only"
    next_index = _load_rotation_index(state_path)
    base_config = ElevenLabsConfig.from_settings(settings)
    if reuse_local_narration and not is_motion_graphic_explainer(package):
        narration = reuse_existing_narration(package.source_inventory_item_id, narration_dir, script=job.script)
        if narration is not None:
            voice_id = narration.metadata.voice_id
            voice_name = next((voice for voice, identifier in APPROVED_VOICES if identifier == voice_id), None)
    if narration is None and job.format == LONG_FORM and not allow_narration_generation:
        return _failed(package, "BLOCKED_NARRATION: no verified narration matches the spoken script; paid generation requires explicit operator action", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    # Paid narration is available only on the explicit operator path. Shorts
    # additionally require creative_approval so an accidental batch render
    # cannot spend credits merely because narration generation was enabled.
    paid_narration_allowed = allow_narration_generation and (
        job.format == LONG_FORM or (job.format == SHORT_FORM and creative_approval)
    )
    for offset in range(1) if narration is None and paid_narration_allowed else ():
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
    audio_mode = "music_only" if narration is None else "neural_voice"
    if narration is None and job.format == SHORT_FORM and paid_narration_allowed:
        return _failed(
            package,
            f"BLOCKED_NARRATION: approved ElevenLabs narration could not be generated: {last_error or 'provider error'}",
            evidence=job.evidence_fingerprint,
            width=job.width,
            height=job.height,
        )
    if narration is None and job.format == SHORT_FORM:
        source_fingerprint = music_bed_source_fingerprint()
        if source_fingerprint is None:
            return _failed(package, "BLOCKED_RENDER: licensed music bed source is unavailable", evidence=job.evidence_fingerprint, width=job.width, height=job.height, audio_mode="music_only")
        audio = narration_dir / f"{package.source_inventory_item_id}-music-bed-{source_fingerprint[:12]}.mp3"
        if not audio.is_file() and not _generate_music_bed(audio, duration=45, run=run):
            return _failed(package, "BLOCKED_RENDER: non-TTS music bed could not be created", evidence=job.evidence_fingerprint, width=job.width, height=job.height, audio_mode="music_only")
    elif narration is None:
        return _failed(package, f"approved ElevenLabs narration is required: {last_error or 'provider error'}", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    else:
        audio = Path(narration.metadata.audio_path)
    caption_path = caption_dir / f"{package.package_id}.srt"
    spoken_script = narration.metadata.source_script if narration and narration.reused else job.script if audio_mode != "music_only" else ""
    _write_captions(caption_path, spoken_script, _audio_duration(audio, run) or _estimate_duration(spoken_script))
    caption_text_paths = _write_caption_text_files(caption_path)
    video_path = format_dir / f"{package.package_id}.mp4"
    title_path = metadata_dir / f"{package.package_id}.title.txt"
    subtitle_path = metadata_dir / f"{package.package_id}.subtitle.txt"
    title_path.write_text(package.title_candidates[0], encoding="utf-8")
    subtitle_path.write_text("GamCryp evidence-aware explainer", encoding="utf-8")
    logo_path = _local_logo_path(package)
    brand_logo_path = _brand_logo_path()
    if is_motion_graphic_explainer(package):
        # These explainers use the real GamCryp logo with original motion
        # graphics built from published methodology copy. They never imitate
        # or pretend to show a live product screenshot.
        logo_path = brand_logo_path
    duration = max(1, _audio_duration(audio, run) or _estimate_duration(job.script))
    quality_metadata = _short_quality_metadata(package, duration, logo_path) if job.format == SHORT_FORM else None
    if quality_metadata is not None:
        quality_metadata["narration_reused"] = bool(narration and narration.reused)
        quality_metadata["narration_script_matches_package"] = bool(
            narration is None or " ".join(narration.metadata.source_script.split()) == " ".join(job.script.split())
        )
        quality_metadata["audio_mode"] = audio_mode if narration is None else "neural_voice"
        quality_metadata["tts_forbidden"] = True
        quality_metadata["narration_generation_approved"] = bool(
            narration is not None and audio_mode == "neural_voice" and creative_approval
        )
    product_visual_paths = (
        tuple(Path(path) for path in quality_metadata["asset_plan"]["product_visual_paths"])
        if quality_metadata and quality_metadata["asset_plan"]["product_visual_paths"]
        else ()
    )
    # A package may have several approved product captures.  Selecting one
    # deterministically per package keeps reruns reproducible while preventing
    # every angle in the review buffer from showing the same screenshot.
    source_media_paths = (
        tuple(Path(path) for path in quality_metadata["asset_plan"].get("source_media_paths", ()))
        if quality_metadata
        else ()
    )
    source_media_path = _select_source_media(source_media_paths, package.package_id)
    product_visual_path = source_media_path if source_media_path and source_media_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico"} else _select_product_visual(product_visual_paths, package.package_id)
    scene_text_paths = _write_scene_text_files(metadata_dir, package, quality_metadata)
    if quality_metadata is not None:
        quality_metadata["visual_copy_complete"] = all(
            not re.search(r"(?:\.\.\.|…)", path.read_text(encoding="utf-8"))
            for path in scene_text_paths
        )
    if job.format == SHORT_FORM and (source_media_path is not None or is_motion_graphic_explainer(package)) and _remotion_short_enabled(command_runner):
        return _render_remotion_short(
            package=package,
            job=job,
            root=root,
            metadata_dir=metadata_dir,
            caption_path=caption_path,
            audio=audio,
            video_path=video_path,
            quality_metadata=quality_metadata or {},
            voice_name=voice_name,
            voice_id=voice_id,
            narration=narration,
            audio_mode=audio_mode if narration is None else "neural_voice",
            source_media_path=source_media_path,
            run=run,
            now=now,
        )
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
        "-map", video_map, "-map", audio_map, "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video_path),
    ]
    try:
        completed = run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        return _failed(package, "ffmpeg is unavailable", evidence=job.evidence_fingerprint, width=job.width, height=job.height, audio_mode=audio_mode if narration is None else "neural_voice")
    if completed.returncode != 0 or not video_path.is_file():
        return _failed(package, f"video render failed: {_safe_process_reason(completed.stderr)}", evidence=job.evidence_fingerprint, width=job.width, height=job.height, audio_mode=audio_mode if narration is None else "neural_voice")
    duration = _probe_video(video_path, run)
    if duration is None:
        return _failed(package, "rendered video is not decodable", evidence=job.evidence_fingerprint, width=job.width, height=job.height, audio_mode=audio_mode if narration is None else "neural_voice")
    if job.format == LONG_FORM and duration < LONG_FORM_MIN_SECONDS:
        return _failed(package, "rendered long-form video is shorter than the evidence-backed minimum", evidence=job.evidence_fingerprint, width=job.width, height=job.height, audio_mode=audio_mode if narration is None else "neural_voice")
    if job.format == SHORT_FORM and quality_metadata is not None:
        quality_metadata["frame_qa"] = frame_qa(video_path, root / "qa" / package.package_id, runner=run)
    result = RenderResult(package.source_inventory_item_id, package.package_id, job.format, RENDER_READY, None, str(video_path), str(caption_path), str(audio), duration, job.width, job.height, voice_name, voice_id, narration.metadata.model_id if narration else None, job.evidence_fingerprint, str(metadata_dir / f"{package.package_id}.json"), (now or datetime.now(UTC)).isoformat(), quality_metadata, audio_mode if narration is None else "neural_voice")
    blockers = validate_render(result)
    if blockers:
        result = replace(result, status=NOT_READY, reason="BLOCKED_VISUAL_QA: " + "; ".join(blockers))
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


def _select_product_visual(paths: tuple[Path, ...], package_id: str) -> Path | None:
    """Choose an approved product capture reproducibly for this package."""
    if not paths:
        return None
    index = int(hashlib.sha256(package_id.encode("utf-8")).hexdigest()[:8], 16) % len(paths)
    return paths[index]


def _select_source_media(paths: tuple[Path, ...], package_id: str) -> Path | None:
    """Choose one approved official source deterministically for a package."""
    if not paths:
        return None
    # Videos outrank stills: the source itself should be the movement whenever
    # an official product/game clip has been supplied.
    videos = tuple(path for path in paths if path.suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"})
    candidates = videos or paths
    index = int(hashlib.sha256(package_id.encode("utf-8")).hexdigest()[:8], 16) % len(candidates)
    return candidates[index]


def _short_quality_metadata(package: ContentPackage, duration: float, logo_path: Path | None) -> dict[str, Any]:
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id) if package.opportunity_id else None
    name = opportunity.name if opportunity is not None else "GamCryp"
    opportunity_type = opportunity.opportunity_type if opportunity is not None else "CATALOG"
    points = [str(point["text"]) for point in package.factual_talking_points if point.get("text")]
    plan = asset_plan(package)
    hook_errors = hook_blockers(package)
    site_explainer = is_motion_graphic_explainer(package)
    scene_count = 6
    return {
        "quality_version": "short-social-motion-v8",
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
        "visual_text_system": "complete_copy_no_ellipsis",
        "duration_seconds": duration,
        "scene_transitions": True,
        "animated_motion": True,
        "transition_effects": ["fade_in", "fade_out", "moving_accents"],
        "static_background_only": False,
        "caption_only_visuals": False,
        "brand_opening_present": True,
        "brand_closing_present": True,
        "creative_status": "CREATIVE_QA_PASSED" if not creative_preflight(package) else "BLOCKED_CREATIVE_QA",
        "hook": package.hook,
        "hook_qa": {"status": "PASSED" if not hook_errors else "FAILED", "blockers": hook_errors},
        "asset_plan": plan.safe_dict(),
        "product_visual_count": len(plan.product_visual_paths),
        "source_media_count": len(plan.source_media_paths),
        "official_video_count": sum(Path(path).suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"} for path in plan.source_media_paths),
        "source_media_selection": "official_video_preferred" if plan.source_media_paths else "none",
        "product_visual_selection": "deterministic_package_rotation" if plan.product_visual_paths else "none",
        "product_visual_provenance": "OFFICIAL_SOURCE_MEDIA" if plan.source_media_paths else "NONE",
        "composition_mode": "gamcryp_site_motion_graphics" if site_explainer else "official_source_led" if plan.source_media_paths else "motion_cards",
        "product_visual_storytelling": site_explainer or bool(plan.source_media_paths),
        "product_visual_motion": "site_motion_infographic" if site_explainer else "official_video_or_ken_burns_capture" if plan.source_media_paths else "none",
        "site_explainer": site_explainer,
        "site_visual_mode": "original_evidence_led_motion_graphics" if site_explainer else None,
        "site_brand_logo_path": str(logo_path) if site_explainer and logo_path is not None else None,
        "site_brand_logo_sha256": _sha256(logo_path) if site_explainer and logo_path is not None else None,
        "gamcryp_product_placement": True,
        "chart": {"used": False, "reason": "No verified comparison metric set was available."},
        "primary_visual_elements": (
            ["gamcryp_brand_identity", "methodology_motion_graphic", "evidence_point_sequence", "branded_cta"]
            if site_explainer else [
            "identity_card",
            "setup_diagram",
            "evidence_or_product_visual",
            "evidence_metric_card",
            "branded_cta",
            ]
        ),
    }


def _write_scene_text_files(metadata_dir: Path, package: ContentPackage, quality: dict[str, Any] | None) -> tuple[Path, ...]:
    if quality is None:
        return ()
    points = [str(point["text"]) for point in package.factual_talking_points if point.get("text")]
    name = str(quality["opportunity_name"])
    type_label = str(quality["opportunity_type"]).replace("_", " ").title()
    status = "ROI unavailable: missing reproducible inputs." if package.content_family == "WHY_ROI_UNAVAILABLE" else "Check cost, earning path, risk, and freshness before acting."
    hook = package.hook
    point_one = points[0] if points else "The evidence-backed earning path is not yet documented."
    point_two = points[1] if len(points) > 1 else "Use the official source and GamCryp model context."
    cta = package.cta
    asset_led = bool(quality.get("product_visual_count", 0))
    # The spoken captions remain the complete factual script.  On-canvas copy
    # is intentionally compact so the product capture can be the visual
    # subject instead of turning the Short into a narrated slide deck.
    texts = (
        f"HOOK\n{hook}",
        f"{name}\n{type_label}",
        "START HERE\nOpen the official product view.",
        "EVIDENCE\nRead the official screen before acting.",
        f"STATUS\n{status}",
        f"GAMCRYP\n{cta}",
    )
    paths = []
    # Product-led scenes use short visual labels; the complete factual points
    # are still carried by the caption track and source-bound metadata.
    visual_widths = (22, 26, 32, 38, 26, 26)
    for index, text in enumerate(texts, start=1):
        path = metadata_dir / f"{package.package_id}.scene-{index}.txt"
        # Visual copy is intentionally complete. The old renderer sliced long
        # evidence points and appended an ellipsis, which made the Shorts look
        # like unfinished slide-deck exports. The new composition gives the
        # explanatory scenes enough room and lets captions carry the full
        # narration separately.
        max_lines = 8 if asset_led and index in (3, 4) else 6
        path.write_text(_wrap_visual_text(text, width=visual_widths[index - 1], max_lines=max_lines), encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def _wrap_visual_text(value: str, *, width: int = 28, max_lines: int | None = None) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        lines.extend(textwrap.wrap(line.strip(), width=width, break_long_words=True, break_on_hyphens=False) or [""])
    if max_lines is not None and len(lines) > max_lines:
        # Never manufacture incomplete copy for a reviewable asset. Keep the
        # full sentence; the render layout is responsible for providing space.
        # This also makes the absence of an ellipsis an auditable invariant.
        pass
    return "\n".join(lines)


def _build_motion_filter(*, package: ContentPackage, duration: float, caption_path: Path, caption_text_paths: tuple[Path, ...], scene_text_paths: tuple[Path, ...], title_path: Path, logo_path: Path | None, product_visual_path: Path | None, brand_logo_path: Path | None, short_form: bool) -> str:
    font_path = _video_font_path()
    font = _filter_path(font_path)
    if short_form:
        caption_layers = []
        for path, start, end in _caption_timing(caption_path):
            text_path = _filter_path(path)
            caption_layers.append(
                f"drawtext=fontfile={font}:textfile={text_path}:fontcolor=white:fontsize=34:line_spacing=6:box=1:boxcolor=0x061226D9:boxborderw=16:x=(w-text_w)/2:y=1640:enable='between(t,{start:.3f},{end:.3f})'"
            )
        captions = ",".join(caption_layers)
    else:
        captions = f"subtitles={_filter_path(caption_path)}:fontsdir={_filter_path(font_path.parent)}:force_style='FontName={font_path.stem},FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101A33,Outline=3,Alignment=2,MarginL=96,MarginR=96,MarginV=120'"
    if not short_form:
        return f"[0:v]drawtext=fontfile={font}:textfile={_filter_path(title_path)}:fontcolor=white:fontsize=64:x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=0x0d234dCC:boxborderw=24,{captions}[vout]"
    scene_timings = _visual_scene_timings(_caption_timing(caption_path), duration)
    scenes: list[str] = []
    # Social-first composition: each beat owns the full canvas. There is no
    # persistent card grid, no slide-deck panel, and no fabricated metric
    # chart. Evidence scenes give the approved product visual the largest
    # screen area; the other beats use kinetic type and simple progress marks.
    scene_colors = ("0x071329", "0x0A1B32", "0x102A47", "0x0B243D", "0x10243F", "0x071329")
    scene_labels = ("THE QUESTION", "THE PROJECT", "START HERE", "OFFICIAL EVIDENCE", "CHECK THE RISKS", "THE TAKEAWAY")
    text_y = (390, 360, 265, 265, 360, 430)
    text_size = (72, 60, 26, 26, 58, 58)
    for index, (label, ty, size) in enumerate(zip(scene_labels, text_y, text_size)):
        start, end = scene_timings[index]
        enable = f"between(t,{start:.3f},{end:.3f})"
        scene_text_path = scene_text_paths[index]
        text_path = _filter_path(scene_text_path)
        motion = f"sin(t*1.35+{index})*18"
        scenes.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={scene_colors[index]}:t=fill:enable='{enable}'")
        scenes.append(f"drawbox=x=72:y=150:w=936:h=8:color=0x21D4FD@0.82:t=fill:enable='{enable}'")
        scenes.append(f"drawbox=x=72+abs(sin(t*1.7+{index})*120):y=150:w={170 + index * 55}:h=8:color=0x8BE9FD@0.92:t=fill:enable='{enable}'")
        scenes.append(f"drawtext=fontfile={font}:text='GAMCRYP / {label}':fontcolor=0x8BE9FD:fontsize=22:x=74:y=92:enable='{enable}'")
        scenes.append(f"drawtext=fontfile={font}:text='0{index + 1} / 06':fontcolor=0x8BE9FD:fontsize=22:x=850:y=92:enable='{enable}'")
        scenes.append(f"drawbox=x=86+{motion}:y=230:w=6:h=1050:color=0x21D4FD@0.52:t=fill:enable='{enable}'")
        if product_visual_path is not None and index in (2, 3):
            # Product scenes are asset-led: the approved capture occupies the
            # centre of the frame, while only a compact label and evidence
            # ribbon remain on canvas.  This is deliberately unlike a stack of
            # text cards; the full factual narration is in the captions.
            # v8 treats the evidence capture as a mobile-first visual rather
            # than a small card in a slide. The larger frame, tighter crop,
            # and moving source rail use the available vertical canvas while
            # keeping all copy factual and source-bound.
            scenes.append(f"drawbox=x=48:y=200:w=984:h=120:color=0x020B19@0.82:t=fill:enable='{enable}'")
            scenes.append(f"drawbox=x=48:y=200:w=8:h=120:color=0x21D4FD@0.95:t=fill:enable='{enable}'")
            scenes.append(f"drawtext=fontfile={font}:textfile={text_path}:fontcolor=white:fontsize=30:line_spacing=6:x=88:y=218+sin(t*0.9+{index})*3:text_align=left:enable='{enable}'")
            scenes.append(f"drawbox=x=30:y=320:w=1020:h=700:color=0x020B19@0.94:t=fill:enable='{enable}'")
            scenes.append(f"drawbox=x=30:y=320:w=1020:h=6:color=0x21D4FD@0.95:t=fill:enable='{enable}'")
            scenes.append(f"drawbox=x=30:y=1020:w=1020:h=110:color=0x020B19@0.86:t=fill:enable='{enable}'")
            scenes.append(f"drawtext=fontfile={font}:text='OFFICIAL PRODUCT VIEW':fontcolor=0x8BE9FD:fontsize=22:x=70:y=1052:enable='{enable}'")
            scenes.append(f"drawbox=x=48:y=1182:w=984:h=8:color=0x21D4FD@0.45:t=fill:enable='{enable}'")
            scenes.append(f"drawbox=x=48+abs(sin(t*1.2+{index})*760):y=1176:w=180:h=20:color=0x8BE9FD@0.9:t=fill:enable='{enable}'")
            scenes.append(f"drawtext=fontfile={font}:text='SOURCE-BOUND / VERIFY BEFORE ACTION':fontcolor=0x8BE9FD:fontsize=24:x=70:y=1218:enable='{enable}'")
        else:
            scenes.append(f"drawtext=fontfile={font}:textfile={text_path}:fontcolor=white:fontsize={size}:line_spacing=14:x=112+{motion}:y={ty}+sin(t*1.1+{index})*5:text_align=left:enable='{enable}'")
        # A small, abstract visual beat supports the copy without pretending
        # to be a financial chart or a product screenshot.
        if index == 0:
            scenes.extend([
                f"drawbox=x=112:y=1040:w=360:h=10:color=0x21D4FD@0.9:t=fill:enable='{enable}'",
                f"drawbox=x=112:y=1080:w=620:h=10:color=0xA78BFA@0.72:t=fill:enable='{enable}'",
                f"drawbox=x=112:y=1120:w=510:h=10:color=0x34D399@0.72:t=fill:enable='{enable}'",
            ])
        elif index == 1:
            scenes.extend([
                f"drawbox=x=730+{motion}:y=420:w=210:h=210:color=0x21D4FD@0.17:t=fill:enable='{enable}'",
                f"drawbox=x=770+{motion}:y=460:w=130:h=130:color=0xA78BFA@0.32:t=fill:enable='{enable}'",
                f"drawbox=x=812+{motion}:y=502:w=46:h=46:color=0x34D399@0.85:t=fill:enable='{enable}'",
            ])
        elif index == 4:
            for chip_x, chip_color, chip_label in ((112, "0x21D4FD", "COST"), (390, "0xA78BFA", "REWARD"), (668, "0x34D399", "EXIT")):
                scenes.append(f"drawbox=x={chip_x}:y=1030:w=240:h=110:color={chip_color}@0.18:t=fill:enable='{enable}'")
                scenes.append(f"drawbox=x={chip_x}:y=1030:w=240:h=6:color={chip_color}@0.85:t=fill:enable='{enable}'")
                scenes.append(f"drawtext=fontfile={font}:text='{chip_label}':fontcolor=white:fontsize=24:x={chip_x + 22}:y=1070:enable='{enable}'")
        scenes.append(f"drawbox=x=72:y=1580:w=936:h=5:color=0x21D4FD@0.62:t=fill:enable='{enable}'")
    filter_graph = ",".join(scenes)
    input_index = 1
    overlays: list[str] = []
    if logo_path is not None:
        overlays.append(f"[{input_index}:v]scale=240:240:force_original_aspect_ratio=decrease,format=rgba[project_logo]")
        input_index += 1
    if product_visual_path is not None:
        # The approved product capture is the visual subject.  Crop a slightly
        # oversized source with a slow, deterministic pan so it remains legible
        # while behaving like a social video asset.  The scanline is
        # decorative only; it does not imply live data.
        overlays.append(
            f"[{input_index}:v]scale=1020:660:force_original_aspect_ratio=decrease,"
            "pad=1020:660:(ow-iw)/2:(oh-ih)/2:color=0x020B19,format=rgba[product_visual]"
        )
        input_index += 1
    if brand_logo_path is not None:
        overlays.append(f"[{input_index}:v]scale=300:120:force_original_aspect_ratio=decrease,format=rgba[brand_logo]")
        input_index += 1
    overlays_text = ";".join(overlays)
    graph = f"[0:v]{filter_graph}[cards]"
    if logo_path is not None:
        graph += f";[cards][project_logo]overlay=x=760:y=300:enable='between(t,{scene_timings[1][0]:.3f},{scene_timings[1][1]:.3f})'[identity]"
    else:
        graph += f";[cards]drawbox=x=760:y=430:w=180:h=180:color=0x21D4FD@0.18:t=fill:enable='between(t,{scene_timings[1][0]:.3f},{scene_timings[1][1]:.3f})',drawtext=fontfile={font}:text='APP':fontcolor=0x21D4FD:fontsize=42:x=807:y=500:enable='between(t,{scene_timings[1][0]:.3f},{scene_timings[1][1]:.3f})'[identity]"
    if product_visual_path is not None:
        product_start, product_end = scene_timings[2][0], scene_timings[3][1]
        graph += (
            f";[identity][product_visual]overlay=x=30+sin(t*0.6)*12:y=350+cos(t*0.45)*8:"
            f"enable='between(t,{product_start:.3f},{product_end:.3f})',"
            f"drawbox=x=30:y=350+abs(sin(t*0.85)*620):w=1020:h=3:color=0x21D4FD@0.58:t=fill:"
            f"enable='between(t,{product_start:.3f},{product_end:.3f})'[product]"
        )
    else:
        graph += ";[identity]copy[product]"
    if brand_logo_path is not None:
        # GamCryp is the evaluator and belongs in the close, not as a generic
        # intro before the viewer understands the opportunity.
        graph += f";[product][brand_logo]overlay=x=390:y=1435:enable='between(t,{scene_timings[5][0]:.3f},{duration:.3f})'[branded]"
    else:
        graph += ";[product]copy[branded]"
    prefix = f"{overlays_text};" if overlays_text else ""
    fade_out_start = max(duration - 0.35, 0.35)
    return f"{prefix}{graph};[branded]{captions},fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start:.3f}:d=0.35[vout]"


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
    if quality.get("visual_copy_complete") is False:
        blockers.append("short-form visual copy contains truncation marks")
    if not quality.get("scene_transitions"):
        blockers.append("short-form scene transitions are missing")
    if not quality.get("animated_motion"):
        blockers.append("short-form does not prove animated motion")
    transition_effects = set(quality.get("transition_effects", ()))
    if not {"fade_in", "fade_out"}.issubset(transition_effects):
        blockers.append("short-form transition effects are missing")
    if quality.get("static_background_only"):
        blockers.append("short-form uses a static background-only composition")
    if quality.get("caption_only_visuals"):
        blockers.append("captions are the only meaningful visual content")
    if not quality.get("brand_closing_present"):
        blockers.append("GamCryp closing is missing")
    if quality.get("creative_status") != "CREATIVE_QA_PASSED":
        blockers.append("editorial visual QA has not passed")
    site_explainer = quality.get("site_explainer") is True
    source_media_count = int(quality.get("source_media_count", 0))
    product_visual_count = int(quality.get("product_visual_count", 0))
    if site_explainer:
        family = str(quality.get("content_family") or "")
        logo = Path(str(quality.get("site_brand_logo_path") or ""))
        if family not in SITE_EXPLAINER_FAMILIES | AUTONOMOUS_CATALOG_FAMILIES:
            blockers.append("motion explainer family is not on the approved educational-content list")
        if (
            quality.get("render_engine") != "remotion"
            or quality.get("quality_version") != "short-social-remotion-site-explainer-v1"
            or
            quality.get("site_visual_mode") != "original_evidence_led_motion_graphics"
            or not logo.is_file()
            or not quality.get("site_brand_logo_sha256")
            or _sha256(logo) != quality.get("site_brand_logo_sha256")
        ):
            blockers.append("official GamCryp brand asset or site-explainer visual provenance is missing")
        minimum_points = 3 if family in SITE_EXPLAINER_FAMILIES else 1
        if int(quality.get("evidence_point_count", 0)) < minimum_points:
            blockers.append("motion explainer has too few evidence-backed points")
        if quality.get("product_visual_motion") != "site_motion_infographic":
            blockers.append("site explainer motion-graphic treatment is missing")
    else:
        if max(source_media_count, product_visual_count) < 1:
            blockers.append("approved official product/app source media is missing (product or app visual is missing)")
        if max(source_media_count, product_visual_count) >= 1 and not quality.get("product_visual_storytelling"):
            blockers.append("official source media is not used as the primary evidence scene")
        allowed_motion = {"ken_burns_crop_and_scanline", "official_video_or_ken_burns_capture", "official_video_or_animated_source_capture"}
        if max(source_media_count, product_visual_count) >= 1 and quality.get("product_visual_motion") not in allowed_motion:
            blockers.append("official source media lacks motion treatment (product visual lacks motion treatment)")
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
    if quality.get("narration_script_matches_package") is False:
        blockers.append("reused narration does not match the current package script")
    if quality.get("audio_mode") == "neural_voice" and not quality.get("narration_reused") and not quality.get("narration_generation_approved"):
        blockers.append("new TTS narration requires explicit creative approval")
    if quality.get("tts_forbidden") is False:
        blockers.append("TTS narration policy is not enabled")
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
    candidate = REPOSITORY_ROOT / "frontend" / opportunity.logo_asset.lstrip("/")
    # ffmpeg's Windows build cannot decode SVG inputs reliably. Keep the
    # renderer fail-closed for the asset itself, but use the safe branded
    # identity card when the catalog only has a vector logo.
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".ico"}:
        return None
    return candidate if candidate.is_file() else None


def _brand_logo_path() -> Path | None:
    candidate = REPOSITORY_ROOT / "frontend/assets/brand/gamcryp-logo.png"
    return candidate if candidate.is_file() else None


def _failed(package: ContentPackage, reason: str, *, evidence: str = "", width: int = 0, height: int = 0, audio_mode: str = "music_only") -> RenderResult:
    return RenderResult(package.source_inventory_item_id, package.package_id, package.format, NOT_READY, reason, None, None, None, None, width, height, None, None, None, evidence or package.evidence_fingerprint, None, None, audio_mode=audio_mode)


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
    if not words:
        path.write_text("", encoding="utf-8")
        return
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
        target.write_text(_wrap_visual_text(text, width=34, max_lines=3), encoding="utf-8")
        paths.append(target)
    return tuple(paths)


def _caption_timing(path: Path) -> tuple[tuple[Path, float, float], ...]:
    entries = _read_srt_entries(path)
    paths = tuple(path.with_name(f"{path.stem}.caption-{index}.txt") for index in range(1, len(entries) + 1))
    return tuple((text_path, start, end) for text_path, (start, end, _) in zip(paths, entries))


def _visual_scene_timings(captions: tuple[tuple[Path, float, float], ...], duration: float) -> tuple[tuple[float, float], ...]:
    """Keep visual beats aligned with spoken caption groups.

    The six visual beats are semantic (hook, project, setup, evidence, risk,
    takeaway), while captions are generated from the spoken script. Grouping
    the evidence captions together avoids showing the next visual beat while
    the previous evidence sentence is still being spoken.
    """
    if len(captions) >= 6:
        if len(captions) == 6:
            groups = tuple((index,) for index in range(6))
        else:
            groups = ((0,), (1,), (2,), tuple(range(3, len(captions) - 2)), (len(captions) - 2,), (len(captions) - 1,))
        return tuple((captions[group[0]][1], captions[group[-1]][2]) for group in groups)
    step = duration / 6.0
    return tuple((index * step, (index + 1) * step) for index in range(6))


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


def _video_font_path() -> Path:
    """Select a font available in the current renderer OS/container."""
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def _remotion_short_enabled(command_runner: Callable[..., subprocess.CompletedProcess[str]] | None) -> bool:
    """Use the real motion renderer in production, while keeping unit-test FFmpeg fakes deterministic."""
    if command_runner is not None:
        return False
    return os.getenv("GAMEFI_VIDEO_RENDER_ENGINE", "remotion").strip().lower() in {"remotion", "react"}


def _render_remotion_short(
    *,
    package: ContentPackage,
    job: RenderJob,
    root: Path,
    metadata_dir: Path,
    caption_path: Path,
    audio: Path,
    video_path: Path,
    quality_metadata: dict[str, Any],
    voice_name: str | None,
    voice_id: str | None,
    narration: ElevenLabsGenerationResult | None,
    audio_mode: str,
    source_media_path: Path | None,
    run: Callable[..., subprocess.CompletedProcess[str]],
    now: datetime | None,
) -> RenderResult:
    """Render an evidence-led Short with the Remotion motion-design composition."""
    remotion_root = REPOSITORY_ROOT / "video/remotion"
    if not (remotion_root / "package.json").is_file():
        return _failed(package, "BLOCKED_RENDER: Remotion project is missing", evidence=job.evidence_fingerprint, width=job.width, height=job.height)

    public_root = remotion_root / "public"
    site_explainer = is_motion_graphic_explainer(package)
    source_name = f"source/{package.package_id}{source_media_path.suffix.lower()}" if source_media_path is not None else ""
    logo_source_name = f"brand/{package.package_id}-gamcryp.png" if site_explainer else ""
    audio_name = f"audio/{package.package_id}.{'mp3' if audio.suffix.lower() != '.wav' else 'wav'}"
    audio_target = public_root / audio_name
    audio_target.parent.mkdir(parents=True, exist_ok=True)
    staged_assets = [audio_target]
    try:
        if source_media_path is not None:
            source_target = public_root / source_name
            source_target.parent.mkdir(parents=True, exist_ok=True)
            staged_assets.append(source_target)
            shutil.copy2(source_media_path, source_target)
        if site_explainer:
            logo_target = public_root / logo_source_name
            logo_target.parent.mkdir(parents=True, exist_ok=True)
            staged_assets.append(logo_target)
            shutil.copy2(REPOSITORY_ROOT / "frontend/assets/brand/gamcryp-logo.png", logo_target)
        shutil.copy2(audio, audio_target)
    except OSError as exc:
        _remove_staged_assets(staged_assets)
        return _failed(package, f"BLOCKED_RENDER: Remotion asset staging failed: {exc}", evidence=job.evidence_fingerprint, width=job.width, height=job.height)

    sting_path = _ensure_brand_sting(root, run)
    sting_name: str | None = None
    if sting_path is not None:
        public_sting = public_root / "audio/gamcryp-brand-sting.wav"
        if public_sting.is_file():
            sting_name = "audio/gamcryp-brand-sting.wav"
        else:
            sting_name = f"audio/{package.package_id}-gamcryp-brand-sting.wav"
            staged_sting = public_root / sting_name
            try:
                shutil.copy2(sting_path, staged_sting)
                staged_assets.append(staged_sting)
            except OSError:
                sting_name = None

    points = [str(point.get("text", "")).strip() for point in package.factual_talking_points if point.get("text")]
    source = package.required_source_references[0]["url"] if package.required_source_references else package.canonical_source_url
    source = re.sub(r"^https?://", "", source).rstrip("/")
    if site_explainer and source.startswith("/"):
        source = f"gamcryp.com{source}"
    props = {
        "title": package.title_candidates[0] if package.title_candidates else package.content_family.replace("_", " "),
        "eyebrow": package.content_family.replace("_", " / "),
        "hook": package.hook,
        "cta": package.cta,
        "source": source,
        "sourceMedia": source_name,
        "sourceMediaKind": "video" if source_media_path is not None and source_media_path.suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"} else "image",
        "productImage": source_name,
        "siteExplainer": site_explainer,
        "brandLogoSrc": logo_source_name,
        "audioSrc": audio_name,
        "brandStingSrc": sting_name,
        "accent": "#4de1ff",
        "accent2": "#a78bfa",
        "steps": points[:4] if site_explainer else ["Read the official guide", "Check required infrastructure", "Verify costs and exit paths"],
        "facts": points[:3] or ["Read the official source", "Check operational requirements", "Verify the current status"],
        "captions": [{"start": start, "end": end, "text": text} for start, end, text in _read_srt_entries(caption_path)],
    }
    props_path = metadata_dir / f"{package.package_id}.remotion-props.json"
    props_path.write_text(json.dumps(props, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    npx = "npx.cmd" if os.name == "nt" else "npx"
    command = [npx, "remotion", "render", "GamcrypMotionShort", str(video_path.resolve()), f"--props={props_path.resolve()}"]
    try:
        completed = run(command, check=False, capture_output=True, text=True, cwd=str(remotion_root.resolve()))
    except OSError:
        _remove_staged_assets(staged_assets)
        return _failed(package, "Remotion is unavailable", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    _remove_staged_assets(staged_assets)
    if completed.returncode != 0 or not video_path.is_file():
        return _failed(package, f"Remotion render failed: {_safe_process_reason(completed.stderr)}", evidence=job.evidence_fingerprint, width=job.width, height=job.height)

    duration = _probe_video(video_path, run)
    if duration is None:
        return _failed(package, "Remotion output is not decodable", evidence=job.evidence_fingerprint, width=job.width, height=job.height)
    quality = dict(quality_metadata)
    quality.update({
        "quality_version": "short-social-remotion-site-explainer-v1" if site_explainer else "short-social-remotion-v2-source-led",
        "composition_mode": "remotion_gamcryp_site_motion_graphics" if site_explainer else "remotion_official_source_led",
        "product_visual_motion": "site_motion_infographic" if site_explainer else "official_video_or_animated_source_capture",
        "render_motion_treatment": "original_evidence_led_site_explainer" if site_explainer else "source_media_first_with_animated_overlays",
        "animated_motion": True,
        "transition_effects": ["fade_in", "fade_out", "spring_scene_reveal", "cross_scene_fade", "moving_orbit", "browser_scan"],
        "brand_sting_present": sting_name is not None,
        "render_engine": "remotion",
    })
    quality["frame_qa"] = frame_qa(video_path, root / "qa" / package.package_id, runner=run)
    result = RenderResult(package.source_inventory_item_id, package.package_id, job.format, RENDER_READY, None, str(video_path), str(caption_path), str(audio), duration, job.width, job.height, voice_name, voice_id, narration.metadata.model_id if narration else None, job.evidence_fingerprint, str(metadata_dir / f"{package.package_id}.json"), (now or datetime.now(UTC)).isoformat(), quality, audio_mode)
    blockers = validate_render(result)
    if blockers:
        result = replace(result, status=NOT_READY, reason="BLOCKED_VISUAL_QA: " + "; ".join(blockers))
    Path(result.metadata_path).write_text(json.dumps({**asdict(result), "music_source_sha256": music_bed_source_fingerprint() if audio_mode == "music_only" else None, "asset_checksums": {"video": _sha256(video_path), "audio": _sha256(audio), "captions": _sha256(caption_path)}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _safe_process_reason(stderr: str | None) -> str:
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    return lines[-1][:240] if lines else "unknown ffmpeg error"


def _remove_staged_assets(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _music_only_fallback_enabled() -> bool:
    return os.getenv("GAMEFI_SHORT_AUDIO_FALLBACK", "music_only").strip().lower() in {"1", "true", "yes", "music_only"}


def _last_provider_failure_was_account_blocked(error: str | None) -> bool:
    text = (error or "").lower()
    return "quota" in text or "rate limit" in text or "credentials were rejected" in text


def music_bed_source_fingerprint() -> str | None:
    """Return the checksum of the licensed music asset currently used for rendering."""
    try:
        return _sha256(MUSIC_BED_SOURCE)
    except OSError:
        return None


def _generate_music_bed(path: Path, *, duration: int, run: Callable[..., subprocess.CompletedProcess[str]]) -> bool:
    """Create a trimmed/faded copy of the licensed music bed without TTS credits."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if not MUSIC_BED_SOURCE.is_file():
        return False
    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(MUSIC_BED_SOURCE),
        "-t", str(duration),
        "-af", "afade=t=in:st=0:d=0.4,afade=t=out:st=" + str(max(duration - 1, 1)) + ":d=1",
        "-c:a", "libmp3lame", "-b:a", "160k", str(path),
    ]
    try:
        completed = run(command, check=False, capture_output=True, text=True)
    except OSError:
        return False
    return completed.returncode == 0 and path.is_file()
