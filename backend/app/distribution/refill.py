"""Bounded, source-backed distribution queue refill."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from app.distribution.content_pack import write_batch
from app.distribution.learning_batch import LEARNING_BATCH_CREATED_AT, LEARNING_BATCH_ID, build_learning_batch
from app.distribution.x_queue import build_x_publish_queue, editorial_order_from_handoff, load_content_pack_batch, write_x_queue
from app.distribution.youtube_queue import build_youtube_publish_queue, load_youtube_queue, write_youtube_queue


@dataclass(frozen=True)
class DistributionRefillConfig:
    enabled: bool = False
    buffer_size: int = 3
    cooldown_hours: int = 24
    content_pack_file: Path = Path("distribution/content_packs/learning_batch_001.json")
    youtube_queue_file: Path = Path("distribution/publish_queue/youtube_publish_queue.json")
    x_queue_file: Path = Path("distribution/publish_queue/x_publish_queue.json")
    handoff_file: Path = Path("distribution/publish_queue/next_publish_queue.json")
    youtube_state_file: Path = Path("data/local/youtube/publish_state.json")
    x_state_file: Path = Path("data/local/x/publications.json")
    video_directory: Path = Path("data/local/youtube/videos")
    rankings_url: str = "https://gamcryp.com/api/v1/rankings?limit=100"
    opportunities_url: str = "https://gamcryp.com/api/v1/opportunities?limit=100"
    base_url: str = "https://gamcryp.com"
    state_file: Path = Path("data/local/distribution/refill_state.json")

    @classmethod
    def from_environment(cls) -> "DistributionRefillConfig":
        return cls(
            enabled=os.getenv("GAMEFI_DISTRIBUTION_REFILL_ENABLED", "false").lower() in {"1", "true", "yes"},
            buffer_size=int(os.getenv("GAMEFI_DISTRIBUTION_BUFFER_SIZE", "3")),
            cooldown_hours=int(os.getenv("GAMEFI_DISTRIBUTION_REFILL_COOLDOWN_HOURS", "24")),
            content_pack_file=Path(os.getenv("GAMEFI_YOUTUBE_CONTENT_PACK_FILE", cls.content_pack_file)),
            youtube_queue_file=Path(os.getenv("GAMEFI_YOUTUBE_QUEUE_FILE", cls.youtube_queue_file)),
            x_queue_file=Path(os.getenv("GAMEFI_X_QUEUE_FILE", cls.x_queue_file)),
            handoff_file=Path(os.getenv("GAMEFI_DISTRIBUTION_HANDOFF_FILE", cls.handoff_file)),
            youtube_state_file=Path(os.getenv("GAMEFI_YOUTUBE_PUBLISH_STATE_FILE", cls.youtube_state_file)),
            x_state_file=Path(os.getenv("GAMEFI_X_PUBLICATION_FILE", cls.x_state_file)),
            video_directory=Path(os.getenv("GAMEFI_DISTRIBUTION_VIDEO_DIR", cls.video_directory)),
            rankings_url=os.getenv("GAMEFI_DISTRIBUTION_RANKINGS_URL", cls.rankings_url),
            opportunities_url=os.getenv("GAMEFI_DISTRIBUTION_OPPORTUNITIES_URL", cls.opportunities_url),
            base_url=os.getenv("GAMEFI_PUBLIC_BASE_URL", cls.base_url),
            state_file=Path(os.getenv("GAMEFI_DISTRIBUTION_REFILL_STATE_FILE", cls.state_file)),
        )


class DistributionRefiller:
    def __init__(
        self,
        config: DistributionRefillConfig,
        *,
        fetch_json: Callable[[str], dict[str, Any]] | None = None,
        build_packs: Callable[..., list[Any]] = build_learning_batch,
    ):
        self.config = config
        self.fetch_json = fetch_json or _fetch_json
        self.build_packs = build_packs

    def run(self, *, now: datetime | None = None) -> dict[str, Any]:
        if not self.config.enabled:
            return {"platform": "distribution", "status": "disabled"}
        current = now or datetime.now(UTC)
        youtube = load_youtube_queue(self.config.youtube_queue_file)
        x = _load_json(self.config.x_queue_file)
        youtube_buffer = _unpublished_ids(youtube.publishable, self.config.youtube_state_file)
        x_buffer = _unpublished_ids_from_json(x, self.config.x_state_file)
        if youtube_buffer >= self.config.buffer_size and x_buffer >= self.config.buffer_size:
            return {"platform": "distribution", "status": "buffer_sufficient", "youtube": youtube_buffer, "x": x_buffer}
        state = _load_json(self.config.state_file)
        last_attempt = _parse_time(state.get("last_attempt_at"))
        if last_attempt and current < last_attempt + timedelta(hours=self.config.cooldown_hours):
            return {"platform": "distribution", "status": "cooldown", "youtube": youtube_buffer, "x": x_buffer}
        rankings = self.fetch_json(self.config.rankings_url)
        opportunities = self.fetch_json(self.config.opportunities_url)
        packs = self.build_packs(rankings, opportunities, base_url=self.config.base_url)
        source_bytes = _canonical_pack_bytes(packs)
        prior_hash = state.get("source_batch_hash")
        batch_hash = hashlib.sha256(source_bytes).hexdigest()
        _write_state(self.config.state_file, {"state_version": "distribution-refill-v1", "last_attempt_at": current.isoformat(), "source_batch_hash": batch_hash})
        if prior_hash == batch_hash and self.config.content_pack_file.is_file():
            return {"platform": "distribution", "status": "unchanged", "youtube": youtube_buffer, "x": x_buffer}
        write_batch(self.config.content_pack_file, packs, batch_id=LEARNING_BATCH_ID, generated_at=LEARNING_BATCH_CREATED_AT, source_dataset=f"{self.config.rankings_url} + {self.config.opportunities_url}")
        payload, loaded_packs = load_content_pack_batch(self.config.content_pack_file)
        write_youtube_queue(self.config.youtube_queue_file, build_youtube_publish_queue(batch_payload=payload, packs=loaded_packs, source_batch_bytes=self.config.content_pack_file.read_bytes(), video_directory=self.config.video_directory))
        write_x_queue(self.config.x_queue_file, build_x_publish_queue(batch_payload=payload, packs=loaded_packs, source_batch_bytes=self.config.content_pack_file.read_bytes(), editorial_order=editorial_order_from_handoff(self.config.handoff_file)))
        return {"platform": "distribution", "status": "refilled", "youtube": youtube_buffer, "x": x_buffer}


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _canonical_pack_bytes(packs: list[Any]) -> bytes:
    payload = [pack.model_dump(mode="json") for pack in sorted(packs, key=lambda item: item.content_id)]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _unpublished_ids(items: tuple[Any, ...], state_file: Path) -> int:
    state = _load_json(state_file)
    records = state.get("records", {})
    return sum(1 for item in items if not (isinstance(records, dict) and isinstance(records.get(item.content_id), dict) and records[item.content_id].get("status") == "uploaded"))


def _unpublished_ids_from_json(queue: dict[str, Any], state_file: Path) -> int:
    items = queue.get("publishable", []) if isinstance(queue, dict) else []
    state = _load_json(state_file)
    records = state.get("records", {})
    return sum(1 for item in items if isinstance(item, dict) and not (isinstance(records, dict) and isinstance(records.get(item.get("content_id")), list) and any(record.get("status") == "published" for record in records[item.get("content_id")])) )


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
