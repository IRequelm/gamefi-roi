"""Deterministic YouTube queue derived from validated Content Pack Lite artifacts."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.distribution.content_pack import (
    ContentPackLite,
    ContentReadiness,
    SourceReference,
    canonical_json,
    validate_batch,
)

YOUTUBE_QUEUE_VERSION = "youtube-publish-queue-v1"
APPROVED_NEURAL_PROVIDERS = frozenset({"elevenlabs", "heygen"})
FORBIDDEN_NARRATION_PROVIDERS = frozenset({"system", "windows", "pyttsx", "basic_tts", "generic_tts"})


class YouTubeApprovalState(str, Enum):
    NOT_REQUIRED = "not_required"
    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    BLOCKED = "blocked"


class YouTubeQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    channel: str = "YOUTUBE_SHORT"
    project: str
    title: str
    description: str
    short_script: str
    attribution_url: str
    status: ContentReadiness
    approval_required: bool
    approval_state: YouTubeApprovalState
    source_snapshot_id: str | None = None
    source_snapshot_timestamp: str | None = None
    source_snapshot_hash: str
    refreshability: str | None = None
    official_source_refs: tuple[SourceReference, ...]
    video_asset_state: str = "missing"
    thumbnail_asset_state: str = "missing"
    upload_state: str = "not_uploaded"
    package_checksum: str
    recommended_order: int
    source_pack_version: str
    generated_at: str
    narration_mode: str = "unknown"
    voice_provider: str | None = None
    voice_model: str | None = None
    narration_quality_status: str = "unknown"


class YouTubePublishQueue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    queue_version: str = YOUTUBE_QUEUE_VERSION
    source_batch_id: str
    source_batch_hash: str
    generated_at: str
    publishable: tuple[YouTubeQueueItem, ...]
    awaiting_human_approval: tuple[YouTubeQueueItem, ...]
    blocked: tuple[YouTubeQueueItem, ...]
    pending_asset: tuple[YouTubeQueueItem, ...] = ()

    @property
    def items(self) -> tuple[YouTubeQueueItem, ...]:
        return self.publishable + self.awaiting_human_approval + self.blocked + self.pending_asset

    def find(self, content_id: str) -> YouTubeQueueItem:
        matches = [item for item in self.items if item.content_id == content_id]
        if len(matches) != 1:
            raise KeyError(content_id)
        return matches[0]


def youtube_package_checksum(pack: ContentPackLite) -> str:
    payload = {
        "attribution_url": pack.distribution.youtube_utm_url,
        "content_id": pack.content_id,
        "content_pack_version": pack.content_pack_version,
        "description": _final_description(pack),
        "official_source_refs": [item.model_dump(mode="json") for item in pack.source.official_source_refs],
        "refreshability": pack.source.refreshability.value if pack.source.refreshability else None,
        "short_script": pack.editorial.youtube_short_script,
        "snapshot_id": pack.source.snapshot_id,
        "snapshot_timestamp": pack.source.snapshot_timestamp,
        "source_snapshot_hash": pack.source.source_snapshot_hash,
        "title": pack.editorial.youtube_title,
    }
    # Preserve the checksum of legacy packs that predate the narration policy;
    # explicit quality metadata is included once a producer records it.
    if (
        pack.editorial.narration_mode != "unknown"
        or pack.editorial.voice_provider
        or pack.editorial.voice_model
        or pack.editorial.narration_quality_status != "unknown"
    ):
        payload.update(
            {
                "narration_mode": pack.editorial.narration_mode,
                "voice_provider": pack.editorial.voice_provider,
                "voice_model": pack.editorial.voice_model,
                "narration_quality_status": pack.editorial.narration_quality_status,
            }
        )
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_youtube_publish_queue(
    *,
    batch_payload: dict[str, Any],
    packs: tuple[ContentPackLite, ...],
    source_batch_bytes: bytes,
    video_directory: Path | None = None,
) -> YouTubePublishQueue:
    validate_batch(list(packs))
    youtube_packs = tuple(pack for pack in packs if _has_youtube_package(pack))
    items = tuple(_queue_item(pack, index + 1, str(batch_payload["generated_at"])) for index, pack in enumerate(youtube_packs))
    publishable = tuple(item for item in items if item.status is ContentReadiness.GREEN)
    pending_asset = tuple(item for item in publishable if narration_quality_blockers(item))
    publishable = tuple(item for item in publishable if item not in pending_asset)
    if video_directory is not None:
        missing_assets = tuple(
            item for item in publishable
            if not any((video_directory / f"{item.content_id}{extension}").is_file() for extension in (".mp4", ".mov", ".m4v", ".webm"))
        )
        pending_asset += missing_assets
        publishable = tuple(item for item in publishable if item not in missing_assets)
    return YouTubePublishQueue(
        source_batch_id=str(batch_payload["batch_id"]),
        source_batch_hash=hashlib.sha256(source_batch_bytes).hexdigest(),
        generated_at=str(batch_payload["generated_at"]),
        publishable=publishable,
        awaiting_human_approval=tuple(item for item in items if item.status is ContentReadiness.YELLOW),
        blocked=tuple(item for item in items if item.status is ContentReadiness.RED),
        pending_asset=pending_asset,
    )


def load_youtube_queue(path: Path) -> YouTubePublishQueue:
    return YouTubePublishQueue.model_validate_json(path.read_text(encoding="utf-8"))


def write_youtube_queue(path: Path, queue: YouTubePublishQueue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(queue.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _has_youtube_package(pack: ContentPackLite) -> bool:
    fields = (
        pack.editorial.youtube_title,
        pack.editorial.youtube_short_script,
        pack.editorial.youtube_description,
    )
    if any(fields) and not all(fields):
        raise ValueError(f"Incomplete YouTube package: {pack.content_id}")
    return all(fields)


def _final_description(pack: ContentPackLite) -> str:
    description = (pack.editorial.youtube_description or "").strip()
    return f"{description}\n\nExplore the source-backed opportunity: {pack.distribution.youtube_utm_url}"


def _queue_item(pack: ContentPackLite, order: int, generated_at: str) -> YouTubeQueueItem:
    status = pack.editorial.readiness
    approval_state = {
        ContentReadiness.GREEN: YouTubeApprovalState.NOT_REQUIRED,
        ContentReadiness.YELLOW: YouTubeApprovalState.AWAITING_HUMAN_APPROVAL,
        ContentReadiness.RED: YouTubeApprovalState.BLOCKED,
    }[status]
    return YouTubeQueueItem(
        content_id=pack.content_id,
        project=pack.facts.project_name,
        title=pack.editorial.youtube_title or "",
        description=_final_description(pack),
        short_script=pack.editorial.youtube_short_script or "",
        attribution_url=pack.distribution.youtube_utm_url,
        status=status,
        approval_required=status is ContentReadiness.YELLOW,
        approval_state=approval_state,
        source_snapshot_id=pack.source.snapshot_id,
        source_snapshot_timestamp=pack.source.snapshot_timestamp,
        source_snapshot_hash=pack.source.source_snapshot_hash,
        refreshability=pack.source.refreshability.value if pack.source.refreshability else None,
        official_source_refs=tuple(pack.source.official_source_refs),
        package_checksum=youtube_package_checksum(pack),
        recommended_order=order,
        source_pack_version=pack.content_pack_version,
        generated_at=generated_at,
        narration_mode=pack.editorial.narration_mode,
        voice_provider=pack.editorial.voice_provider,
        voice_model=pack.editorial.voice_model,
        narration_quality_status=pack.editorial.narration_quality_status,
    )


def narration_quality_blockers(item: YouTubeQueueItem) -> tuple[str, ...]:
    """Return publish blockers for narration provenance and quality."""

    mode = item.narration_mode.strip().lower()
    provider = (item.voice_provider or "").strip().lower()
    status = item.narration_quality_status.strip().lower()
    if mode in {"music_only", "silent"}:
        return () if status == "approved" else ("intentional no-narration format is not approved",)
    if mode == "human":
        return () if status == "approved" else ("human narration quality is not approved",)
    if mode == "neural_voice":
        if provider in FORBIDDEN_NARRATION_PROVIDERS:
            return ("forbidden basic/system TTS provider",)
        if provider not in APPROVED_NEURAL_PROVIDERS:
            return ("neural voice provider is not approved",)
        return () if status == "approved" else ("neural narration quality is not approved",)
    return ("narration mode is missing or unknown",)
