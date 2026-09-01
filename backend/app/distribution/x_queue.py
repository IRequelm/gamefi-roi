"""Deterministic X publishing queue derived from validated Content Pack Lite artifacts."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import string
import unicodedata
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from app.distribution.content_pack import ContentPackLite, ContentReadiness, canonical_json, validate_batch

X_QUEUE_VERSION = "x-publish-queue-v1"
X_MAX_WEIGHTED_LENGTH = 280
X_TRANSFORMED_URL_LENGTH = 23
HTTP_URL_START_RE = re.compile(r"(?i)https?://")
HTTP_HOST_RE = re.compile(r"(?i)(?<![\w@])https?://(?P<host>(?:[^\W_]|[.-])+)")
BARE_DOMAIN_RE = re.compile(
    r"(?i)(?<![\w@])(?:www\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
)
UNICODE_DOMAIN_RE = re.compile(r"(?i)(?<![\w@])(?P<host>(?:[^\W_]|-)+(?:\.(?:[^\W_]|-)+)+)")
ASCII_URL_CHARACTERS = frozenset(
    string.ascii_letters + string.digits + "-._~:/?#[]@!$&'()*+,;=%"
)
TRAILING_URL_PUNCTUATION = frozenset(
    ".,!?:;'\"\u2018\u2019\u201c\u201d\u00ab\u00bb\u2039\u203a"
    "\u3002\uff0c\uff01\uff1f\uff1a\uff1b\u3001"
)
BRACKET_PAIRS = {')': '(', ']': '[', '}': '{'}


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

    Valid HTTP(S) and bare-domain URLs use X's transformed length. Balanced URL
    brackets and internal query/fragment punctuation are retained; terminal
    punctuation is ordinary text. Common emoji grapheme sequences count as two.
    Ambiguous or malformed URL-like text is deliberately over-counted so local
    validation cannot admit an over-limit Post. X remains the final authority.
    """

    normalized = unicodedata.normalize("NFC", text)
    count = 0
    cursor = 0
    for start, end, url_weight in _url_spans(normalized):
        count += _weighted_text(normalized[cursor:start]) + url_weight
        cursor = end
    return count + _weighted_text(normalized[cursor:])


def contains_unsupported_idn_hostname(text: str) -> bool:
    """Return whether copy contains a URL/domain hostname outside ASCII."""

    normalized = unicodedata.normalize("NFC", text)
    for pattern in (HTTP_HOST_RE, UNICODE_DOMAIN_RE):
        for match in pattern.finditer(normalized):
            if not match.group("host").isascii():
                return True
    return False


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


def _url_spans(text: str) -> tuple[tuple[int, int, int], ...]:
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    while match := HTTP_URL_START_RE.search(text, cursor):
        start = match.start()
        cursor = match.end()
        if start > 0 and (text[start - 1].isalnum() or text[start - 1] in {"_", "@"}):
            continue
        candidate_end = cursor
        while candidate_end < len(text) and text[candidate_end] in ASCII_URL_CHARACTERS:
            candidate_end += 1
        end = _valid_url_end(text, start, candidate_end, minimum_end=match.end())
        if end > start:
            spans.append((start, end, X_TRANSFORMED_URL_LENGTH))
            cursor = end
            continue
        raw_end = match.end()
        while raw_end < len(text) and not text[raw_end].isspace():
            raw_end += 1
        raw_weight = _weighted_text(text[start:raw_end])
        spans.append((start, raw_end, max(X_TRANSFORMED_URL_LENGTH, raw_weight)))
        cursor = raw_end

    for match in BARE_DOMAIN_RE.finditer(text):
        start = match.start()
        if any(existing_start <= start < existing_end for existing_start, existing_end, _ in spans):
            continue
        candidate_end = match.end()
        while candidate_end < len(text) and text[candidate_end] in ASCII_URL_CHARACTERS:
            candidate_end += 1
        end = _valid_bare_url_end(text, start, candidate_end, minimum_end=match.end())
        if end <= start:
            continue
        literal_weight = _weighted_text(text[start:end])
        spans.append((start, end, max(X_TRANSFORMED_URL_LENGTH, literal_weight)))
    return tuple(sorted(spans, key=lambda item: item[0]))


