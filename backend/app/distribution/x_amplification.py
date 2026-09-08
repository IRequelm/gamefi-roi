"""Fail-closed X signal matching and a durable manual amplification outbox."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.strategies.catalog import list_opportunities

DEFAULT_FEED = Path("distribution/inbox/x_signal_feed.json")
DEFAULT_WHITELIST = Path("config/distribution/x_source_whitelist.json")
DEFAULT_OUTBOX = Path("distribution/manual_outbox/x_amplification_ready.json")
DEFAULT_HISTORY = Path("distribution/manual_outbox/x_amplification_history.json")
POST_URL_RE = re.compile(r"^https://(?:x\.com|twitter\.com)/[A-Za-z0-9_]{1,15}/status/[0-9]+(?:\?.*)?$")
UNSAFE_RE = re.compile(r"(?i)\b(guaranteed|risk[- ]?free|double your|100x|airdrop claim now|send crypto|buy now)\b")
SPAM_RE = re.compile(r"(?i)\b(giveaway|casino|referral code|limited time|free money)\b")


class AmplificationDecision(StrEnum):
    REPOST_NOW = "REPOST_NOW"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    IGNORE = "IGNORE"


class XSourcePost(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_account: str
    source_verified: bool = False
    source_type: str = "project_official"
    original_url: str
    post_id: str
    posted_at: str
    text: str

    @field_validator("original_url")
    @classmethod
    def stable_url(cls, value: str) -> str:
        if not POST_URL_RE.fullmatch(value):
            raise ValueError("original X URL must be a stable public status URL")
        return value


class XSourceWhitelistEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_account: str
    source_type: str
    verified: bool = False
    official_source_url: str


class XAmplificationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_account: str
    opportunity_id: str | None = None
    project_name: str | None = None
    original_post_url: str
    post_id: str
    post_timestamp: str
    reason: str
    recommendation: str
    suggested_quote: str | None = None
    confidence: float = Field(ge=0, le=1)
    priority: str
    decision: AmplificationDecision
    fingerprint: str
    created_at: str


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def _fingerprint(post: XSourcePost) -> str:
    return hashlib.sha256(f"{post.source_account.lower()}|{post.post_id}|{post.original_url}".encode()).hexdigest()


def _catalog_match(text: str) -> tuple[str | None, str | None]:
    lowered = text.casefold()
    for opportunity in list_opportunities():
        if opportunity.name.casefold() in lowered:
            return opportunity.opportunity_id, opportunity.name
    return None, None


def load_whitelist(path: Path = DEFAULT_WHITELIST) -> dict[str, XSourceWhitelistEntry]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {entry.source_account.casefold(): entry for entry in (XSourceWhitelistEntry.model_validate(item) for item in payload.get("sources", [])) if entry.verified and entry.official_source_url.startswith("https://")}
    except (OSError, ValueError, TypeError):
        return {}


def classify_candidate(post: XSourcePost, whitelist: dict[str, XSourceWhitelistEntry], *, now: datetime, freshness_hours: int = 72) -> XAmplificationCandidate:
    opportunity_id, project_name = _catalog_match(post.text)
    fingerprint = _fingerprint(post)
    base = dict(source_account=post.source_account, opportunity_id=opportunity_id, project_name=project_name, original_post_url=post.original_url, post_id=post.post_id, post_timestamp=post.posted_at, fingerprint=fingerprint, created_at=now.astimezone(UTC).isoformat())
    source = whitelist.get(post.source_account.casefold())
    try:
        fresh = now.astimezone(UTC) - _parse(post.posted_at) <= timedelta(hours=freshness_hours)
    except ValueError:
        fresh = False
    if source is None or not post.source_verified or not fresh or opportunity_id is None:
        return XAmplificationCandidate(**base, reason="source, freshness, or catalog relevance could not be verified", recommendation="IGNORE", confidence=0.0, priority="LOW", decision=AmplificationDecision.IGNORE)
    if UNSAFE_RE.search(post.text) or SPAM_RE.search(post.text):
        return XAmplificationCandidate(**base, reason="promotional or unsafe claim requires human review", recommendation="QUOTE", confidence=0.4, priority="LOW", decision=AmplificationDecision.MANUAL_REVIEW, suggested_quote=f"{project_name}: GamCryp tracks the evidence and economics. Review the full breakdown before acting.")
    return XAmplificationCandidate(**base, reason=f"verified {source.source_type} post directly references {project_name}", recommendation="REPOST", confidence=0.9, priority="HIGH", decision=AmplificationDecision.REPOST_NOW)


class XAmplificationOutbox:
    def __init__(self, path: Path = DEFAULT_OUTBOX, history_path: Path = DEFAULT_HISTORY):
        self.path, self.history_path = path, history_path

    def current(self) -> tuple[XAmplificationCandidate, ...]:
        payload = self._read(self.path, {"version": 1, "items": []})
        return tuple(XAmplificationCandidate.model_validate(item) for item in payload.get("items", []))

    def write(self, candidates: list[XAmplificationCandidate]) -> str:
        history = self._read(self.history_path, {"version": 1, "handled": []})
        handled = {str(item) for item in history.get("handled", [])}
        existing = {item.fingerprint for item in self.current()}
        usable = [item for item in candidates if item.decision != AmplificationDecision.IGNORE and item.fingerprint not in handled and item.fingerprint not in existing]
        if not usable:
            return "unchanged"
        current = list(self.current()) + usable
        self._write(self.path, {"version": 1, "items": [item.model_dump(mode="json") for item in current[:20]]})
        return "written"

    def mark_handled(self, fingerprint: str, *, repost_id: str | None = None, status: str = "manual_handled", now: datetime | None = None) -> None:
        payload = self._read(self.history_path, {"version": 1, "handled": []})
        if fingerprint not in payload["handled"]:
            payload["handled"].append(fingerprint)
        self._write(self.history_path, {"version": 1, "handled": payload["handled"], "last": {"fingerprint": fingerprint, "repost_id": repost_id, "status": status, "at": (now or datetime.now(UTC)).isoformat()}})
        self._write(self.path, {"version": 1, "items": [item.model_dump(mode="json") for item in self.current() if item.fingerprint != fingerprint]})

    @staticmethod
    def _read(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else default
        except (OSError, ValueError):
            return default

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


def load_feed(path: Path = DEFAULT_FEED) -> tuple[XSourcePost, ...]:
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return tuple(XSourcePost.model_validate(item) for item in payload.get("posts", []))
    except (OSError, ValueError, TypeError):
        return ()
