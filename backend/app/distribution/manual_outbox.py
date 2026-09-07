"""Small deterministic outbox for operator-mediated X publication."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
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


class XManualOutbox:
    def __init__(self, path: Path):
        self.path = path

    def current(self) -> XManualReadyRecord | None:
        payload = self._read()
        item = payload.get("item")
        return XManualReadyRecord.model_validate(item) if isinstance(item, dict) else None

    def prepare(self, record: XManualReadyRecord) -> str:
        current = self.current()
        if current and not current.published and current.checksum != record.checksum:
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

    def clear(self, *, content_id: str, checksum: str) -> None:
        current = self.current()
        if current is None:
            raise ValueError("no current X manual-ready item")
        if current.content_id != content_id or current.checksum != checksum:
            raise ValueError("current X manual-ready item does not match confirmation")
        self._write({"version": 1, "item": current.model_copy(update={"published": True}).model_dump(mode="json")})

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


def manual_ready_record(*, content_id: str, post_text: str, source_url: str, checksum: str, now: datetime | None = None) -> XManualReadyRecord:
    prepared_at = (now or datetime.now(UTC)).isoformat()
    return XManualReadyRecord(content_id=content_id, post_text=post_text, source_url=source_url, prepared_at=prepared_at, checksum=checksum)
