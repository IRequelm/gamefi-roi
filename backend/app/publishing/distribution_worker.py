"""Small restart-safe worker for eligible distribution queue items."""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from app.distribution.manual_outbox import XManualOutbox, manual_ready_record
from app.distribution.x_email_notify import XAmplificationEmailNotifier, XEmailConfig, XEmailNotificationError, XManualEmailNotifier
from app.distribution.x_amplification import (
    DEFAULT_FEED,
    DEFAULT_HISTORY,
    DEFAULT_OUTBOX,
    DEFAULT_WHITELIST,
    XAmplificationOutbox,
    classify_candidate,
    load_feed,
    load_whitelist,
)
from app.distribution.x_intelligence import XIntelligenceCollector, intelligence_is_live_and_fresh
from app.distribution.x_publisher import XApiError, XAuthError, XAmbiguousApiError, XPublisherConfig, XPublisherError, XPublishingService
from app.distribution.refill import DistributionRefillConfig, DistributionRefiller
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.publishing.youtube_distribution import YouTubeDistributionConfig, YouTubeDistributionPublisher
from app.config.settings import get_settings
from app.publishing.short_youtube_handoff import (
    DEFAULT_CAP_STATE,
    DEFAULT_QUEUE,
    autonomous_youtube_cap_available,
    load_handoff,
    prepare_short_handoff,
    publish_next as publish_next_short_handoff,
    record_autonomous_youtube_success,
)

logger = logging.getLogger("gamcryp.distribution_worker")


@dataclass(frozen=True)
class DistributionWorkerConfig:
    live: bool = False
    x_publishing_mode: str = "dry_run"
    video_directory: Path = Path("data/local/youtube/videos")
    thumbnail_directory: Path | None = None
    state_file: Path = Path("data/local/distribution/worker_state.json")
    heartbeat_file: Path = Path("data/local/distribution/worker_heartbeat.json")
    failure_cooldown_seconds: int = 1800
    manual_outbox_file: Path = Path("distribution/manual_outbox/x_manual_ready.json")
    short_handoff_file: Path = DEFAULT_QUEUE
    autonomous_cap_file: Path = DEFAULT_CAP_STATE
    short_handoff_refill_enabled: bool = False
    x_amplification_feed_file: Path = DEFAULT_FEED
    x_amplification_whitelist_file: Path = DEFAULT_WHITELIST
    x_amplification_outbox_file: Path = DEFAULT_OUTBOX
    x_amplification_history_file: Path = DEFAULT_HISTORY
    x_intelligence_state_file: Path = Path("data/local/x/intelligence_state.json")
    x_amplification_min_engagement_score: int = 10
    x_amplification_auto_repost: bool = False

    @classmethod
    def from_environment(cls) -> "DistributionWorkerConfig":
        thumbnail = os.getenv("GAMEFI_DISTRIBUTION_THUMBNAIL_DIR", "").strip()
        live = os.getenv("GAMEFI_DISTRIBUTION_LIVE", "false").strip().lower() in {"1", "true", "yes"}
        return cls(
            live=live,
            x_publishing_mode=os.getenv("GAMEFI_X_PUBLISHING_MODE", "dry_run").strip().lower(),
            video_directory=Path(os.getenv("GAMEFI_DISTRIBUTION_VIDEO_DIR", "data/local/youtube/videos")),
            thumbnail_directory=Path(thumbnail) if thumbnail else None,
            state_file=Path(os.getenv("GAMEFI_DISTRIBUTION_WORKER_STATE_FILE", "data/local/distribution/worker_state.json")),
            heartbeat_file=Path(os.getenv("GAMEFI_DISTRIBUTION_HEARTBEAT_FILE", "data/local/distribution/worker_heartbeat.json")),
            failure_cooldown_seconds=int(os.getenv("GAMEFI_DISTRIBUTION_FAILURE_COOLDOWN_SECONDS", "1800")),
            manual_outbox_file=Path(os.getenv("GAMEFI_MANUAL_X_OUTBOX_FILE", "distribution/manual_outbox/x_manual_ready.json")),
            short_handoff_file=Path(os.getenv("GAMEFI_SHORT_YOUTUBE_HANDOFF_FILE", str(DEFAULT_QUEUE))),
            autonomous_cap_file=Path(os.getenv("GAMEFI_YOUTUBE_AUTONOMOUS_CAP_FILE", str(DEFAULT_CAP_STATE))),
            short_handoff_refill_enabled=os.getenv("GAMEFI_SHORT_YOUTUBE_HANDOFF_REFILL_ENABLED", "true" if live else "false").strip().lower() in {"1", "true", "yes"},
            x_amplification_feed_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_FEED_FILE", str(DEFAULT_FEED))),
            x_amplification_whitelist_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_WHITELIST_FILE", str(DEFAULT_WHITELIST))),
            x_amplification_outbox_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_OUTBOX_FILE", str(DEFAULT_OUTBOX))),
            x_amplification_history_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_HISTORY_FILE", str(DEFAULT_HISTORY))),
            x_intelligence_state_file=Path(os.getenv("GAMEFI_X_INTELLIGENCE_STATE_FILE", "data/local/x/intelligence_state.json")),
            x_amplification_min_engagement_score=max(0, int(os.getenv("GAMEFI_X_AMPLIFICATION_MIN_ENGAGEMENT", "10"))),
            x_amplification_auto_repost=os.getenv("GAMEFI_X_AMPLIFICATION_AUTO_REPOST", "false").strip().lower() in {"1", "true", "yes"},
        )


