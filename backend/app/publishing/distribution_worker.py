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

from app.distribution.x_publisher import XPublisherConfig, XPublishingService
from app.distribution.refill import DistributionRefillConfig, DistributionRefiller
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.publishing.youtube_distribution import YouTubeDistributionConfig, YouTubeDistributionPublisher

logger = logging.getLogger("gamcryp.distribution_worker")


@dataclass(frozen=True)
class DistributionWorkerConfig:
    live: bool = False
    video_directory: Path = Path("data/local/youtube/videos")
    thumbnail_directory: Path | None = None
    state_file: Path = Path("data/local/distribution/worker_state.json")
    failure_cooldown_seconds: int = 1800

    @classmethod
    def from_environment(cls) -> "DistributionWorkerConfig":
        thumbnail = os.getenv("GAMEFI_DISTRIBUTION_THUMBNAIL_DIR", "").strip()
        return cls(
            live=os.getenv("GAMEFI_DISTRIBUTION_LIVE", "false").strip().lower() in {"1", "true", "yes"},
            video_directory=Path(os.getenv("GAMEFI_DISTRIBUTION_VIDEO_DIR", "data/local/youtube/videos")),
            thumbnail_directory=Path(thumbnail) if thumbnail else None,
            state_file=Path(os.getenv("GAMEFI_DISTRIBUTION_WORKER_STATE_FILE", "data/local/distribution/worker_state.json")),
            failure_cooldown_seconds=int(os.getenv("GAMEFI_DISTRIBUTION_FAILURE_COOLDOWN_SECONDS", "1800")),
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
        value = self.records.get(key, {}).get("retry_after")
        if not value:
            return False
        try:
            return datetime.fromisoformat(value) > now
        except ValueError:
            return False

    def record_failure(self, key: str, *, error_category: str, now: datetime, cooldown_seconds: int) -> None:
        self.records[key] = {
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
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.config = config or DistributionWorkerConfig.from_environment()
        self.x_service = x_service or XPublishingService(XPublisherConfig.from_environment())
        self.youtube_distribution = youtube_distribution or _youtube_distribution_from_environment()
        self.refiller = refiller or DistributionRefiller(DistributionRefillConfig.from_environment())
        self.now = now
        self.state = WorkerState(self.config.state_file)

    def run_once(self) -> list[dict[str, Any]]:
        now = self.now()
        results = []
        try:
            refill_result = self.refiller.run(now=now)
            if refill_result.get("status") != "disabled":
                results.append(refill_result)
        except Exception as exc:
            logger.error("distribution_refill_failed category=%s", type(exc).__name__)
            results.append({"platform": "distribution", "status": "refill_failed", "error_category": type(exc).__name__})
        results.append(self._process_x(now))
        results.extend(self._process_youtube(now))
        return results

    def run_forever(self, *, interval_seconds: int = 1800) -> None:
        if interval_seconds < 60:
            raise ValueError("worker interval must be at least 60 seconds")
        while True:
            self.run_once()
            time.sleep(interval_seconds)

    def _process_x(self, now: datetime) -> dict[str, Any]:
        summary = self.x_service.queue_summary()
        candidates = summary.get("publishable", [])
        if not candidates:
            return {"platform": "X", "status": "idle", "detail": "no GREEN queue item"}
        content_id = str(candidates[0])
        key = f"X:{content_id}"
        try:
            preview = self.x_service.preview(content_id)
            key = f"X:{content_id}:{preview.content_checksum}"
            if self.state.blocked(key, now=now) or self.state.blocked(f"X:{content_id}", now=now):
                return {"platform": "X", "content_id": content_id, "status": "cooldown"}
            result = self.x_service.publish(content_id, dry_run=not self.config.live, confirm_publish=self.config.live)
            self.state.record_success(key)
            return {"platform": "X", "content_id": content_id, "status": "published" if self.config.live else "dry_run", "result": result.model_dump(mode="json")}
        except Exception as exc:  # Publisher classifies and persists the failure; worker must continue.
            category = type(exc).__name__
            self.state.record_failure(key, error_category=category, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
            if key != f"X:{content_id}":
                self.state.record_failure(f"X:{content_id}", error_category=category, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
            logger.error("distribution_publish_failed platform=X content_id=%s category=%s", content_id, category)
            return {"platform": "X", "content_id": content_id, "status": "failed", "error_category": category}

    def _process_youtube(self, now: datetime) -> list[dict[str, Any]]:
        summary = self.youtube_distribution.queue_summary()
        results = []
        for content_id in summary.get("publishable", []):
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
                results.append({"platform": "YouTube", "content_id": content_id, "status": "published" if self.config.live else "dry_run", "result": operation.to_safe_dict()})
            except Exception as exc:
                category = type(exc).__name__
                self.state.record_failure(key, error_category=category, now=now, cooldown_seconds=self.config.failure_cooldown_seconds)
                logger.error("distribution_publish_failed platform=YouTube content_id=%s category=%s", content_id, category)
                results.append({"platform": "YouTube", "content_id": content_id, "status": "failed", "error_category": category})
        if not results:
            results.append({"platform": "YouTube", "status": "idle", "detail": "no GREEN queue item"})
        return results


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
    parser = argparse.ArgumentParser(description="Run the fail-closed GamCryp distribution worker.")
    parser.add_argument("--once", action="store_true", help="Process one interval and exit.")
    parser.add_argument("--interval-seconds", type=int, default=1800)
    args = parser.parse_args(argv)
    logging.basicConfig(level=os.getenv("GAMEFI_DISTRIBUTION_LOG_LEVEL", "INFO"))
    worker = DistributionWorker()
    if args.once:
        print(json.dumps(worker.run_once(), indent=2, sort_keys=True))
    else:
        worker.run_forever(interval_seconds=args.interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
