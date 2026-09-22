"""Restart-safe YouTube -> X pairing for the autonomous distribution worker."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.distribution.x_queue import x_weighted_character_count


PAIRED_SOCIAL_VERSION = "youtube-x-pair-v1"
DEFAULT_STATE_FILE = Path("data/local/distribution/paired_social.json")
DEFAULT_OUTBOX_FILE = Path("data/local/distribution/paired_x_outbox.json")


class PairedSocialStore:
    """Small atomic JSON store keyed by the exact published video checksum."""

    def __init__(self, path: Path = DEFAULT_STATE_FILE) -> None:
        self.path = path
        self.payload = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": PAIRED_SOCIAL_VERSION, "records": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": PAIRED_SOCIAL_VERSION, "records": {}}
        records = payload.get("records") if isinstance(payload, dict) else None
        return {"version": PAIRED_SOCIAL_VERSION, "records": records if isinstance(records, dict) else {}}

    def get(self, key: str) -> dict[str, Any] | None:
        value = self.payload["records"].get(key)
        return dict(value) if isinstance(value, dict) else None

    def put(self, key: str, record: dict[str, Any]) -> None:
        self.payload["records"][key] = dict(record)
        self._save()

    def all(self) -> list[dict[str, Any]]:
        return [dict(record) for record in self.payload["records"].values() if isinstance(record, dict)]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self.payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def pairing_key(content_id: str, video_checksum: str) -> str:
    return f"{content_id}:{video_checksum}"


def build_paired_x_text(*, title: str, youtube_video_id: str, source_url: str) -> str:
    """Build a short, link-first promotional post within X's weighted limit."""
    youtube_url = f"https://youtu.be/{youtube_video_id}"
    clean_title = " ".join(str(title or "GamCryp Short").split())[:110]
    clean_source = str(source_url or "").strip()
    candidates = (
        f"{clean_title}\n\nYeni Short: {youtube_url}\n\n{clean_source}\n\n#GamCryp #Web3",
        f"{clean_title}\n\nIzle: {youtube_url}\n\n#GamCryp #Web3",
        f"{clean_title} - {youtube_url}\n\n#GamCryp",
    )
    for candidate in candidates:
        if x_weighted_character_count(candidate) <= 280:
            return candidate
    return candidates[-1][:280]


def youtube_record(*, item: Any, youtube_video_id: str, now: datetime) -> dict[str, Any]:
    checksum = str(item.video_checksum)
    return {
        "version": PAIRED_SOCIAL_VERSION,
        "key": pairing_key(str(item.content_id), checksum),
        "package_id": str(item.package_id),
        "content_id": str(item.content_id),
        "title": str(item.title),
        "source_url": str(item.source_url),
        "video_path": str(item.video_path),
        "video_checksum": checksum,
        "youtube_video_id": str(youtube_video_id),
        "youtube_url": f"https://youtu.be/{youtube_video_id}",
        "x_text": build_paired_x_text(title=str(item.title), youtube_video_id=str(youtube_video_id), source_url=str(item.source_url)),
        "x_status": "pending",
        "x_post_id": None,
        "x_media_id": None,
        "last_error": None,
        "created_at": now.astimezone(UTC).isoformat(),
        "updated_at": now.astimezone(UTC).isoformat(),
    }


def write_outbox(path: Path, records: list[dict[str, Any]], *, now: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": PAIRED_SOCIAL_VERSION,
        "generated_at": now.astimezone(UTC).isoformat(),
        "items": [record for record in records if record.get("x_status") in {"manual_ready", "pending", "failed"}],
    }
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

