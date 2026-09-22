"""Small restart-safe worker for eligible distribution queue items."""

from __future__ import annotations

import argparse
import contextlib
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
from app.distribution.x_intelligence import XIntelligenceCollector, intelligence_is_live_and_fresh, load_intelligence_state
from app.distribution.x_publisher import XApiError, XAuthError, XAmbiguousApiError, XPublisherConfig, XPublisherError, XPublishingService
from app.distribution.refill import DistributionRefillConfig, DistributionRefiller
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.publishing.youtube_distribution import YouTubeDistributionConfig, YouTubeDistributionPublisher
from app.config.settings import get_settings
from app.storage.database import check_connectivity, create_database_engine
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
    lock_file: Path = Path("data/local/distribution/worker.lock")
    failure_cooldown_seconds: int = 1800
    manual_outbox_file: Path = Path("distribution/manual_outbox/x_manual_ready.json")
    manual_outbox_stale_hours: int = 24
    short_handoff_file: Path = DEFAULT_QUEUE
    autonomous_cap_file: Path = DEFAULT_CAP_STATE
    short_handoff_refill_enabled: bool = False
    short_handoff_refill_batch: int = 1
    x_amplification_feed_file: Path = DEFAULT_FEED
    x_amplification_whitelist_file: Path = DEFAULT_WHITELIST
    x_amplification_outbox_file: Path = DEFAULT_OUTBOX
    x_amplification_history_file: Path = DEFAULT_HISTORY
    x_intelligence_state_file: Path = Path("data/local/x/intelligence_state.json")
    x_intelligence_refresh_hours: int = 6
    x_amplification_min_engagement_score: int = 10
    x_amplification_auto_repost: bool = False
    x_daily_cap_file: Path = Path("data/local/x/daily_cap.json")
    x_daily_post_cap: int = 2
    x_daily_retweet_cap: int = 2

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
            lock_file=Path(os.getenv("GAMEFI_DISTRIBUTION_LOCK_FILE", "data/local/distribution/worker.lock")),
            failure_cooldown_seconds=int(os.getenv("GAMEFI_DISTRIBUTION_FAILURE_COOLDOWN_SECONDS", "1800")),
            manual_outbox_file=Path(os.getenv("GAMEFI_MANUAL_X_OUTBOX_FILE", "distribution/manual_outbox/x_manual_ready.json")),
            manual_outbox_stale_hours=max(1, int(os.getenv("GAMEFI_X_MANUAL_OUTBOX_STALE_HOURS", "24"))),
            short_handoff_file=Path(os.getenv("GAMEFI_SHORT_YOUTUBE_HANDOFF_FILE", str(DEFAULT_QUEUE))),
            autonomous_cap_file=Path(os.getenv("GAMEFI_YOUTUBE_AUTONOMOUS_CAP_FILE", str(DEFAULT_CAP_STATE))),
            short_handoff_refill_enabled=os.getenv("GAMEFI_SHORT_YOUTUBE_HANDOFF_REFILL_ENABLED", "true" if live else "false").strip().lower() in {"1", "true", "yes"},
            short_handoff_refill_batch=max(1, min(int(os.getenv("GAMEFI_SHORT_YOUTUBE_REFILL_BATCH", "1")), 5)),
            x_amplification_feed_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_FEED_FILE", str(DEFAULT_FEED))),
            x_amplification_whitelist_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_WHITELIST_FILE", str(DEFAULT_WHITELIST))),
            x_amplification_outbox_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_OUTBOX_FILE", str(DEFAULT_OUTBOX))),
            x_amplification_history_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_HISTORY_FILE", str(DEFAULT_HISTORY))),
            x_intelligence_state_file=Path(os.getenv("GAMEFI_X_INTELLIGENCE_STATE_FILE", "data/local/x/intelligence_state.json")),
            x_intelligence_refresh_hours=max(1, int(os.getenv("GAMEFI_X_INTELLIGENCE_REFRESH_HOURS", "6"))),
            x_amplification_min_engagement_score=max(0, int(os.getenv("GAMEFI_X_AMPLIFICATION_MIN_ENGAGEMENT", "10"))),
            x_amplification_auto_repost=os.getenv("GAMEFI_X_AMPLIFICATION_AUTO_REPOST", "false").strip().lower() in {"1", "true", "yes"},
            x_daily_cap_file=Path(os.getenv("GAMEFI_X_DAILY_CAP_FILE", "data/local/x/daily_cap.json")),
            x_daily_post_cap=max(0, int(os.getenv("GAMEFI_X_DAILY_POST_CAP", "2"))),
            x_daily_retweet_cap=max(0, int(os.getenv("GAMEFI_X_DAILY_RETWEET_CAP", "2"))),
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