def _trim_url_end(text: str, start: int, end: int) -> int:
    while end > start:
        candidate = text[start:end]
        trailing = candidate[-1]
        if trailing in TRAILING_URL_PUNCTUATION:
            end -= 1
            continue
        opener = BRACKET_PAIRS.get(trailing)
        if opener and candidate.count(trailing) > candidate.count(opener):
            end -= 1
            continue
        break
    return end


def _valid_url_end(text: str, start: int, end: int, *, minimum_end: int) -> int:
    candidate_end = _trim_url_end(text, start, end)
    while candidate_end >= minimum_end:
        if _is_valid_http_url(text[start:candidate_end]):
            return candidate_end
        candidate_end = _trim_url_end(text, start, candidate_end - 1)
    return start


def _valid_bare_url_end(text: str, start: int, end: int, *, minimum_end: int) -> int:
    candidate_end = _trim_url_end(text, start, end)
    while candidate_end >= minimum_end:
        if _is_valid_http_url(f"https://{text[start:candidate_end]}"):
            return candidate_end
        candidate_end = _trim_url_end(text, start, candidate_end - 1)
    return start


def _is_valid_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        return False
    if host == "localhost":
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    labels = host.rstrip(".").split(".")
    top_level_domain = labels[-1]
    return (
        len(labels) >= 2
        and (
            (len(top_level_domain) >= 2 and top_level_domain.isalpha())
            or (
                top_level_domain.lower().startswith("xn--")
                and len(top_level_domain) > 4
                and top_level_domain[4:].isalnum()
            )
        )
        and all(label and len(label) <= 63 for label in labels)
        and all(
            label[0].isalnum()
            and label[-1].isalnum()
            and all(character.isalnum() or character == "-" for character in label)
            for label in labels
        )
    )


def _weighted_text(text: str) -> int:
    count = 0
    cursor = 0
    while cursor < len(text):
        emoji_end = _emoji_sequence_end(text, cursor)
        if emoji_end is not None:
            count += 2
            cursor = emoji_end
            continue
        count += _character_weight(text[cursor])
        cursor += 1
    return count


def _emoji_sequence_end(text: str, start: int) -> int | None:
    codepoint = ord(text[start])
    if _is_regional_indicator(codepoint):
        if start + 1 < len(text) and _is_regional_indicator(ord(text[start + 1])):
            return start + 2
        return start + 1
    if text[start] in "#*0123456789":
        cursor = start + 1
        if cursor < len(text) and ord(text[cursor]) == 0xFE0F:
            cursor += 1
        return cursor + 1 if cursor < len(text) and ord(text[cursor]) == 0x20E3 else None
    if not _is_emoji_base(codepoint):
        return None
    cursor = _consume_emoji_component(text, start)
    while cursor < len(text) and ord(text[cursor]) == 0x200D:
        next_start = cursor + 1
        if next_start >= len(text) or not _is_emoji_base(ord(text[next_start])):
            break
        cursor = _consume_emoji_component(text, next_start)
    if cursor < len(text) and 0xE0020 <= ord(text[cursor]) <= 0xE007E:
        while cursor < len(text) and 0xE0020 <= ord(text[cursor]) <= 0xE007E:
            cursor += 1
        if cursor < len(text) and ord(text[cursor]) == 0xE007F:
            cursor += 1
    return cursor


def _consume_emoji_component(text: str, start: int) -> int:
    cursor = start + 1
    if cursor < len(text) and ord(text[cursor]) in {0xFE0E, 0xFE0F}:
        cursor += 1
    if cursor < len(text) and 0x1F3FB <= ord(text[cursor]) <= 0x1F3FF:
        cursor += 1
    return cursor


def _is_regional_indicator(codepoint: int) -> bool:
    return 0x1F1E6 <= codepoint <= 0x1F1FF


def _is_emoji_base(codepoint: int) -> bool:
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or codepoint
        in {0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x3030, 0x303D, 0x3297, 0x3299}
    )


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
