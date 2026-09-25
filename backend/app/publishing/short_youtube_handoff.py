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
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import Engine

from app.config.settings import Settings
from app.content_package.generator import AUTONOMOUS_CATALOG_FAMILIES, ContentPackage, SITE_EXPLAINER_FAMILIES, build_content_packages, is_motion_graphic_explainer, is_site_explainer, validate_package
from app.video_render.factory import APPROVED_VOICES, RENDER_READY, RenderResult, music_bed_source_fingerprint, render_package, short_quality_blockers, validate_render
from app.video_render.creative_qa import asset_plan, creative_preflight, frame_qa
from app.publishing.youtube import YouTubeOperationResult, YouTubePublishManifest, YouTubePublisher
from app.publishing.youtube import PublishStateStore
from app.publishing.elevenlabs import _atomic_write_text

HANDOFF_VERSION = "youtube-short-handoff-v1"
SHORT_CREATIVE_POLICY_VERSION = "approved-reuse-tts-motion-v9-licensed-music"
DEFAULT_QUEUE = Path("distribution/publish_queue/youtube_short_handoff.json")
DEFAULT_CAP_STATE = Path("data/local/youtube/autonomous_daily_cap.json")
DEFAULT_STANDING_POLICY = Path("data/local/youtube/site_short_publication_mandate.json")
STANDING_POLICY_ID = "user-directed-gamcryp-youtube-explainers-v2"
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
    narration_provider: str = "elevenlabs"
    narration_voice_id: str = ""
    narration_model_id: str = ""
    audio_mode: str = "neural_voice"
    narration_reused: bool = False
    evidence_fingerprint: str
    video_checksum: str
    created_at: str
    creative_approval_state: str = "pending_review"
    creative_approval_video_checksum: str | None = None
    creative_approved_at: str | None = None
    creative_reviewed_by: str | None = None
    creative_review_note: str | None = None


class ShortHandoffQueue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = HANDOFF_VERSION
    buffer_target: int = DEFAULT_BUFFER_TARGET
    items: tuple[ShortHandoffItem, ...] = ()
    blocked: dict[str, dict[str, Any]] = {}


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
    _atomic_write_text(path, queue.model_dump_json(indent=2) + "\n")