class WorkerState:
    """Persists cooldowns so a failed item is not retried every loop or after restart."""

    def __init__(self, path: Path):
        self.path = path
        self.records: dict[str, dict[str, str]] = {}
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and isinstance(payload.get("records"), dict):
                    self.records = payload["records"]
            except (OSError, json.JSONDecodeError):
                logger.warning("worker_state_unreadable path=%s", path)

    def blocked(self, key: str, *, now: datetime) -> bool:
        if self.records.get(key, {}).get("dead_letter"):
            return True
        value = self.records.get(key, {}).get("retry_after")
        if not value:
            return False
        try:
            return datetime.fromisoformat(value) > now
        except ValueError:
            return False

    def record_failure(self, key: str, *, error_category: str, now: datetime, cooldown_seconds: int) -> None:
        attempts = int(self.records.get(key, {}).get("attempts", 0)) + 1
        self.records[key] = {
            "attempts": attempts,
            "dead_letter": attempts >= 3,
            "error_category": error_category,
            "last_attempt_at": now.isoformat(),
            "retry_after": (now + timedelta(seconds=cooldown_seconds)).isoformat(),
        }
        self._save()

    def record_success(self, key: str) -> None:
        if key in self.records:
            self.records.pop(key, None)
            self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"state_version": "distribution-worker-v1", "records": self.records}, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class DistributionWorker:
    def __init__(
        self,
        *,
        config: DistributionWorkerConfig | None = None,
        x_service: XPublishingService | None = None,
        youtube_distribution: YouTubeDistributionPublisher | None = None,
        refiller: DistributionRefiller | None = None,
        x_intelligence: XIntelligenceCollector | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.config = config or DistributionWorkerConfig.from_environment()
        self.x_service = x_service or XPublishingService(XPublisherConfig.from_environment())
        self.youtube_distribution = youtube_distribution or _youtube_distribution_from_environment()
        self.refiller = refiller or DistributionRefiller(DistributionRefillConfig.from_environment())
        self.now = now
        self.state = WorkerState(self.config.state_file)
        self.manual_outbox = XManualOutbox(Path(os.getenv("GAMEFI_MANUAL_X_OUTBOX_FILE", str(self.config.manual_outbox_file))))
        self.x_email_notifier = XManualEmailNotifier(XEmailConfig.from_environment())
        self.x_amplification_email_notifier = XAmplificationEmailNotifier(XEmailConfig.from_environment())
        self.x_intelligence = x_intelligence or XIntelligenceCollector(service=self.x_service)

    def run_once(self) -> list[dict[str, Any]]:
        now = self.now()
        results = []
        self._write_heartbeat(status="running", now=now, results=results)
        try:
            refill_result = self.refiller.run(now=now)
            if refill_result.get("status") != "disabled":
                results.append(refill_result)
        except Exception as exc:
            logger.error("distribution_refill_failed category=%s", type(exc).__name__)
            results.append({"platform": "distribution", "status": "refill_failed", "error_category": type(exc).__name__})
        results.append(self._process_x(now))
        amplification_result = self._process_x_amplification(now)
        if amplification_result.get("status") != "idle":
            results.append(amplification_result)
        # The legacy Content Pack queue remains available for explicit
        # operator/CLI use. Autonomous publishing uses only the Short handoff,
        # which carries the current render, narration, and creative QA proof.
        results.append({"platform": "YouTubeLegacyQueue", "status": "disabled_for_autonomous_worker"})
        results.append(self._process_short_handoff(now))
        degraded = any(item.get("status") in {"failed", "refill_failed", "not_ready", "blocked", "dead_letter"} for item in results)
        self._write_heartbeat(status="degraded" if degraded else "ok", now=self.now(), results=results)
        return results

    def run_forever(self, *, interval_seconds: int = 1800) -> None:
        if interval_seconds < 60:
            raise ValueError("worker interval must be at least 60 seconds")
        while True:
            try:
                self.run_once()
            except Exception as exc:  # Keep the long-lived scheduler alive after an unexpected cycle failure.
                now = self.now()
                logger.exception("distribution_cycle_failed category=%s", type(exc).__name__)
                self._write_heartbeat(status="failed", now=now, results=[], error_category=type(exc).__name__)
            time.sleep(interval_seconds)

    def _write_heartbeat(
        self,
        *,
        status: str,
        now: datetime,
        results: list[dict[str, Any]],
        error_category: str | None = None,
    ) -> None:
        payload = {
            "version": 1,
            "status": status,
            "pid": os.getpid(),
            "updated_at": now.astimezone(UTC).isoformat(),
            "platform_statuses": [
                {"platform": item.get("platform"), "status": item.get("status")}
                for item in results
            ],
        }
        if error_category:
            payload["error_category"] = error_category
        path = self.config.heartbeat_file
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _process_x(self, now: datetime) -> dict[str, Any]:
        if self.config.x_publishing_mode == "disabled":
            return {"platform": "X", "status": "disabled"}
        summary = self.x_service.queue_summary()
        candidates = summary.get("publishable", [])
        if not candidates:
            return {"platform": "X", "status": "idle", "detail": "no GREEN queue item"}
        saw_cooldown = False
        for raw_content_id in candidates:
            content_id = str(raw_content_id)
            key = f"X:{content_id}"
            preview = None
            try:
                preview = self.x_service.preview(content_id)
                key = f"X:{content_id}:{preview.content_checksum}"
                if self.config.x_publishing_mode == "manual":
                    record = manual_ready_record(
                        content_id=content_id,
                        post_text=preview.exact_final_copy,
                        source_url=preview.attribution_url,
                        checksum=preview.content_checksum,
                        now=now,
                        official_handle=getattr(preview, "official_handle", None),
                        hashtags=getattr(preview, "hashtags", ()),
                        media_path=getattr(preview, "media_path", None),
                        media_kind=getattr(preview, "media_kind", None),
                        media_source=getattr(preview, "media_source", None),
                        enrichment_fingerprint=getattr(preview, "enrichment_fingerprint", None),
                    )
                    outbox_status = self.manual_outbox.prepare(record)
                    try:
                        email_status = self.x_email_notifier.notify_if_needed(self.manual_outbox.current())
                    except XEmailNotificationError as exc:
                        logger.error("manual_x_email_failed category=%s", type(exc).__name__)
                        email_status = "failed"
                    return {"platform": "X", "content_id": content_id, "status": "manual_ready", "outbox": outbox_status, "email": email_status}
                if self.state.blocked(key, now=now) or self.state.blocked(f"X:{content_id}", now=now):
                    saw_cooldown = True
                    continue
                result = self.x_service.publish(content_id, dry_run=not self.config.live, confirm_publish=self.config.live)
                self.state.record_success(key)
                return {"platform": "X", "content_id": content_id, "status": "published" if self.config.live else "dry_run", "result": result.model_dump(mode="json")}
            except (XAuthError, XApiError) as exc:
                if not isinstance(exc, XAmbiguousApiError) and preview is not None and preview.would_publish:
                    outbox_status = self.manual_outbox.prepare(
                        manual_ready_record(
                            content_id=content_id,
                            post_text=preview.exact_final_copy,
                            source_url=preview.attribution_url,
                            checksum=preview.content_checksum,
                            now=now,
                            official_handle=getattr(preview, "official_handle", None),
                            hashtags=getattr(preview, "hashtags", ()),
                            media_path=getattr(preview, "media_path", None),
                            media_kind=getattr(preview, "media_kind", None),
                            media_source=getattr(preview, "media_source", None),
                            enrichment_fingerprint=getattr(preview, "enrichment_fingerprint", None),
                        )
                    )
                else:
                    outbox_status = None
                self._record_x_failure(key, content_id, type(exc).__name__, now)
                logger.error("distribution_publish_failed platform=X content_id=%s category=%s", content_id, type(exc).__name__)
                return {"platform": "X", "content_id": content_id, "status": "manual_ready" if outbox_status else "failed", "error_category": type(exc).__name__, "outbox": outbox_status}
            except Exception as exc:  # Publisher classifies and persists the failure; worker must continue.
                self._record_x_failure(key, content_id, type(exc).__name__, now)
                logger.error("distribution_publish_failed platform=X content_id=%s category=%s", content_id, type(exc).__name__)
                return {"platform": "X", "content_id": content_id, "status": "failed", "error_category": type(exc).__name__}
        if saw_cooldown:
            return {"platform": "X", "status": "cooldown"}
        return {"platform": "X", "status": "idle", "detail": "no unblocked GREEN queue item"}

    def _process_x_amplification(self, now: datetime) -> dict[str, Any]:
        """Collect X signals and optionally retweet only high-confidence candidates."""
        try:
            live_x = self.config.live and self.config.x_publishing_mode == "live"
            if live_x:
                intelligence = self.x_intelligence.collect(now=now)
                if intelligence.get("status") != "LIVE" or not intelligence_is_live_and_fresh(
                    self.config.x_intelligence_state_file,
                    now=now,
                    max_age_hours=self.x_intelligence.config.freshness_hours,
                ):
                    return {
                        "platform": "XAmplification",
                        "status": "blocked",
                        "detail": intelligence.get("limitation") or "live X intelligence is unavailable",
                    }
            posts = load_feed(self.config.x_amplification_feed_file)
            if not posts:
                return {"platform": "XAmplification", "status": "idle", "detail": "no approved signal feed"}
            whitelist = load_whitelist(self.config.x_amplification_whitelist_file)
            candidates = [
                classify_candidate(
                    post,
                    whitelist,
                    now=now,
                    min_engagement_score=self.config.x_amplification_min_engagement_score if live_x else 0,
                )
                for post in posts
            ]
            outbox = XAmplificationOutbox(self.config.x_amplification_outbox_file, self.config.x_amplification_history_file)
            status = outbox.write(candidates)
            reposted = 0
            if live_x and self.config.x_amplification_auto_repost:
                user_payload = self.x_service.api_client.authenticated_user()
                user_id = str((user_payload.get("data") or {}).get("id") or "")
                if not user_id:
                    raise XAuthError("X authenticated-user response did not contain a user id")
                for candidate in candidates:
                    if candidate.decision.value != "REPOST_NOW":
                        continue
                    if outbox.is_handled(candidate.fingerprint):
                        continue
                    key = f"XRetweet:{candidate.fingerprint}"
                    if self.state.blocked(key, now=now):
                        continue
                    repost_id = self.x_service.api_client.create_retweet(user_id, candidate.post_id)
                    outbox.mark_handled(candidate.fingerprint, repost_id=repost_id, status="published", now=now)
                    self.state.record_success(key)
                    reposted += 1
            try:
                email_status = self.x_amplification_email_notifier.notify_if_needed(outbox)
            except XEmailNotificationError as exc:
                logger.error("x_amplification_email_failed category=%s", type(exc).__name__)
                email_status = "failed"
            return {"platform": "XAmplification", "status": "reposted" if reposted else status, "actionable": len(outbox.current()), "reposted": reposted, "email": email_status}
        except Exception as exc:
            logger.error("x_amplification_failed category=%s", type(exc).__name__)
            return {"platform": "XAmplification", "status": "failed", "error_category": type(exc).__name__}

    def _record_x_failure(self, key: str, content_id: str, category: str, now: datetime) -> None:
        self.state.record_failure(key, error_category=category, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
        if key != f"X:{content_id}":
            self.state.record_failure(f"X:{content_id}", error_category=category, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)

    def _process_youtube(self, now: datetime) -> list[dict[str, Any]]:
        summary = self.youtube_distribution.queue_summary()
        results = []
        cap_available = autonomous_youtube_cap_available(self.config.autonomous_cap_file, now=now)
        for content_id in summary.get("publishable", []):
            if self.config.live and not cap_available:
                results.append({"platform": "YouTube", "content_id": content_id, "status": "daily_cap"})
                continue
            key = f"YouTube:{content_id}"
            video_path = _find_asset(self.config.video_directory, content_id, (".mp4", ".mov", ".m4v", ".webm"))
            thumbnail_path = _find_asset(self.config.thumbnail_directory, content_id, (".jpg", ".jpeg", ".png")) if self.config.thumbnail_directory else None
            if video_path is None:
                results.append({"platform": "YouTube", "content_id": content_id, "status": "blocked", "detail": "video asset is missing"})
                continue
            try:
                preview = self.youtube_distribution.preview(content_id, video_path=video_path, thumbnail_path=thumbnail_path)
                key = f"YouTube:{content_id}:{preview.package_checksum}:{video_path.name}"
                if self.state.blocked(key, now=now):
                    results.append({"platform": "YouTube", "content_id": content_id, "status": "cooldown"})
                    continue
                operation = self.youtube_distribution.upload(content_id, video_path=video_path, thumbnail_path=thumbnail_path, confirm_publish=self.config.live) if self.config.live else self.youtube_distribution.dry_run(content_id, video_path=video_path, thumbnail_path=thumbnail_path)
                self.state.record_success(key)
                if self.config.live and getattr(operation, "status", None) == "uploaded":
                    record_autonomous_youtube_success(self.config.autonomous_cap_file, now=now)
                    cap_available = False
                results.append({"platform": "YouTube", "content_id": content_id, "status": "published" if self.config.live else "dry_run", "result": operation.to_safe_dict()})
            except Exception as exc:
                category = type(exc).__name__
                self.state.record_failure(key, error_category=category, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
                logger.error("distribution_publish_failed platform=YouTube content_id=%s category=%s", content_id, category)
                results.append({"platform": "YouTube", "content_id": content_id, "status": "failed", "error_category": category})
        if not results:
            results.append({"platform": "YouTube", "status": "idle", "detail": "no GREEN queue item"})
        return results

    def _process_short_handoff(self, now: datetime) -> dict[str, Any]:
        key = "YouTubeShortHandoff"
        if self.state.blocked(key, now=now):
            return {"platform": key, "status": "dead_letter" if self.state.records[key].get("dead_letter") else "cooldown"}
        try:
            queue = load_handoff(self.config.short_handoff_file)
            queued = sum(item.status == "queued" and item.readiness == "GREEN" for item in queue.items)
            if self.config.short_handoff_refill_enabled and queued < queue.buffer_target:
                prepare_short_handoff(
                    settings=get_settings(),
                    queue_path=self.config.short_handoff_file,
                    limit=queue.buffer_target,
                )
            if not self.config.short_handoff_file.is_file():
                return {"platform": "YouTubeShortHandoff", "status": "idle", "detail": "handoff queue is empty"}
            result = publish_next_short_handoff(
                publisher=self.youtube_distribution.publisher,
                queue_path=self.config.short_handoff_file,
                cap_path=self.config.autonomous_cap_file,
                now=now,
                live=self.config.live,
            )
            if result.get("status") == "not_ready":
                self.state.record_failure(key, error_category="BLOCKED_VISUAL_QA", now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
            else:
                self.state.record_success(key)
            return {"platform": "YouTubeShortHandoff", **result}
        except Exception as exc:
            self.state.record_failure(key, error_category=type(exc).__name__, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
            logger.error("short_youtube_handoff_failed category=%s", type(exc).__name__)
            return {"platform": "YouTubeShortHandoff", "status": "failed", "error_category": type(exc).__name__}


def _find_asset(directory: Path | None, content_id: str, extensions: tuple[str, ...]) -> Path | None:
    if directory is None:
        return None
    for extension in extensions:
        candidate = directory / f"{content_id}{extension}"
        if candidate.is_file():
            return candidate
    return None


def _youtube_distribution_from_environment() -> YouTubeDistributionPublisher:
    publisher = YouTubePublisher(
        config=YouTubePublisherConfig(
            client_secrets_file=_optional_path("GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE"),
            token_file=_optional_path("GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE"),
            state_file=Path(os.getenv("GAMEFI_YOUTUBE_PUBLISH_STATE_FILE", "data/local/youtube/publish_state.json")),
            channel_handle=os.getenv("GAMEFI_YOUTUBE_CHANNEL_HANDLE", "@GamCryp"),
            max_retries=int(os.getenv("GAMEFI_YOUTUBE_MAX_RETRIES", "2")),
        )
    )
    return YouTubeDistributionPublisher(
        publisher,
        config=YouTubeDistributionConfig(
            content_pack_file=Path(os.getenv("GAMEFI_YOUTUBE_CONTENT_PACK_FILE", "distribution/content_packs/learning_batch_001.json")),
            queue_file=Path(os.getenv("GAMEFI_YOUTUBE_QUEUE_FILE", "distribution/publish_queue/youtube_publish_queue.json")),
            approval_file=Path(os.getenv("GAMEFI_YOUTUBE_APPROVAL_FILE", "data/local/youtube/approvals.json")),
        ),
    )


def _optional_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value) if value else None


def main(argv: list[str] | None = None) -> int:
    # Task Scheduler launches without a shell profile; load the existing local
    # .env convention before reading worker flags. Explicit process variables
    # still take precedence.
    load_dotenv(override=False, encoding="utf-8-sig")
    parser = argparse.ArgumentParser(description="Run the fail-closed GamCryp distribution worker.")
    parser.add_argument("--once", action="store_true", help="Process one interval and exit.")
    parser.add_argument("--interval-seconds", type=int, default=1800)
    subcommands = parser.add_subparsers(dest="command")
    confirm = subcommands.add_parser("x-manual-confirm", help="Confirm the current manually published X outbox item.")
    confirm.add_argument("content_id")
    amp_confirm = subcommands.add_parser("x-amplification-confirm", help="Mark a manually handled amplification candidate; this never publishes to X.")
    amp_confirm.add_argument("fingerprint")
    amp_confirm.add_argument("--repost-id", default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=os.getenv("GAMEFI_DISTRIBUTION_LOG_LEVEL", "INFO"))
    if args.command == "x-manual-confirm":
        try:
            config = DistributionWorkerConfig.from_environment()
            service = XPublishingService(XPublisherConfig.from_environment())
            outbox = XManualOutbox(Path(os.getenv("GAMEFI_MANUAL_X_OUTBOX_FILE", str(config.manual_outbox_file))))
            record = outbox.current()
            if record is None or record.published or record.content_id != args.content_id:
                raise XPublisherError("current manual-ready outbox item does not match content_id")
            service.confirm_manual_publication(args.content_id, checksum=record.checksum)
            outbox.clear(content_id=record.content_id, checksum=record.checksum)
            print(json.dumps({"content_id": record.content_id, "status": "manual_confirmed", "published": True}))
            return 0
        except (XPublisherError, OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "error", "error": str(exc)}))
            return 1
    if args.command == "x-amplification-confirm":
        from app.distribution.x_amplification import XAmplificationOutbox
        config = DistributionWorkerConfig.from_environment()
        outbox = XAmplificationOutbox(config.x_amplification_outbox_file, config.x_amplification_history_file)
        if not any(item.fingerprint == args.fingerprint for item in outbox.current()):
            print(json.dumps({"status": "error", "error": "amplification fingerprint is not pending"}))
            return 1
        outbox.mark_handled(args.fingerprint, repost_id=args.repost_id, status="manual_handled")
        print(json.dumps({"fingerprint": args.fingerprint, "status": "amplification_manual_confirmed", "published": False}))
        return 0
    worker = DistributionWorker()
    if args.once:
        print(json.dumps(worker.run_once(), indent=2, sort_keys=True))
    else:
        worker.run_forever(interval_seconds=args.interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
