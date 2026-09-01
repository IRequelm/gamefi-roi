"""Deterministic X publishing queue derived from validated Content Pack Lite artifacts."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.distribution.content_pack import ContentPackLite, ContentReadiness, canonical_json, validate_batch

X_QUEUE_VERSION = "x-publish-queue-v1"
X_MAX_WEIGHTED_LENGTH = 280
X_TRANSFORMED_URL_LENGTH = 23


class QueueApprovalState(str, Enum):
    NOT_REQUIRED = "not_required"
    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    BLOCKED = "blocked"


class XQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    channel: str = "X"
    project: str
    status: ContentReadiness
    approval_required: bool
    approval_state: QueueApprovalState
    final_copy: str
    attribution_url: str
    snapshot_id: str | None = None
    snapshot_timestamp: str | None = None
    refreshability: str | None = None
    risk_caveat: str
    content_checksum: str
    recommended_order: int = Field(ge=1)
    source_pack_version: str
    generated_at: str


class XPublishQueue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    queue_version: str = X_QUEUE_VERSION
    source_batch_id: str
    source_batch_hash: str
    generated_at: str
    publishable: tuple[XQueueItem, ...]
    awaiting_human_approval: tuple[XQueueItem, ...]
    blocked: tuple[XQueueItem, ...]

    @property
    def items(self) -> tuple[XQueueItem, ...]:
        return self.publishable + self.awaiting_human_approval + self.blocked

    def find(self, content_id: str) -> XQueueItem:
        matches = [item for item in self.items if item.content_id == content_id]
        if len(matches) != 1:
            raise KeyError(content_id)
        return matches[0]


def load_content_pack_batch(path: Path) -> tuple[dict[str, Any], tuple[ContentPackLite, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    packs = tuple(ContentPackLite.model_validate(item) for item in payload["packs"])
    validate_batch(list(packs))
    return payload, packs


def load_x_queue(path: Path) -> XPublishQueue:
    return XPublishQueue.model_validate_json(path.read_text(encoding="utf-8"))


def x_content_checksum(pack: ContentPackLite, final_copy: str | None = None) -> str:
    copy = final_copy if final_copy is not None else pack.editorial.x_post
    payload = {
        "attribution_url": pack.distribution.x_utm_url,
        "content_id": pack.content_id,
        "content_pack_version": pack.content_pack_version,
        "copy": unicodedata.normalize("NFC", copy),
        "snapshot_id": pack.source.snapshot_id,
        "snapshot_timestamp": pack.source.snapshot_timestamp,
        "source_snapshot_hash": pack.source.source_snapshot_hash,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_x_publish_queue(
    *,
    batch_payload: dict[str, Any],
    packs: tuple[ContentPackLite, ...],
    source_batch_bytes: bytes,
    editorial_order: dict[str, int] | None = None,
) -> XPublishQueue:
    validate_batch(list(packs))
    order = dict(editorial_order or {})
    fallback_start = max(order.values(), default=0) + 1
    fallback_ids = sorted(pack.content_id for pack in packs if pack.content_id not in order)
    order.update({content_id: fallback_start + index for index, content_id in enumerate(fallback_ids)})

    items = tuple(_queue_item(pack, order[pack.content_id], str(batch_payload["generated_at"])) for pack in packs)
    return XPublishQueue(
        source_batch_id=str(batch_payload["batch_id"]),
        source_batch_hash=hashlib.sha256(source_batch_bytes).hexdigest(),
        generated_at=str(batch_payload["generated_at"]),
        publishable=tuple(sorted((item for item in items if item.status is ContentReadiness.GREEN), key=_order_key)),
        awaiting_human_approval=tuple(
            sorted((item for item in items if item.status is ContentReadiness.YELLOW), key=_order_key)
        ),
        blocked=tuple(sorted((item for item in items if item.status is ContentReadiness.RED), key=_order_key)),
    )


def write_x_queue(path: Path, queue: XPublishQueue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(queue.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def editorial_order_from_handoff(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = list(payload.get("green", [])) + list(payload.get("yellow_requires_human_approval", []))
    return {
        str(item["content_id"]): int(item["recommended_order"])
        for item in items
        if item.get("channel") == "X" and item.get("content_id") and item.get("recommended_order")
    }


def x_weighted_character_count(text: str) -> int:
    """Conservatively implement X's 280-weight count and 23-character URL rule.

    The official twitter-text implementation should remain the final platform
    authority. This counter follows its documented Unicode ranges and safely
    over-counts complex emoji sequences rather than allowing an oversized Post.
    """

    normalized = unicodedata.normalize("NFC", text)
    count = 0
    cursor = 0
    for start, end in _url_spans(normalized):
        count += _weighted_text(normalized[cursor:start]) + X_TRANSFORMED_URL_LENGTH
        cursor = end
    return count + _weighted_text(normalized[cursor:])


def _queue_item(pack: ContentPackLite, recommended_order: int, generated_at: str) -> XQueueItem:
    approval_required = pack.editorial.readiness is ContentReadiness.YELLOW
    approval_state = {
        ContentReadiness.GREEN: QueueApprovalState.NOT_REQUIRED,
        ContentReadiness.YELLOW: QueueApprovalState.AWAITING_HUMAN_APPROVAL,
        ContentReadiness.RED: QueueApprovalState.BLOCKED,
    }[pack.editorial.readiness]
    return XQueueItem(
        content_id=pack.content_id,
        project=pack.facts.project_name,
        status=pack.editorial.readiness,
        approval_required=approval_required,
        approval_state=approval_state,
        final_copy=pack.editorial.x_post,
        attribution_url=pack.distribution.x_utm_url,
        snapshot_id=pack.source.snapshot_id,
        snapshot_timestamp=pack.source.snapshot_timestamp,
        refreshability=pack.source.refreshability.value if pack.source.refreshability else None,
        risk_caveat=pack.facts.major_catch,
        content_checksum=x_content_checksum(pack),
        recommended_order=recommended_order,
        source_pack_version=pack.content_pack_version,
        generated_at=generated_at,
    )


def _order_key(item: XQueueItem) -> tuple[int, str]:
    return item.recommended_order, item.content_id


def _url_spans(text: str) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    for scheme in ("https://", "http://"):
        start = 0
        while True:
            index = text.find(scheme, start)
            if index < 0:
                break
            end = index
            while end < len(text) and not text[end].isspace():
                end += 1
            spans.append((index, end))
            start = end
    return tuple(sorted(spans))


def _weighted_text(text: str) -> int:
    return sum(_character_weight(character) for character in text)


def _character_weight(character: str) -> int:
    codepoint = ord(character)
    if 0 <= codepoint <= 4351:
        return 1
    if 8192 <= codepoint <= 8205:
        return 1
    if 8208 <= codepoint <= 8223:
        return 1
    if 8242 <= codepoint <= 8247:
        return 1
    return 2
