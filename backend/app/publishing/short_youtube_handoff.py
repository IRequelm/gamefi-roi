"""Short-form render handoff into the existing YouTube publisher.

This queue is deliberately separate from the legacy Content Pack queue. It
contains only evidence-bound, reviewable short renders and never changes X or
long-form state.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from app.config.settings import Settings
from app.content_package.generator import ContentPackage, build_content_packages, validate_package
from app.video_render.factory import APPROVED_VOICES, RENDER_READY, RenderResult, render_package, validate_render
from app.publishing.youtube import YouTubeOperationResult, YouTubePublishManifest, YouTubePublisher

HANDOFF_VERSION = "youtube-short-handoff-v1"
DEFAULT_QUEUE = Path("distribution/publish_queue/youtube_short_handoff.json")
DEFAULT_CAP_STATE = Path("data/local/youtube/autonomous_daily_cap.json")
# A small forward buffer avoids unnecessary ElevenLabs/render credit churn while
# keeping unattended publication supplied for several weeks at one per day.
DEFAULT_BUFFER_TARGET = 14


class ShortHandoffItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    package_id: str
    content_id: str
    format: str = "SHORT_FORM"
    readiness: str = "GREEN"
    status: str = "queued"
    title: str
    description: str
    source_url: str
    tags: tuple[str, ...]
    category_id: str = "28"
    made_for_kids: bool = False
    video_path: str
    caption_path: str
    narration_path: str
    narration_provider: str
    narration_voice_id: str
    narration_model_id: str
    evidence_fingerprint: str
    video_checksum: str
    created_at: str


class ShortHandoffQueue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = HANDOFF_VERSION
    buffer_target: int = DEFAULT_BUFFER_TARGET
    items: tuple[ShortHandoffItem, ...] = ()


@dataclass(frozen=True)
class DailyCap:
    date: str
    successful_publications: int

    @property
    def available(self) -> bool:
        return self.successful_publications < 1


def load_handoff(path: Path = DEFAULT_QUEUE) -> ShortHandoffQueue:
    if not path.is_file():
        return ShortHandoffQueue()
    queue = ShortHandoffQueue.model_validate_json(path.read_text(encoding="utf-8"))
    return queue.model_copy(update={"buffer_target": min(queue.buffer_target, DEFAULT_BUFFER_TARGET)})


def write_handoff(path: Path, queue: ShortHandoffQueue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(queue.model_dump_json(indent=2) + "\n", encoding="utf-8")


def prepare_short_handoff(
    *,
    settings: Settings,
    queue_path: Path = DEFAULT_QUEUE,
    render_root: Path = Path("data/local/video_render"),
    limit: int = 13,
    packages: list[ContentPackage] | None = None,
    render: Callable[..., RenderResult] = render_package,
) -> ShortHandoffQueue:
    if limit < 1:
        raise ValueError("handoff preparation limit must be positive")
    current = load_handoff(queue_path)
    by_package = {item.package_id: item for item in current.items}
    candidates = [package for package in (packages or build_content_packages()) if package.format == "SHORT_FORM" and package.generation_status == "READY_FOR_REVIEW" and validate_package(package)]
    family_counts = {package_family(item.package_id): 0 for item in by_package.values() if item.status == "queued"}
    opportunity_counts = {package_opportunity(item.package_id): 0 for item in by_package.values() if item.status == "queued"}
    for item in by_package.values():
        if item.status == "queued":
            family_counts[package_family(item.package_id)] = family_counts.get(package_family(item.package_id), 0) + 1
            opportunity_counts[package_opportunity(item.package_id)] = opportunity_counts.get(package_opportunity(item.package_id), 0) + 1
    for package in sorted(candidates, key=lambda item: (family_counts.get(item.content_family, 0), opportunity_counts.get(item.opportunity_id or "gamcryp", 0), item.package_id)):
        if len([item for item in by_package.values() if item.status == "queued"]) >= limit:
            break
        existing = by_package.get(package.package_id)
        if existing and existing.evidence_fingerprint == package.evidence_fingerprint and Path(existing.video_path).is_file():
            continue
        result = render(package, settings=settings, root=render_root)
        blockers = validate_render(result)
        if result.status != RENDER_READY or blockers:
            continue
        if result.voice_id is None or result.model_id is None or result.narration_path is None or result.video_path is None or result.caption_path is None:
            continue
        video_checksum = hashlib.sha256(Path(result.video_path).read_bytes()).hexdigest()
        by_package[package.package_id] = ShortHandoffItem(
            package_id=package.package_id,
            content_id=package.source_inventory_item_id,
            readiness="GREEN",
            title=package.title_candidates[0],
            description=_description(package),
            source_url=f"{settings.public_base_url.rstrip('/')}{package.canonical_source_url}",
            tags=("GamCryp", "Web3", package.content_family.replace("_", " ").title()),
            video_path=result.video_path,
            caption_path=result.caption_path,
            narration_path=result.narration_path,
            narration_provider="elevenlabs",
            narration_voice_id=result.voice_id,
            narration_model_id=result.model_id,
            evidence_fingerprint=package.evidence_fingerprint,
            video_checksum=video_checksum,
            created_at=datetime.now(UTC).isoformat(),
        )
        family_counts[package.content_family] = family_counts.get(package.content_family, 0) + 1
        opportunity_counts[package.opportunity_id or "gamcryp"] = opportunity_counts.get(package.opportunity_id or "gamcryp", 0) + 1
    queue = ShortHandoffQueue(buffer_target=min(current.buffer_target, DEFAULT_BUFFER_TARGET), items=tuple(sorted(by_package.values(), key=lambda item: item.package_id)))
    write_handoff(queue_path, queue)
    return queue


def publish_next(
    *,
    publisher: YouTubePublisher,
    queue_path: Path = DEFAULT_QUEUE,
    cap_path: Path = DEFAULT_CAP_STATE,
    now: datetime | None = None,
    live: bool = False,
) -> dict[str, Any]:
    queue = load_handoff(queue_path)
    item = next((candidate for candidate in queue.items if candidate.status == "queued" and candidate.readiness == "GREEN"), None)
    if item is None:
        return {"status": "idle", "detail": "no queued GREEN short"}
    blockers = _handoff_blockers(item)
    if blockers:
        return {"status": "not_ready", "content_id": item.content_id, "detail": "; ".join(blockers)}
    current = now or datetime.now(UTC)
    cap = _load_cap(cap_path, current)
    if live and not cap.available:
        return {"status": "daily_cap", "content_id": item.content_id, "detail": "one successful autonomous public YouTube publication already recorded for the local calendar day"}
    manifest = YouTubePublishManifest(
        content_id=item.content_id,
        video_path=Path(item.video_path),
        title=item.title,
        description=item.description,
        tags=item.tags,
        privacy="public",
        category_id=item.category_id,
        made_for_kids=False,
        campaign_source="youtube",
        campaign_medium="short",
        campaign_campaign="content-package-handoff",
    )
    operation = publisher.upload_video(manifest) if live else publisher.dry_run_upload(manifest)
    if live and operation.status == "uploaded":
        _save_cap(cap_path, DailyCap(cap.date, cap.successful_publications + 1))
        _replace_item(queue_path, queue, item.model_copy(update={"status": "uploaded"}))
    return {"status": operation.status if live else "dry_run", "content_id": item.content_id, "video_id": operation.video_id}


def report(queue_path: Path = DEFAULT_QUEUE, cap_path: Path = DEFAULT_CAP_STATE, *, now: datetime | None = None) -> dict[str, Any]:
    queue = load_handoff(queue_path)
    cap = _load_cap(cap_path, now or datetime.now(UTC))
    return {
        "buffer_target": queue.buffer_target,
        "queued_green_shorts": sum(item.status == "queued" and item.readiness == "GREEN" for item in queue.items),
        "uploaded": sum(item.status == "uploaded" for item in queue.items),
        "daily_cap_used": cap.successful_publications,
        "daily_cap_available": cap.available,
    }


def autonomous_youtube_cap_available(path: Path = DEFAULT_CAP_STATE, *, now: datetime | None = None) -> bool:
    return _load_cap(path, now or datetime.now(UTC)).available


def record_autonomous_youtube_success(path: Path = DEFAULT_CAP_STATE, *, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    cap = _load_cap(path, current)
    _save_cap(path, DailyCap(cap.date, cap.successful_publications + 1))


def _description(package: ContentPackage) -> str:
    facts = "\n\n".join(str(point["text"]) for point in package.factual_talking_points if point.get("text"))
    return f"{package.hook}\n\n{facts}\n\n{package.cta}"[:5000]


def package_family(package_id: str) -> str:
    parts = package_id.split("-")
    return parts[2] if len(parts) > 2 else "unknown"


def package_opportunity(package_id: str) -> str:
    parts = package_id.split("-", 3)
    return parts[3] if len(parts) > 3 else package_id


def _handoff_blockers(item: ShortHandoffItem) -> tuple[str, ...]:
    blockers: list[str] = []
    if item.format != "SHORT_FORM":
        blockers.append("only SHORT_FORM assets may enter this handoff")
    if item.readiness != "GREEN":
        blockers.append("handoff item is not GREEN")
    if item.narration_provider != "elevenlabs" or item.narration_voice_id not in {voice_id for _, voice_id in APPROVED_VOICES}:
        blockers.append("approved ElevenLabs narration metadata is required")
    for label, value in (("video", item.video_path), ("captions", item.caption_path), ("narration", item.narration_path)):
        if not Path(value).is_file():
            blockers.append(f"{label} asset is missing")
    if Path(item.video_path).is_file() and hashlib.sha256(Path(item.video_path).read_bytes()).hexdigest() != item.video_checksum:
        blockers.append("video checksum does not match handoff metadata")
    return tuple(blockers)


def _load_cap(path: Path, now: datetime) -> DailyCap:
    local_date = _local_date(now)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("date") == local_date:
            return DailyCap(local_date, int(payload.get("successful_publications", 0)))
    except (OSError, ValueError, TypeError):
        pass
    return DailyCap(local_date, 0)


def _save_cap(path: Path, cap: DailyCap) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "date": cap.date, "successful_publications": cap.successful_publications}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _local_date(now: datetime) -> str:
    timezone_name = os.getenv("GAMEFI_LOCAL_TIMEZONE", "Europe/Istanbul")
    return now.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _replace_item(path: Path, queue: ShortHandoffQueue, old: ShortHandoffItem) -> None:
    updated = tuple(item.model_copy(update={"status": "uploaded"}) if item.package_id == old.package_id else item for item in queue.items)
    write_handoff(path, queue.model_copy(update={"items": updated}))
