"""Creative-director checks for publishable Shorts.

Technical decoding is intentionally kept separate from this module. A valid
MP4 is not enough: the package needs a real opportunity asset, a spoken hook,
an evidence-led visual plan, and a GamCryp evaluation close.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from app.content_package.generator import ContentPackage

BLOCKED_MISSING_ASSETS = "BLOCKED_MISSING_ASSETS"
BLOCKED_WEAK_HOOK = "BLOCKED_WEAK_HOOK"
BLOCKED_VISUAL_QA = "BLOCKED_VISUAL_QA"
BLOCKED_SCRIPT_QA = "BLOCKED_SCRIPT_QA"
ASSETS_REQUIRED = "ASSETS_REQUIRED"
ASSETS_READY = "ASSETS_READY"

GENERIC_HOOK_PREFIXES = (
    "start with the evidence",
    "today we look at",
    "this is a decentralized",
    "gamcryp analyzed",
    "welcome to gamcryp",
)


@dataclass(frozen=True)
class AssetPlan:
    status: str
    required_kinds: tuple[str, ...]
    logo_path: str | None
    product_visual_paths: tuple[str, ...]
    source_media_paths: tuple[str, ...] = ()
    source_card_required: bool = True

    def safe_dict(self) -> dict[str, Any]:
        return asdict(self)


def asset_plan(package: ContentPackage) -> AssetPlan:
    """Find approved local source media; never invent a screenshot or gameplay clip.

    Source media is intentionally broader than the historical ``product_visual``
    field.  A real official MP4/WebM/MOV is the strongest input, followed by an
    official product/game/site capture.  The renderer decides how to animate the
    source, but it must never replace the source with a fabricated UI.
    """
    opportunity_id = package.opportunity_id or "gamcryp"
    logo = _find_logo(package)
    root = Path(os.getenv("GAMEFI_SHORT_ASSET_ROOT", "data/local/video_assets")) / opportunity_id
    required = ("gameplay_or_ui",) if _is_game(package) else ("product_ui_or_device",)
    source_media = tuple(str(path) for path in sorted(root.glob("*")) if path.is_file() and _is_source_media(path))
    product = tuple(path for path in source_media if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico"})
    status = ASSETS_READY if source_media else ASSETS_REQUIRED
    return AssetPlan(status, required, str(logo) if logo else None, product, source_media)


def creative_preflight(package: ContentPackage) -> tuple[str, ...]:
    blockers: list[str] = []
    blockers.extend(hook_blockers(package))
    if not package.cta or "gamcryp" not in package.cta.lower():
        blockers.append(f"{BLOCKED_SCRIPT_QA}: CTA does not position GamCryp as the evaluator")
    plan = asset_plan(package)
    if plan.status != ASSETS_READY:
        blockers.append(f"{BLOCKED_MISSING_ASSETS}: approved official source media is missing ({', '.join(plan.required_kinds)})")
    return tuple(blockers)


def hook_blockers(package: ContentPackage) -> tuple[str, ...]:
    hook = " ".join(package.hook.strip().split())
    lowered = hook.lower()
    blockers: list[str] = []
    if not hook or len(hook.split()) > 18:
        blockers.append(f"{BLOCKED_WEAK_HOOK}: hook must be short and spoken in the first two seconds")
    if lowered.startswith(GENERIC_HOOK_PREFIXES):
        blockers.append(f"{BLOCKED_WEAK_HOOK}: generic introduction")
    if not any(mark in hook for mark in ("?", "!")) and not any(word in lowered for word in ("check", "catch", "break even", "number")):
        blockers.append(f"{BLOCKED_WEAK_HOOK}: hook has no question, tension, or concrete result")
    return tuple(blockers)


def frame_qa(
    video_path: Path,
    output_dir: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Extract five representative frames and prove they are readable files.

    Semantic review still belongs to a human creative review. This automated
    layer prevents a missing/duplicate frame set from being called reviewed.
    """
    duration = _probe_duration(video_path, runner)
    if duration is None or duration <= 0:
        return {"status": "FAILED", "checkpoints": (), "frames": [], "reason": "video duration probe failed"}
    # A frame at t=0 is commonly still inside the renderer's fade-in and can
    # be completely black. Review frames must represent visible content, not
    # just prove that an MP4 decoder opened.
    first_checkpoint = min(max(duration * 0.04, 0.4), max(duration - 0.5, 0.4))
    checkpoints = (first_checkpoint, *(round(duration * fraction, 3) for fraction in (0.22, 0.47, 0.72, 0.95)))
    output_dir.mkdir(parents=True, exist_ok=True)
    frames: list[str] = []
    for index, checkpoint in enumerate(checkpoints, start=1):
        frame = output_dir / f"frame-{index:02d}.png"
        command = ["ffmpeg", "-y", "-ss", str(checkpoint), "-i", str(video_path), "-frames:v", "1", str(frame)]
        completed = runner(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0 or not frame.is_file() or frame.stat().st_size < 100:
            return {"status": "FAILED", "checkpoints": checkpoints, "frames": frames, "reason": "representative frame extraction failed"}
        frames.append(str(frame))
    unique_sizes = len({Path(path).stat().st_size for path in frames})
    return {
        "status": "PASSED" if len(frames) == len(checkpoints) and unique_sizes >= 3 else "FAILED",
        "checkpoints": checkpoints,
        "frames": frames,
        "unique_frame_sizes": unique_sizes,
    }


def _probe_duration(video_path: Path, runner: Callable[..., subprocess.CompletedProcess[str]]) -> float | None:
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
    completed = runner(command, check=False, capture_output=True, text=True)
    try:
        return float((completed.stdout or "").strip())
    except (TypeError, ValueError):
        return None


def _find_logo(package: ContentPackage) -> Path | None:
    if not package.opportunity_id:
        return None
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id)
    if opportunity is None or not opportunity.logo_asset:
        return None
    candidate = Path("frontend") / opportunity.logo_asset.lstrip("/")
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".ico"}:
        return None
    return candidate if candidate.is_file() else None


def _is_game(package: ContentPackage) -> bool:
    if not package.opportunity_id:
        return False
    from app.strategies.catalog import get_opportunity

    opportunity = get_opportunity(package.opportunity_id)
    return bool(opportunity and opportunity.opportunity_type == "GAME")


def _is_product_visual(path: Path) -> bool:
    # ffmpeg receives these files as looping image inputs.  SVG support varies
    # by build and can fail inside the multi-input filter graph; prefer an
    # approved raster capture when one exists and never let a vector asset
    # enter a publish handoff unnoticed.
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".ico"}:
        return False
    try:
        if path.stat().st_size < 100:
            return False
    except OSError:
        return False
    name = path.stem.lower()
    return any(token in name for token in ("gameplay", "game-ui", "ui", "dashboard", "device", "hardware", "product", "site", "official"))


def _is_source_media(path: Path) -> bool:
    """Admit only local, explicitly named official source media.

    SVG remains excluded from the renderer input because it may be an
    illustration rather than a capture and is not consistently decoded by all
    render paths.  It can remain beside a raster renderer input for provenance.
    """
    if path.suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"}:
        return _has_source_name(path)
    return _is_product_visual(path)


def _has_source_name(path: Path) -> bool:
    try:
        if path.stat().st_size < 100:
            return False
    except OSError:
        return False
    name = path.stem.lower()
    return any(token in name for token in ("official", "gameplay", "product", "capture", "demo", "portal", "dashboard"))
