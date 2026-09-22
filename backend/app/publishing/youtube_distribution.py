"""Approval-gated YouTube publishing over the low-level Data API transport."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict

from app.distribution.content_pack import ContentPackLite, ContentReadiness
from app.distribution.x_queue import load_content_pack_batch
from app.distribution.youtube_queue import (
    YouTubePublishQueue,
    YouTubeQueueItem,
    build_youtube_publish_queue,
    load_youtube_queue,
    write_youtube_queue,
    youtube_package_checksum,
    narration_quality_blockers,
)
from app.publishing.youtube import (
    YouTubeManifestError,
    YouTubeOperationResult,
    YouTubePublishManifest,
    YouTubePublisher,
    sha256_file,
    validate_thumbnail_file,
    validate_video_file,
)

ApprovalState = Literal["approved", "revoked"]


class YouTubeDistributionError(YouTubeManifestError):
    """Fail-closed queue, approval, or asset error."""


class YouTubeCreativeApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    state: ApprovalState
    approved_at: str
    package_checksum: str
    video_checksum: str
    thumbnail_checksum: str | None = None
    creative_checksum: str


class YouTubePackagePreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    project: str
    readiness: ContentReadiness
    approval_state: str
    title: str
    description: str
    short_script: str
    attribution_url: str
    package_checksum: str
    creative_checksum: str | None
    video_asset_state: str
    thumbnail_asset_state: str
    upload_state: str
    source_snapshot_id: str | None
    source_snapshot_timestamp: str | None
    refreshability: str | None
    would_upload: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class YouTubeDistributionConfig:
    content_pack_file: Path = Path("distribution/content_packs/learning_batch_001.json")
    queue_file: Path = Path("distribution/publish_queue/youtube_publish_queue.json")
    approval_file: Path = Path("data/local/youtube/approvals.json")


class YouTubeApprovalStore:
    def __init__(self, path: Path):
        self.path = path

    def latest(self, content_id: str) -> YouTubeCreativeApproval | None:
        raw = self._read().get(content_id)
        return YouTubeCreativeApproval.model_validate(raw) if isinstance(raw, dict) else None

    def save(self, record: YouTubeCreativeApproval) -> None:
        records = self._read()
        records[record.content_id] = record.model_dump(mode="json")
        self._write(records)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        records = payload.get("records", payload) if isinstance(payload, dict) else None
        if not isinstance(records, dict):
            raise YouTubeDistributionError("YouTube approval state must contain a records object")
        return records

    def _write(self, records: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "records": records}, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temp_name, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class YouTubeDistributionPublisher:
    def __init__(
        self,
        publisher: YouTubePublisher,
        *,
        config: YouTubeDistributionConfig | None = None,
        approvals: YouTubeApprovalStore | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.publisher = publisher
        self.config = config or YouTubeDistributionConfig()
        self.approvals = approvals or YouTubeApprovalStore(self.config.approval_file)
        self.now = now

    def rebuild_queue(self) -> YouTubePublishQueue:
        source_bytes = self.config.content_pack_file.read_bytes()
        payload, packs = load_content_pack_batch(self.config.content_pack_file)
        queue = build_youtube_publish_queue(
            batch_payload=payload,
            packs=packs,
            source_batch_bytes=source_bytes,
        )
        write_youtube_queue(self.config.queue_file, queue)
        return queue

    def queue_summary(self) -> dict[str, Any]:
        queue, _ = self._load_context()
        return {
            "queue_version": queue.queue_version,
            "publishable": [item.content_id for item in queue.publishable],
            "awaiting_human_approval": [item.content_id for item in queue.awaiting_human_approval],
            "blocked": [item.content_id for item in queue.blocked],
            "pending_asset": [item.content_id for item in queue.pending_asset],
        }

    def preview(
        self,
        content_id: str,
        *,
        video_path: Path | None = None,
        thumbnail_path: Path | None = None,
    ) -> YouTubePackagePreview:
        queue, packs = self._load_context()
        item = _find_item(queue, content_id)
        pack = _find_pack(packs, content_id)
        blockers = list(self._package_blockers(item, pack))
        video_checksum, thumbnail_checksum, asset_blockers = _asset_checksums(video_path, thumbnail_path)
        blockers.extend(asset_blockers)
        creative_checksum = (
            _creative_checksum(item.package_checksum, video_checksum, thumbnail_checksum)
            if video_checksum
            else None
        )
        approval_state = "blocked"
        if item.status in {ContentReadiness.GREEN, ContentReadiness.YELLOW}:
            approval_state = "awaiting_human_approval"
            approval = self.approvals.latest(content_id)
            if approval and approval.state == "approved" and creative_checksum:
                if (
                    approval.package_checksum == item.package_checksum
                    and approval.video_checksum == video_checksum
                    and approval.thumbnail_checksum == thumbnail_checksum
                    and approval.creative_checksum == creative_checksum
                ):
                    approval_state = "approved"
                else:
                    approval_state = "approval_invalidated_by_content_or_asset_change"
            if approval_state != "approved":
                blockers.append("GREEN/YELLOW package requires checksum-bound human creative approval")
        if item.status is ContentReadiness.RED:
            blockers.append("RED package is permanently blocked from YouTube publishing")
        upload_state = "not_uploaded"
        record = self.publisher.state_store.find(content_id)
        if record is not None:
            upload_state = record.status
            if video_checksum and record.video_checksum_sha256 == video_checksum and record.status == "uploaded":
                blockers.append("same content_id and video checksum were already uploaded")
            elif video_checksum and record.video_checksum_sha256 != video_checksum:
                blockers.append("content_id already has a different video checksum")
        return YouTubePackagePreview(
            content_id=item.content_id,
            project=item.project,
            readiness=item.status,
            approval_state=approval_state,
            title=item.title,
            description=item.description,
            short_script=item.short_script,
            attribution_url=item.attribution_url,
            package_checksum=item.package_checksum,
            creative_checksum=creative_checksum,
            video_asset_state="ready" if video_checksum else "missing",
            thumbnail_asset_state="ready" if thumbnail_checksum else "missing",
            upload_state=upload_state,
            source_snapshot_id=item.source_snapshot_id,
            source_snapshot_timestamp=item.source_snapshot_timestamp,
            refreshability=item.refreshability,
            would_upload=not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
        )

    def approve(
        self,
        content_id: str,
        *,
        video_path: Path,
        thumbnail_path: Path | None = None,
    ) -> YouTubeCreativeApproval:
        queue, packs = self._load_context()
        item = _find_item(queue, content_id)
        pack = _find_pack(packs, content_id)
        if item.status is ContentReadiness.RED:
            raise YouTubeDistributionError("RED package cannot be approved")
        if item.status not in {ContentReadiness.GREEN, ContentReadiness.YELLOW}:
            raise YouTubeDistributionError("RED package cannot be approved")
        blockers = list(self._package_blockers(item, pack))
        video_checksum, thumbnail_checksum, asset_blockers = _asset_checksums(video_path, thumbnail_path)
        blockers.extend(asset_blockers)
        if blockers or not video_checksum:
            raise YouTubeDistributionError("Approval blocked: " + "; ".join(blockers))
        checksum = _creative_checksum(item.package_checksum, video_checksum, thumbnail_checksum)
        record = YouTubeCreativeApproval(
            content_id=content_id,
            state="approved",
            approved_at=self.now().isoformat(),
            package_checksum=item.package_checksum,
            video_checksum=video_checksum,
            thumbnail_checksum=thumbnail_checksum,
            creative_checksum=checksum,
        )
        self.approvals.save(record)
        return record

    def revoke(self, content_id: str) -> YouTubeCreativeApproval:
        current = self.approvals.latest(content_id)
        if current is None:
            raise YouTubeDistributionError("No YouTube approval exists for this content_id")
        revoked = current.model_copy(update={"state": "revoked", "approved_at": self.now().isoformat()})
        self.approvals.save(revoked)
        return revoked

    def dry_run(
        self,
        content_id: str,
        *,
        video_path: Path,
        thumbnail_path: Path | None = None,
    ) -> YouTubeOperationResult:
        preview = self.preview(content_id, video_path=video_path, thumbnail_path=thumbnail_path)
        if not preview.would_upload:
            raise YouTubeDistributionError("Dry-run blocked: " + "; ".join(preview.blockers))
        return self.publisher.dry_run_upload(self._manifest(preview, video_path, thumbnail_path))

    def upload(
        self,
        content_id: str,
        *,
        video_path: Path,
        thumbnail_path: Path | None = None,
        confirm_publish: bool = False,
        privacy: str = "private",
        category_id: str | None = None,
        made_for_kids: bool = False,
    ) -> YouTubeOperationResult:
        if not confirm_publish:
            raise YouTubeDistributionError("Upload requires explicit --confirm-publish")
        preview = self.preview(content_id, video_path=video_path, thumbnail_path=thumbnail_path)
        if not preview.would_upload:
            raise YouTubeDistributionError("Upload blocked: " + "; ".join(preview.blockers))
        return self.publisher.upload_video(
            self._manifest(
                preview,
                video_path,
                thumbnail_path,
                privacy=privacy,
                category_id=category_id,
                made_for_kids=made_for_kids,
            )
        )

    def _manifest(
        self,
        preview: YouTubePackagePreview,
        video_path: Path,
        thumbnail_path: Path | None,
        *,
        privacy: str = "private",
        category_id: str | None = None,
        made_for_kids: bool = False,
    ) -> YouTubePublishManifest:
        timestamp = (
            datetime.fromisoformat(preview.source_snapshot_timestamp.replace("Z", "+00:00"))
            if preview.source_snapshot_timestamp
            else None
        )
        return YouTubePublishManifest(
            content_id=preview.content_id,
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            title=preview.title,
            description=preview.description,
            tags=("GamCryp", "Web3", preview.project),
            privacy=privacy,
            category_id=category_id,
            made_for_kids=made_for_kids,
            source_snapshot_id=preview.source_snapshot_id,
            source_snapshot_timestamp=timestamp,
            campaign_source="youtube",
            campaign_medium="short",
            campaign_campaign="distribution-mvp",
        )

    def _load_context(self) -> tuple[YouTubePublishQueue, tuple[ContentPackLite, ...]]:
        queue = load_youtube_queue(self.config.queue_file)
        source_bytes = self.config.content_pack_file.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != queue.source_batch_hash:
            raise YouTubeDistributionError("YouTube queue is stale relative to the canonical content-pack artifact")
        _, packs = load_content_pack_batch(self.config.content_pack_file)
        youtube_packs = tuple(pack for pack in packs if pack.editorial.youtube_short_script)
        if {item.content_id for item in queue.items} != {pack.content_id for pack in youtube_packs}:
            raise YouTubeDistributionError("YouTube queue inventory does not match canonical content packs")
        return queue, youtube_packs

    @staticmethod
    def _package_blockers(item: YouTubeQueueItem, pack: ContentPackLite) -> tuple[str, ...]:
        blockers: list[str] = []
        if youtube_package_checksum(pack) != item.package_checksum:
            blockers.append("YouTube package checksum does not match canonical content pack")
        if item.attribution_url not in item.description:
            blockers.append("YouTube description is missing the exact attribution URL")
        if pack.editorial.readiness is not item.status:
            blockers.append("YouTube queue readiness does not match canonical content pack")
        if item.status is ContentReadiness.GREEN:
            blockers.extend(narration_quality_blockers(item))
        return tuple(blockers)


def _find_item(queue: YouTubePublishQueue, content_id: str) -> YouTubeQueueItem:
    try:
        return queue.find(content_id)
    except KeyError as exc:
        raise YouTubeDistributionError(f"Unknown YouTube content_id: {content_id}") from exc


def _find_pack(packs: tuple[ContentPackLite, ...], content_id: str) -> ContentPackLite:
    matches = [pack for pack in packs if pack.content_id == content_id]
    if len(matches) != 1:
        raise YouTubeDistributionError(f"Canonical YouTube content pack not found: {content_id}")
    return matches[0]


def _asset_checksums(
    video_path: Path | None,
    thumbnail_path: Path | None,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    blockers: list[str] = []
    video_checksum: str | None = None
    thumbnail_checksum: str | None = None
    if video_path is None:
        blockers.append("video asset is missing")
    else:
        try:
            validate_video_file(video_path)
            video_checksum = sha256_file(video_path)
        except YouTubeManifestError as exc:
            blockers.append(str(exc))
    if thumbnail_path is not None:
        try:
            validate_thumbnail_file(thumbnail_path)
            thumbnail_checksum = sha256_file(thumbnail_path)
        except YouTubeManifestError as exc:
            blockers.append(str(exc))
    return video_checksum, thumbnail_checksum, tuple(blockers)


def _creative_checksum(package_checksum: str, video_checksum: str, thumbnail_checksum: str | None) -> str:
    payload = f"{package_checksum}\n{video_checksum}\n{thumbnail_checksum or ''}"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()
