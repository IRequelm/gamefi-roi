"""Small deterministic outbox for operator-mediated X publication."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class XManualReadyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    status: str = "MANUAL_READY"
    post_text: str
    source_url: str
    prepared_at: str
    checksum: str
    published: bool = False
    official_handle: str | None = None
    hashtags: tuple[str, ...] = ()
    media_path: str | None = None
    media_kind: str | None = None
    media_source: str | None = None
    enrichment_fingerprint: str | None = None


class XManualOutbox:
    def __init__(self, path: Path):
        self.path = path
        self.archive_path = path.with_name(f"{path.stem}_archive.jsonl")

    def current(self) -> XManualReadyRecord | None:
        records = self._records()
        return next((record for record in records if not record.published), records[0] if records else None)

    def pending(self) -> XManualReadyRecord | None:
        """Return only an unpublished item; confirmed records stay auditable."""
        record = self.current()
        return record if record is not None and not record.published else None

    def prepare(
        self,
        record: XManualReadyRecord,
        *,
        now: datetime | None = None,
        stale_after_hours: int | None = None,
    ) -> str:
        current = self.current()
        if current and not current.published and current.checksum != record.checksum:
            if current.content_id == record.content_id:
                self._archive(current)
                self._write({"version": 1, "item": record.model_dump(mode="json")})
                return "replaced_changed"
            if stale_after_hours is not None and stale_after_hours > 0 and self._is_stale(
                current,
                now=now or datetime.now(UTC),
                stale_after_hours=stale_after_hours,
            ):
                self._archive(current)
                self._write({"version": 1, "item": record.model_dump(mode="json")})
                return "replaced_stale"
            return "retained_existing"
        if current and not current.published and (
            current.content_id,
            current.checksum,
            current.post_text,
            current.source_url,
        ) == (
            record.content_id,
            record.checksum,
            record.post_text,
            record.source_url,
        ):
            return "unchanged"
        self._write({"version": 1, "item": record.model_dump(mode="json")})
        return "written"

    def prepare_many(
        self,
        records: list[XManualReadyRecord],
        *,
        now: datetime | None = None,
        stale_after_hours: int | None = None,
    ) -> str:
        """Add a bounded batch while preserving unpublished manual items."""
        if not records:
            return "unchanged_batch"
        existing = self._records()
        retained: list[XManualReadyRecord] = []
        changed = False
        incoming_by_content_id = {record.content_id: record for record in records}
        for current in existing:
            if current.published:
                retained.append(current)
                continue
            incoming = incoming_by_content_id.get(current.content_id)
            if incoming is not None and current.checksum != incoming.checksum:
                self._archive(current)
                changed = True
                continue
            if stale_after_hours is not None and stale_after_hours > 0 and self._is_stale(
                current,
                now=now or datetime.now(UTC),
                stale_after_hours=stale_after_hours,
            ):
                self._archive(current)
                changed = True
            else:
                retained.append(current)
        seen = {(record.content_id, record.checksum) for record in retained}
        for record in records:
            key = (record.content_id, record.checksum)
            if key not in seen:
                retained.append(record)
                seen.add(key)
                changed = True
        if changed or not existing:
            self._write_records(retained)
            return "written_batch"
        return "unchanged_batch"

    @staticmethod
    def _is_stale(record: XManualReadyRecord, *, now: datetime, stale_after_hours: int) -> bool:
        try:
            prepared_at = datetime.fromisoformat(record.prepared_at)
        except ValueError:
            return False
        if prepared_at.tzinfo is None:
            prepared_at = prepared_at.replace(tzinfo=UTC)
        return now.astimezone(UTC) - prepared_at.astimezone(UTC) >= timedelta(hours=stale_after_hours)

    def _archive(self, record: XManualReadyRecord) -> None:
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        with self.archive_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")

    def clear(self, *, content_id: str, checksum: str) -> None:
        current = self.current()
        if current is None:
            raise ValueError("no current X manual-ready item")
        if current.content_id != content_id or current.checksum != checksum:
            raise ValueError("current X manual-ready item does not match confirmation")
        records = [
            record.model_copy(update={"published": True}) if record.content_id == content_id and record.checksum == checksum else record
            for record in self._records()
        ]
        self._write_records(records)

    def _records(self) -> list[XManualReadyRecord]:
        payload = self._read()
        raw_items = payload.get("items")
        if isinstance(raw_items, list):
            return [XManualReadyRecord.model_validate(item) for item in raw_items if isinstance(item, dict)]
        item = payload.get("item")
        return [XManualReadyRecord.model_validate(item)] if isinstance(item, dict) else []

    def _read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def _write_records(self, records: list[XManualReadyRecord]) -> None:
        pending = next((record for record in records if not record.published), records[0] if records else None)
        payload: dict[str, Any] = {
            "version": 2,
            "items": [record.model_dump(mode="json") for record in records],
        }
        if pending is not None:
            payload["item"] = pending.model_dump(mode="json")
        self._write(payload)


def manual_ready_record(*, content_id: str, post_text: str, source_url: str, checksum: str, now: datetime | None = None, official_handle: str | None = None, hashtags: tuple[str, ...] = (), media_path: str | None = None, media_kind: str | None = None, media_source: str | None = None, enrichment_fingerprint: str | None = None) -> XManualReadyRecord:
    prepared_at = (now or datetime.now(UTC)).isoformat()
    return XManualReadyRecord(content_id=content_id, post_text=post_text, source_url=source_url, prepared_at=prepared_at, checksum=checksum, official_handle=official_handle, hashtags=hashtags, media_path=media_path, media_kind=media_kind, media_source=media_source, enrichment_fingerprint=enrichment_fingerprint)