class XDailyCapState:
    """UTC-day persistent caps for autonomous X writes."""

    def __init__(self, path: Path):
        self.path = path
        self.payload = {"date": "", "posts": 0, "retweets": 0}
        if path.is_file():
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(candidate, dict):
                    self.payload.update(candidate)
            except (OSError, json.JSONDecodeError):
                logger.warning("x_daily_cap_unreadable path=%s", path)

    def _normalize(self, now: datetime) -> None:
        today = now.astimezone(UTC).date().isoformat()
        if self.payload.get("date") != today:
            self.payload = {"date": today, "posts": 0, "retweets": 0}

    def available(self, kind: str, limit: int, *, now: datetime) -> bool:
        self._normalize(now)
        return int(self.payload.get(kind, 0)) < limit

    def record(self, kind: str, *, now: datetime) -> None:
        self._normalize(now)
        self.payload[kind] = int(self.payload.get(kind, 0)) + 1
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self.payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


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
        self.x_daily_cap = XDailyCapState(self.config.x_daily_cap_file)
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
        degraded = any(
            item.get("status") in {"failed", "refill_failed", "not_ready", "blocked", "dead_letter"}
            or item.get("catalog_status") == "unavailable"
            for item in results
        )
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
        if self.config.live and not self.x_daily_cap.available("posts", self.config.x_daily_post_cap, now=now):
            return {"platform": "X", "status": "daily_cap", "detail": "daily X post cap reached"}
        saw_cooldown = False
        manual_blockers: list[str] = []
        published_results: list[dict[str, Any]] = []
        for raw_content_id in candidates:
            content_id = str(raw_content_id)
            key = f"X:{content_id}"
            preview = None
            try:
                preview = self.x_service.preview(content_id)
                key = f"X:{content_id}:{preview.content_checksum}"
                if self.config.x_publishing_mode == "manual":
                    if not preview.would_publish:
                        manual_blockers.extend(f"{content_id}: {blocker}" for blocker in preview.blockers)
                        continue
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
                    published_results.append(record)
                    if len(published_results) >= min(2, max(1, self.config.x_daily_post_cap)):
                        break
                    continue
                if self.state.blocked(key, now=now) or self.state.blocked(f"X:{content_id}", now=now):
                    saw_cooldown = True
                    continue
                result = self.x_service.publish(content_id, dry_run=not self.config.live, confirm_publish=self.config.live)
                self.state.record_success(key)
                if self.config.live:
                    self.x_daily_cap.record("posts", now=now)
                    published_results.append({"content_id": content_id, "result": result.model_dump(mode="json")})
                    if not self.x_daily_cap.available("posts", self.config.x_daily_post_cap, now=now):
                        break
                    continue
                return {"platform": "X", "content_id": content_id, "status": "dry_run", "result": result.model_dump(mode="json")}
            except (XAuthError, XApiError) as exc:
                # A live worker must report the provider failure/cooldown; it
                # must not turn a billing/auth outage into a human-review
                # queue. The manual outbox remains available for explicit
                # non-live operator mode only.
                if not self.config.live and not isinstance(exc, XAmbiguousApiError) and preview is not None and preview.would_publish:
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
                        ),
                        now=now,
                        stale_after_hours=self.config.manual_outbox_stale_hours,
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
        if published_results and self.config.x_publishing_mode == "manual":
            outbox_status = self.manual_outbox.prepare_many(
                published_results,
                now=now,
                stale_after_hours=self.config.manual_outbox_stale_hours,
            )
            try:
                email_status = self.x_email_notifier.notify_if_needed(self.manual_outbox.current())
            except XEmailNotificationError as exc:
                logger.error("manual_x_email_failed category=%s", type(exc).__name__)
                email_status = "failed"
            return {
                "platform": "X",
                "content_id": published_results[0].content_id,
                "content_ids": [record.content_id for record in published_results],
                "status": "manual_ready",
                "outbox": outbox_status,
                "email": email_status,
            }
        if saw_cooldown:
            return {"platform": "X", "status": "cooldown"}
        if manual_blockers:
            return {"platform": "X", "status": "blocked", "detail": "; ".join(dict.fromkeys(manual_blockers))}
        if published_results:
            return {"platform": "X", "status": "published", "published_count": len(published_results), "results": published_results}
        return {"platform": "X", "status": "idle", "detail": "no unblocked GREEN queue item"}

    def _process_x_amplification(self, now: datetime) -> dict[str, Any]:
        """Collect X signals and optionally retweet only high-confidence candidates."""
        try:
            live_x = self.config.live and self.config.x_publishing_mode == "live"
            if live_x:
                cached = load_intelligence_state(self.config.x_intelligence_state_file)
                if cached and cached.get("status") == "LIVE" and intelligence_is_live_and_fresh(
                    self.config.x_intelligence_state_file,
                    now=now,
                    max_age_hours=self.config.x_intelligence_refresh_hours,
                ):
                    intelligence = cached
                elif cached and cached.get("status") == "BLOCKED" and _state_age_hours(cached, now=now) < self.config.x_intelligence_refresh_hours:
                    intelligence = cached
                else:
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
                if not self.x_daily_cap.available("retweets", self.config.x_daily_retweet_cap, now=now):
                    return {"platform": "XAmplification", "status": "daily_cap", "detail": "daily X retweet cap reached", "reposted": 0}
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
                    self.x_daily_cap.record("retweets", now=now)
                    reposted += 1
                    if not self.x_daily_cap.available("retweets", self.config.x_daily_retweet_cap, now=now):
                        break
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
            # A visual-QA dead letter is a retry guard, not a permanent ban.
            # Human approval is the explicit state transition that makes a
            # newly reviewed checksum eligible again. Without this recovery,
            # an item approved after a prior review failure would remain stuck
            # forever even though publish_next() would now pass its gates.
            previous = self.state.records.get(key, {})
            review_state_changed = (
                previous.get("error_category") == "BLOCKED_VISUAL_QA"
                and (_approved_short_waiting(self.config.short_handoff_file) or _pending_review_short_waiting(self.config.short_handoff_file))
            )
            if review_state_changed:
                self.state.record_success(key)
            else:
                return {"platform": key, "status": "dead_letter" if self.state.records[key].get("dead_letter") else "cooldown"}
        if not self.config.short_handoff_file.is_file() and not self.config.short_handoff_refill_enabled:
            return {"platform": "YouTubeShortHandoff", "status": "idle", "detail": "handoff queue is empty"}
        engine = None
        catalog_status = "available"
        try:
            try:
                engine = create_database_engine(get_settings())
                check_connectivity(engine)
            except Exception as exc:
                if engine is not None:
                    engine.dispose()
                engine = None
                catalog_status = "unavailable"
                logger.warning("dynamic_content_catalog_unavailable category=%s; using static catalog", type(exc).__name__)
            queue = load_handoff(self.config.short_handoff_file)
            queued = sum(item.status == "queued" and item.readiness == "GREEN" for item in queue.items)
            if self.config.short_handoff_refill_enabled and queued < queue.buffer_target:
                prepare_short_handoff(
                    settings=get_settings(),
                    queue_path=self.config.short_handoff_file,
                    # Rendering is expensive and the daily public cap is one
                    # Short.  Keep an at-most-one forward refill per cycle by
                    # default; operators can raise this bounded value when a
                    # larger pre-render buffer is intentionally desired.
                    limit=min(queue.buffer_target, self.config.short_handoff_refill_batch),
                    engine=engine,
                )
            if not self.config.short_handoff_file.is_file():
                return {
                    "platform": "YouTubeShortHandoff",
                    "status": "idle",
                    "detail": "handoff queue is empty",
                    "catalog_status": catalog_status,
                }
            result = publish_next_short_handoff(
                publisher=self.youtube_distribution.publisher,
                queue_path=self.config.short_handoff_file,
                cap_path=self.config.autonomous_cap_file,
                now=now,
                live=self.config.live,
                engine=engine,
            )
            if result.get("status") == "not_ready":
                if _human_review_required(result.get("detail")):
                    self.state.record_success(key)
                    result = {**result, "status": "awaiting_human_approval"}
                else:
                    self.state.record_failure(key, error_category="BLOCKED_VISUAL_QA", now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
            else:
                self.state.record_success(key)
            return {"platform": "YouTubeShortHandoff", **result, "catalog_status": catalog_status}
        except Exception as exc:
            self.state.record_failure(key, error_category=type(exc).__name__, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
            logger.error("short_youtube_handoff_failed category=%s", type(exc).__name__)
            return {
                "platform": "YouTubeShortHandoff",
                "status": "failed",
                "error_category": type(exc).__name__,
                "catalog_status": catalog_status,
            }
        finally:
            if engine is not None:
                engine.dispose()


def _state_age_hours(payload: dict[str, Any], *, now: datetime) -> float:
    try:
        generated = datetime.fromisoformat(str(payload["generated_at"]).replace("Z", "+00:00")).astimezone(UTC)
        return max(0.0, (now.astimezone(UTC) - generated).total_seconds() / 3600)
    except (KeyError, TypeError, ValueError):
        return float("inf")


def _approved_short_waiting(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        queue = load_handoff(path)
    except (OSError, ValueError, TypeError):
        return False
    return any(
        item.status == "queued"
        and item.readiness == "GREEN"
        and item.creative_approval_state == "approved"
        and item.creative_approval_video_checksum == item.video_checksum
        for item in queue.items
    )


def _pending_review_short_waiting(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        queue = load_handoff(path)
    except (OSError, ValueError, TypeError):
        return False
    return any(
        item.status == "queued"
        and item.readiness == "GREEN"
        and item.creative_approval_state == "pending_review"
        for item in queue.items
    )


def _human_review_required(detail: Any) -> bool:
    return "human creative quality approval is required" in str(detail or "")


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


@contextlib.contextmanager
def _exclusive_worker_lock(path: Path):
    """Prevent Task Scheduler restarts from creating competing workers.

    The lock is held by the process for its entire lifetime and is released by
    the OS when the process exits, including an ungraceful termination.  The
    lock file itself is intentionally retained as a harmless operational
    marker; only the OS lock controls ownership.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        handle.seek(0)
        handle.write(b"0")
        handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("another distribution worker instance is already running") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("another distribution worker instance is already running") from exc
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()


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
    try:
        with _exclusive_worker_lock(worker.config.lock_file):
            if args.once:
                print(json.dumps(worker.run_once(), indent=2, sort_keys=True))
            else:
                worker.run_forever(interval_seconds=args.interval_seconds)
    except RuntimeError as exc:
        logger.warning("distribution_worker_not_started reason=%s", exc)
        print(json.dumps({"status": "already_running", "detail": str(exc)}))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