@contextmanager
def _handoff_prepare_lock(queue_path: Path):
    """Serialize CLI and scheduled-worker render preparation per queue.

    A render writes MP4, metadata, captions, and QA frames across several
    paths.  Atomic queue JSON alone cannot protect those related artifacts
    from a second prepare process.  The OS releases this lock if a process
    exits unexpectedly; the marker file itself is harmless and retained.
    """
    lock_path = Path(f"{queue_path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        handle.seek(0)
        handle.write(b"0")
        handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def prepare_short_handoff(
    *,
    settings: Settings,
    queue_path: Path = DEFAULT_QUEUE,
    render_root: Path = Path("data/local/video_render"),
    limit: int = 13,
    packages: list[ContentPackage] | None = None,
    render: Callable[..., RenderResult] = render_package,
    engine: Engine | None = None,
    force_rerender: bool = False,
) -> ShortHandoffQueue:
    with _handoff_prepare_lock(queue_path):
        return _prepare_short_handoff(
            settings=settings,
            queue_path=queue_path,
            render_root=render_root,
            limit=limit,
            packages=packages,
            render=render,
            engine=engine,
            force_rerender=force_rerender,
        )


def _prepare_short_handoff(
    *,
    settings: Settings,
    queue_path: Path = DEFAULT_QUEUE,
    render_root: Path = Path("data/local/video_render"),
    limit: int = 13,
    packages: list[ContentPackage] | None = None,
    render: Callable[..., RenderResult] = render_package,
    engine: Engine | None = None,
    force_rerender: bool = False,
) -> ShortHandoffQueue:
    if limit < 1:
        raise ValueError("handoff preparation limit must be positive")
    current = load_handoff(queue_path)
    by_package = {item.package_id: item for item in current.items}
    blocked = dict(current.blocked)
    publication_state = PublishStateStore(Path(settings.youtube_publish_state_file))
    candidates = [package for package in (packages or build_content_packages(engine=engine)) if package.format == "SHORT_FORM" and package.generation_status == "READY_FOR_REVIEW" and validate_package(package)]
    # A publication record is keyed by content package, but viewers experience
    # the opportunity as the subject.  Once an opportunity has an uploaded or
    # unresolved/ambiguous attempt, do not silently select another angle for
    # the same opportunity.  This is especially important after an interrupted
    # YouTube upload: the next run must reconcile the old attempt, not create a
    # second Akash/DFK/etc. Short while the first result is unknown.
    published_or_ambiguous_opportunities = {
        package.opportunity_id
        for package in candidates
        if package.opportunity_id
        and (prior := publication_state.find(package.source_inventory_item_id)) is not None
        and prior.status in {"uploaded", "ambiguous"}
    }
    published_or_ambiguous_opportunities.update(
        package_opportunity(item.package_id)
        for item in by_package.values()
        if item.status in {"uploaded", "ambiguous"} and package_opportunity(item.package_id) != "unknown"
    )
    family_counts = {package_family(item.package_id): 0 for item in by_package.values() if item.status == "queued"}
    opportunity_counts = {package_opportunity(item.package_id): 0 for item in by_package.values() if item.status == "queued"}
    # Reconcile checksums for already-queued renders before applying the
    # bounded buffer limit. A quality rebuild must not leave a valid item
    # blocked by the checksum of its previous MP4.
    # Never adopt a changed MP4 checksum without a successful render/QA result.
    for item in by_package.values():
        if item.status == "queued":
            family_counts[package_family(item.package_id)] = family_counts.get(package_family(item.package_id), 0) + 1
            opportunity_counts[package_opportunity(item.package_id)] = opportunity_counts.get(package_opportunity(item.package_id), 0) + 1
    for package in sorted(candidates, key=lambda item: (0 if is_site_explainer(item) else 1 if item.content_family in {"HOW_TO_START", "WHAT_YOU_NEED", "HOW_YOU_EARN", "HOW_TO_CLAIM_OR_EXIT", "DEPIN_SETUP", "WHY_ROI_UNAVAILABLE"} else 2, family_counts.get(item.content_family, 0), opportunity_counts.get(item.opportunity_id or "gamcryp", 0), item.package_id)):
        existing = by_package.get(package.package_id)
        prior = publication_state.find(package.source_inventory_item_id)
        if (
            package.opportunity_id
            and package.opportunity_id in published_or_ambiguous_opportunities
            and not (existing and existing.status == "queued")
        ):
            continue
        if prior is not None:
            if existing and prior.status == "uploaded":
                by_package[package.package_id] = existing.model_copy(update={"status": "uploaded"})
            continue
        if existing and existing.status == "uploaded":
            continue
        previous = blocked.get(package.package_id, {})
        # A package may have been dead-lettered because an approved product
        # visual was missing. Re-check current creative blockers before
        # honoring retry suppression: adding the asset must permit a fresh,
        # review-only render.
        creative_blockers = creative_preflight(package) if packages is None else ()
        if (
            previous.get("evidence_fingerprint") == package.evidence_fingerprint
            and previous.get("policy_version") == SHORT_CREATIVE_POLICY_VERSION
            and previous.get("attempts", 0) >= 3
            and creative_blockers
        ):
            continue
        if (not force_rerender and existing and existing.evidence_fingerprint == package.evidence_fingerprint and Path(existing.video_path).is_file() and _stored_render_creative_ready(existing, package)):
            expected_source_url = f"{settings.public_base_url.rstrip('/')}{package.canonical_source_url}"
            expected_description = _description(package, settings.public_base_url, existing.audio_mode)
            updates: dict[str, Any] = {}
            if existing.source_url != expected_source_url:
                updates["source_url"] = expected_source_url
            if existing.description != expected_description:
                updates["description"] = expected_description
            # A quality-gated render can be rebuilt by an operator or a
            # recovery worker after the handoff record was written.  Adopt the
            # new checksum only after the persisted render metadata verifies
            # the current video/audio/caption files and creative QA result.
            # This prevents a valid rebuilt video from being stuck behind a
            # stale checksum while still refusing unverified file changes.
            current_video_checksum = hashlib.sha256(Path(existing.video_path).read_bytes()).hexdigest()
            if current_video_checksum != existing.video_checksum:
                if _load_render_quality_metadata(existing) is None:
                    continue
                updates.update(
                    {
                        "video_checksum": current_video_checksum,
                        "creative_approval_state": "pending_review",
                        "creative_approval_video_checksum": None,
                        "creative_approved_at": None,
                    }
                )
            if updates:
                by_package[package.package_id] = existing.model_copy(update=updates)
            continue
        # Reconcile/rebuild an existing queued render even when the bounded
        # buffer is full. The limit applies to new queue additions, not to a
        # newly available official product visual or other quality rebuild.
        if len([item for item in by_package.values() if item.status == "queued"]) >= limit and not (existing and existing.status == "queued"):
            continue
        if packages is None and creative_blockers:
            # Do not spend narration credits or create a publishable-looking
            # asset when the creative director has not approved the package.
            blocked[package.package_id] = {"state": "BLOCKED_PACKAGE", "reason": "; ".join(creative_blockers), "evidence_fingerprint": package.evidence_fingerprint, "policy_version": SHORT_CREATIVE_POLICY_VERSION, "attempts": 3}
            continue
        result = render(package, settings=settings, root=render_root)
        blockers = validate_render(result)
        if result.status != RENDER_READY or blockers:
            blocked[package.package_id] = {"state": "BLOCKED_NARRATION" if "NARRATION" in (result.reason or "") else "BLOCKED_RENDER", "reason": result.reason or "; ".join(blockers), "evidence_fingerprint": package.evidence_fingerprint, "policy_version": SHORT_CREATIVE_POLICY_VERSION, "attempts": previous.get("attempts", 0) + 1, "updated_at": datetime.now(UTC).isoformat()}
            continue
        if result.narration_path is None or result.video_path is None or result.caption_path is None:
            continue
        if result.audio_mode == "neural_voice" and not (result.quality_metadata or {}).get("narration_reused"):
            # Newly generated neural audio is never admitted to the
            # autonomous queue. Reused audio is admitted only after the
            # renderer verified its exact script/checksum and quality status.
            continue
        if result.audio_mode not in {"music_only", "human", "neural_voice"}:
            continue
        if result.audio_mode in {"human", "neural_voice"} and (result.voice_id is None or result.model_id is None):
            continue
        video_checksum = hashlib.sha256(Path(result.video_path).read_bytes()).hexdigest()
        blocked.pop(package.package_id, None)
        by_package[package.package_id] = ShortHandoffItem(
            package_id=package.package_id,
            content_id=package.source_inventory_item_id,
            readiness="GREEN",
            title=package.title_candidates[0],
            description=_description(package, settings.public_base_url, result.audio_mode),
            source_url=f"{settings.public_base_url.rstrip('/')}{package.canonical_source_url}",
            tags=("GamCryp", "Web3", package.content_family.replace("_", " ").title()),
            video_path=result.video_path,
            caption_path=result.caption_path,
            narration_path=result.narration_path,
            narration_provider=(
                "local_music" if result.audio_mode == "music_only"
                else "elevenlabs" if result.audio_mode == "neural_voice"
                else "human"
            ),
            narration_voice_id=result.voice_id or "",
            narration_model_id=result.model_id or "",
            audio_mode=result.audio_mode,
            narration_reused=bool((result.quality_metadata or {}).get("narration_reused")),
            evidence_fingerprint=package.evidence_fingerprint,
            video_checksum=video_checksum,
            created_at=datetime.now(UTC).isoformat(),
            creative_approval_state="pending_review",
        )
        family_counts[package.content_family] = family_counts.get(package.content_family, 0) + 1
        opportunity_counts[package.opportunity_id or "gamcryp"] = opportunity_counts.get(package.opportunity_id or "gamcryp", 0) + 1
    queue = ShortHandoffQueue(buffer_target=min(current.buffer_target, DEFAULT_BUFFER_TARGET), items=tuple(sorted(by_package.values(), key=lambda item: item.package_id)), blocked=blocked)
    write_handoff(queue_path, queue)
    return queue


def publish_next(
    *,
    publisher: YouTubePublisher,
    queue_path: Path = DEFAULT_QUEUE,
    cap_path: Path = DEFAULT_CAP_STATE,
    now: datetime | None = None,
    live: bool = False,
    engine: Engine | None = None,
) -> dict[str, Any]:
    queue = load_handoff(queue_path)
    queued = [candidate for candidate in queue.items if candidate.status == "queued" and candidate.readiness == "GREEN"]
    # Only user-authorized educational explainers may be auto-approved.
    # They take precedence over preserved, pre-mandate review backlog.
    allowed_families = SITE_EXPLAINER_FAMILIES | AUTONOMOUS_CATALOG_FAMILIES
    item = next((candidate for candidate in queued if package_family(candidate.package_id) in allowed_families), None)
    if item is None:
        item = next(iter(queued), None)
    if item is None:
        return {"status": "idle", "detail": "no queued GREEN short"}
    package = next((candidate for candidate in build_content_packages(engine=engine) if candidate.package_id == item.package_id), None)
    blockers = _handoff_blockers(item, engine=engine)
    if package is not None:
        blockers = (*blockers, *creative_preflight(package))
        if not blockers and item.creative_approval_state != "approved" and _standing_policy_allows(package, item, publisher.config.channel_handle):
            approved = item.model_copy(update={
                "creative_approval_state": "approved",
                "creative_approval_video_checksum": item.video_checksum,
                "creative_approved_at": (now or datetime.now(UTC)).isoformat(),
                "creative_reviewed_by": "user-standing-mandate/automated-qa",
                "creative_review_note": f"{STANDING_POLICY_ID}; factual and render QA passed; checksum recorded; no TTS; licensed Kevin MacLeod music with attribution in description.",
            })
            updated = tuple(approved if candidate.package_id == item.package_id else candidate for candidate in queue.items)
            queue = queue.model_copy(update={"items": updated})
            write_handoff(queue_path, queue)
            item = approved
    if item.creative_approval_state != "approved":
        blockers = (*blockers, "human creative quality approval is required before YouTube use")
    elif item.creative_approval_video_checksum != item.video_checksum:
        blockers = (*blockers, "creative approval does not match the current video checksum")
    if blockers:
        return {"status": "not_ready", "content_id": item.content_id, "detail": "; ".join(blockers)}
    current = now or datetime.now(UTC)
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
    if live:
        # Hold the lock across the cap check, upload, and state update. This
        # prevents a second worker/CLI process from publishing a second Short
        # after both processes observed an available cap.
        with _daily_cap_lock(cap_path):
            cap = _load_cap(cap_path, current)
            if not cap.available:
                return {"status": "daily_cap", "content_id": item.content_id, "detail": "one successful autonomous public YouTube publication already recorded for the local calendar day"}
            operation = publisher.upload_video(manifest)
            if operation.status in {"uploaded", "skipped_duplicate"}:
                if operation.status == "uploaded":
                    _save_cap(cap_path, DailyCap(cap.date, cap.successful_publications + 1))
                _replace_item(queue_path, queue, item.model_copy(update={"status": "uploaded"}))
    else:
        operation = publisher.dry_run_upload(manifest)
    return {"status": operation.status if live else "dry_run", "validation_status": operation.status, "content_id": item.content_id, "video_id": operation.video_id}


def report(queue_path: Path = DEFAULT_QUEUE, cap_path: Path = DEFAULT_CAP_STATE, *, now: datetime | None = None) -> dict[str, Any]:
    queue = load_handoff(queue_path)
    cap = _load_cap(cap_path, now or datetime.now(UTC))
    audit = audit_handoff(queue_path)
    return {
        "buffer_target": queue.buffer_target,
        "queued_green_shorts": sum(item.status == "queued" and item.readiness == "GREEN" for item in queue.items),
        "uploaded": sum(item.status == "uploaded" for item in queue.items),
        "ambiguous": sum(item.status == "ambiguous" for item in queue.items),
        "blocked": queue.blocked,
        "quality_review_required": len(audit["items"]),
        "daily_cap_used": cap.successful_publications,
        "daily_cap_available": cap.available,
    }


def audit_handoff(queue_path: Path = DEFAULT_QUEUE) -> dict[str, Any]:
    """Report historical handoff records that cannot be treated as approved now.

    This is read-only. It intentionally does not change upload state: an old
    local record may correspond to a real external publication and must be
    reconciled against YouTube before being relabelled.
    """
    queue = load_handoff(queue_path)
    findings: list[dict[str, Any]] = []
    for item in queue.items:
        blockers: list[str] = []
        if item.status in {"uploaded", "ambiguous"} and item.creative_approval_state != "approved":
            blockers.append("historical item has no current checksum-bound creative approval")
        if item.source_url.startswith("http://localhost") or item.source_url.startswith("http://127.0.0.1"):
            blockers.append("source URL points to a local development host")
        if item.audio_mode == "neural_voice" and not item.narration_reused:
            blockers.append("historical neural narration has no verified reuse provenance")
        mandate_audio = item.creative_reviewed_by == "user-standing-mandate/automated-qa" and item.audio_mode == "music_only"
        if item.audio_mode == "music_only" and not mandate_audio:
            blockers.append("music-only audio is not narration and requires explicit creative review")
        if item.status == "queued" and item.creative_approval_state != "approved":
            blockers.append("queued item is not approved for YouTube use")
        if blockers:
            findings.append({
                "package_id": item.package_id,
                "content_id": item.content_id,
                "status": item.status,
                "creative_approval_state": item.creative_approval_state,
                "audio_mode": item.audio_mode,
                "source_url": item.source_url,
                "blockers": tuple(dict.fromkeys(blockers)),
            })
    return {
        "audit_status": "review_required" if findings else "clean",
        "item_count": len(queue.items),
        "items": findings,
    }


def reconcile_handoff_state(verified_content_ids: set[str], queue_path: Path = DEFAULT_QUEUE) -> int:
    """Synchronize local handoff claims with the publisher reconciliation result."""
    queue = load_handoff(queue_path)
    changed = tuple(
        item.model_copy(update={"status": "ambiguous"}) if item.status == "uploaded" and item.content_id not in verified_content_ids else item
        for item in queue.items
    )
    count = sum(before.status != after.status for before, after in zip(queue.items, changed, strict=True))
    if count:
        write_handoff(queue_path, queue.model_copy(update={"items": changed}))
    return count


def approve_handoff_item(
    package_id: str,
    queue_path: Path = DEFAULT_QUEUE,
    *,
    now: datetime | None = None,
    engine: Engine | None = None,
    confirm_reviewed: bool = False,
    reviewed_by: str | None = None,
    review_note: str | None = None,
) -> ShortHandoffItem:
    """Approve exactly one rendered Short after the operator reviews its frames."""
    if not confirm_reviewed:
        raise ValueError("creative approval requires explicit confirm_reviewed acknowledgement")
    queue = load_handoff(queue_path)
    item = next((candidate for candidate in queue.items if candidate.package_id == package_id), None)
    if item is None:
        raise KeyError(package_id)
    blockers = _handoff_blockers(item, engine=engine)
    if blockers:
        raise ValueError("creative approval blocked: " + "; ".join(blockers))
    approved = item.model_copy(update={
        "creative_approval_state": "approved",
        "creative_approval_video_checksum": item.video_checksum,
        "creative_approved_at": (now or datetime.now(UTC)).isoformat(),
        "creative_reviewed_by": (reviewed_by or "operator").strip() or "operator",
        "creative_review_note": (review_note or "Human creative review confirmed.").strip(),
    })
    write_handoff(queue_path, queue.model_copy(update={"items": tuple(approved if candidate.package_id == package_id else candidate for candidate in queue.items)}))
    return approved


def revoke_handoff_approval(package_id: str, queue_path: Path = DEFAULT_QUEUE) -> ShortHandoffItem:
    queue = load_handoff(queue_path)
    item = next((candidate for candidate in queue.items if candidate.package_id == package_id), None)
    if item is None:
        raise KeyError(package_id)
    revoked = item.model_copy(update={"creative_approval_state": "pending_review", "creative_approval_video_checksum": None, "creative_approved_at": None})
    write_handoff(queue_path, queue.model_copy(update={"items": tuple(revoked if candidate.package_id == package_id else candidate for candidate in queue.items)}))
    return revoked


def autonomous_youtube_cap_available(path: Path = DEFAULT_CAP_STATE, *, now: datetime | None = None) -> bool:
    return _load_cap(path, now or datetime.now(UTC)).available


def record_autonomous_youtube_success(path: Path = DEFAULT_CAP_STATE, *, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    with _daily_cap_lock(path):
        cap = _load_cap(path, current)
        _save_cap(path, DailyCap(cap.date, cap.successful_publications + 1))


def _description(package: ContentPackage, public_base_url: str = "https://gamcryp.com", audio_mode: str = "music_only") -> str:
    facts = "\n\n".join(str(point["text"]) for point in package.factual_talking_points if point.get("text"))
    description = f"{package.hook}\n\n{facts}\n\n{package.cta}"
    if is_motion_graphic_explainer(package):
        landing = f"{public_base_url.rstrip('/')}{package.canonical_source_url}"
        tracking = urlencode({
            "utm_source": "youtube",
            "utm_medium": "short",
            "utm_campaign": "site_explainer" if is_site_explainer(package) else "catalog_guide",
            "utm_content": package.content_family.lower(),
        })
        description += f"\n\nExplore the source and methodology: {landing}?{tracking}"
        if audio_mode == "music_only":
            description += (
                "\n\nMusic: \"Inspired\" Kevin MacLeod (incompetech.com)"
                "\nLicensed under Creative Commons: By Attribution 4.0 License"
                "\nhttps://creativecommons.org/licenses/by/4.0/"
                "\nEdited for video duration with trimming/looping and fades. All guidance is on-screen; there is no spoken narration."
            )
        else:
            description += "\n\nAll guidance is on-screen and no spoken narration is included."
        description += "\nAnalytics only. No guaranteed returns. Not investment advice.\n\n#GamCryp #Web3 #GameFi"
        if not is_site_explainer(package):
            source_links = "\n".join(f"{reference.get('label', 'Official source')}: {reference['url']}" for reference in package.required_source_references if str(reference.get("url", "")).startswith("https://"))
            if source_links:
                description += f"\n\nOfficial references:\n{source_links}"
    return description[:5000]


def package_family(package_id: str) -> str:
    parts = package_id.split("-")
    return parts[2] if len(parts) > 2 else "unknown"


def package_opportunity(package_id: str) -> str:
    parts = package_id.split("-", 3)
    return parts[3] if len(parts) > 3 else package_id


def _handoff_blockers(item: ShortHandoffItem, *, engine: Engine | None = None) -> tuple[str, ...]:
    blockers: list[str] = []
    if item.format != "SHORT_FORM":
        blockers.append("only SHORT_FORM assets may enter this handoff")
    if item.readiness != "GREEN":
        blockers.append("handoff item is not GREEN")
    if item.audio_mode == "music_only":
        if item.narration_provider != "local_music":
            blockers.append("non-TTS music audio provenance is invalid")
    elif item.audio_mode == "human":
        if item.narration_provider != "human":
            blockers.append("human narration provenance is invalid")
    elif item.audio_mode == "neural_voice":
        if item.narration_provider != "elevenlabs":
            blockers.append("reused neural narration provenance is invalid")
        if not item.narration_reused:
            blockers.append("new TTS narration is forbidden for autonomous Shorts")
    else:
        blockers.append("audio mode is missing or unsupported")
    for label, value in (("video", item.video_path), ("captions", item.caption_path), ("narration", item.narration_path)):
        if not Path(value).is_file():
            blockers.append(f"{label} asset is missing")
    if Path(item.video_path).is_file() and hashlib.sha256(Path(item.video_path).read_bytes()).hexdigest() != item.video_checksum:
        blockers.append("video checksum does not match handoff metadata")
    if Path(item.video_path).is_file() and any(candidate.package_id == item.package_id for candidate in build_content_packages(engine=engine)):
        qa = frame_qa(Path(item.video_path), Path("data/local/video_render/qa") / item.package_id)
        if qa.get("status") != "PASSED":
            blockers.append("BLOCKED_VISUAL_QA: representative frame extraction failed")
        quality = _load_render_quality_metadata(item)
        if quality is None:
            blockers.append("BLOCKED_VISUAL_QA: persisted creative quality metadata is missing")
        else:
            blockers.extend(short_quality_blockers(quality))
    return tuple(blockers)


def _standing_policy_allows(package: ContentPackage, item: ShortHandoffItem, channel_handle: str) -> bool:
    """Apply the user's explicit mandate to site and active catalog explainers.

    The private policy record is local and ignored by Git. Its narrow allowlist
    does not approve opportunity-specific financial or promotional content.
    """
    if not is_motion_graphic_explainer(package) or item.audio_mode != "music_only":
        return False
    if item.audio_mode == "neural_voice" or item.readiness != "GREEN" or item.status != "queued":
        return False
    try:
        current_checksum = hashlib.sha256(Path(item.video_path).read_bytes()).hexdigest()
    except OSError:
        return False
    if item.video_checksum != current_checksum:
        return False
    path = DEFAULT_STANDING_POLICY
    allowed_families = SITE_EXPLAINER_FAMILIES | AUTONOMOUS_CATALOG_FAMILIES
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        policy.get("policy_id") == STANDING_POLICY_ID
        and policy.get("status") == "active"
        and policy.get("channel_handle") == channel_handle == "@GamCryp"
        and policy.get("visibility") == "public"
        and policy.get("max_public_shorts_per_local_day") == 1
        and policy.get("audio_mode") == "music_only"
        and policy.get("tts_allowed") is False
        and set(policy.get("allowed_content_families", ())) == allowed_families
        and package.content_family in allowed_families
        and (is_site_explainer(package) or _active_official_catalog_package(package))
        and item.source_url.startswith("https://gamcryp.com/")
        and bool(policy.get("authorized_at"))
    )


def _active_official_catalog_package(package: ContentPackage) -> bool:
    if package.content_family not in AUTONOMOUS_CATALOG_FAMILIES or not package.opportunity_id:
        return False
    from app.strategies.catalog import get_opportunity
    opportunity = get_opportunity(package.opportunity_id)
    return bool(opportunity and opportunity.status == "active" and package.required_source_references and all(str(ref.get("url", "")).startswith("https://") for ref in package.required_source_references))


def _load_render_quality_metadata(item: ShortHandoffItem) -> dict[str, Any] | None:
    video = Path(item.video_path)
    candidates = (
        video.parent.parent / "metadata" / f"{item.package_id}.json",
        video.parent.parent.parent / "metadata" / f"{item.package_id}.json",
    )
    for metadata in candidates:
        try:
            payload = json.loads(metadata.read_text(encoding="utf-8"))
            if item.audio_mode == "music_only" and payload.get("music_source_sha256") != music_bed_source_fingerprint():
                return None
            checksums = payload.get("asset_checksums", {})
            for label, path in (("video", item.video_path), ("audio", item.narration_path), ("captions", item.caption_path)):
                if checksums.get(label) != hashlib.sha256(Path(path).read_bytes()).hexdigest():
                    return None
            quality = payload.get("quality_metadata")
            if isinstance(quality, dict):
                return quality
        except (OSError, ValueError, TypeError):
            continue
    return None


def _stored_render_creative_ready(item: ShortHandoffItem, package: ContentPackage | None = None) -> bool:
    """Require new editorial metadata before reusing an old MP4."""
    video = Path(item.video_path)
    metadata = video.parent.parent / "metadata" / f"{item.package_id}.json"
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        quality = payload.get("quality_metadata") or {}
    except (OSError, ValueError, TypeError):
        return False
    if item.audio_mode == "music_only" and payload.get("music_source_sha256") != music_bed_source_fingerprint():
        return False
    if package is not None:
        stored_product_paths = tuple((quality.get("asset_plan") or {}).get("product_visual_paths") or ())
        current_product_paths = tuple(asset_plan(package).product_visual_paths)
        stored_source_paths = tuple((quality.get("asset_plan") or {}).get("source_media_paths") or ())
        current_source_paths = tuple(asset_plan(package).source_media_paths)
        if stored_product_paths != current_product_paths or stored_source_paths != current_source_paths:
            return False
    source_count = int(quality.get("source_media_count", 0))
    product_count = int(quality.get("product_visual_count", 0))
    common_ready = (
        quality.get("creative_status") == "CREATIVE_QA_PASSED"
        and quality.get("hook_qa", {}).get("status") == "PASSED"
        and quality.get("gamcryp_product_placement") is True
        and quality.get("brand_closing_present") is True
    )
    if quality.get("site_explainer") is True and package is not None and is_motion_graphic_explainer(package):
        logo = Path(str(quality.get("site_brand_logo_path") or ""))
        try:
            logo_matches = logo.is_file() and hashlib.sha256(logo.read_bytes()).hexdigest() == quality.get("site_brand_logo_sha256")
        except OSError:
            logo_matches = False
        return (
            common_ready
            and quality.get("render_engine") == "remotion"
            and quality.get("quality_version") == "short-social-remotion-site-explainer-v1"
            and quality.get("site_visual_mode") == "original_evidence_led_motion_graphics"
            and quality.get("product_visual_motion") == "site_motion_infographic"
            and logo_matches
        )
    return (
        common_ready
        and max(source_count, product_count) >= 1
        and quality.get("product_visual_motion") in {"ken_burns_crop_and_scanline", "official_video_or_ken_burns_capture", "official_video_or_animated_source_capture"}
    )


def _load_cap(path: Path, now: datetime) -> DailyCap:
    local_date = _local_date(now)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("date") == local_date:
            return DailyCap(local_date, int(payload.get("successful_publications", 0)))
    except (OSError, ValueError, TypeError):
        pass
    return DailyCap(local_date, 0)


@contextmanager
def _daily_cap_lock(cap_path: Path):
    """Cross-platform process lock for the one-public-Short daily cap."""
    lock_path = cap_path.with_name(f"{cap_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 30
    while True:
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode("ascii", errors="ignore"))
            os.close(descriptor)
            break
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 6 * 60 * 60:
                    lock_path.unlink()
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("timed out waiting for the YouTube daily-cap lock")
            time.sleep(0.1)
    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _save_cap(path: Path, cap: DailyCap) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "date": cap.date, "successful_publications": cap.successful_publications}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _local_date(now: datetime) -> str:
    timezone_name = os.getenv("GAMEFI_LOCAL_TIMEZONE", "Europe/Istanbul")
    return now.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _replace_item(path: Path, queue: ShortHandoffQueue, old: ShortHandoffItem) -> None:
    updated = tuple(item.model_copy(update={"status": "uploaded"}) if item.package_id == old.package_id else item for item in queue.items)
    write_handoff(path, queue.model_copy(update={"items": updated}))
