"""Deterministic discovery and admission logic; no provider calls here."""

from __future__ import annotations

import re
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import urlparse
from app.strategies.taxonomy import canonical_type


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Signal:
    name: str
    value: float | None
    source: str
    observed_at: datetime
    status: str
    explanation: str


@dataclass(frozen=True)
class EvidenceRecord:
    source_url: str
    source_role: str
    fact: str
    verified: bool
    observed_at: datetime
    notes: str = ""


@dataclass
class DiscoveryRecord:
    canonical_name: str
    aliases: list[str]
    category: str
    official_url: str | None
    discovery_source: str
    discovery_query: str | None = None
    first_seen_at: datetime = field(default_factory=_now)
    last_seen_at: datetime = field(default_factory=_now)
    signals: list[Signal] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    evidence_strength: str = "UNKNOWN"
    missing_evidence: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    validation_status: str = "DISCOVERED"
    matched_opportunity_id: str | None = None
    discovery_score: float = 0.0
    research_priority: str = "LOW"
    why_discovered: str = ""

    @property
    def discovery_id(self) -> str:
        return "discovery-" + sha256(normalize_entity(self.canonical_name).encode()).hexdigest()[:24]


@dataclass(frozen=True)
class AdmissionDecision:
    outcome: str
    reason: str
    missing_evidence: tuple[str, ...] = ()


def normalize_entity(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()
    value = re.sub(r"\b(io|app|network|official)\b", "", value)
    value = re.sub(r"\bget\s*", "", value)
    return re.sub(r"\s+", " ", value).strip()


def score_discovery(record: DiscoveryRecord) -> DiscoveryRecord:
    weights = {
        "search_momentum": 0.24,
        "social_momentum": 0.12,
        "youtube_outlier": 0.16,
        "recency": 0.10,
        "audience_fit": 0.14,
        "commercial_potential": 0.08,
        "visual_potential": 0.08,
        "novelty": 0.08,
    }
    positive = sum((signal.value or 0) * weights.get(signal.name, 0) for signal in record.signals)
    penalty = 8 * len(record.risk_flags) + 5 * len(record.missing_evidence)
    record.discovery_score = round(max(0.0, min(100.0, positive - penalty)), 2)
    record.research_priority = "HIGH" if record.discovery_score >= 60 else "MEDIUM" if record.discovery_score >= 30 else "LOW"
    record.why_discovered = "; ".join(signal.explanation for signal in record.signals if signal.value and signal.value >= 60) or "Recorded provider signal requires research."
    return record


def evaluate_admission(record: DiscoveryRecord) -> AdmissionDecision:
    try:
        canonical_type(record.category)
    except ValueError:
        return AdmissionDecision("QUARANTINE", "Invalid canonical opportunity type; research is required.", ("canonical opportunity_type",))
    parsed = urlparse(record.official_url or "")
    identity = bool(record.canonical_name.strip() and parsed.scheme == "https" and parsed.netloc)
    verified_facts = {e.fact for e in record.evidence if e.verified}
    if record.risk_flags or not identity:
        return AdmissionDecision("QUARANTINE", "Identity, URL, or risk conflict requires human review.", tuple(record.risk_flags or ["verified HTTPS official URL"]))
    required = {"identity", "participation", "reward_mechanism"}
    missing = sorted(required - verified_facts)
    if missing:
        return AdmissionDecision("KEEP_RESEARCHING", "Useful discovery is not yet sufficiently evidenced for admission.", tuple(missing))
    if {"entry_cost", "realizable_reward_value", "exit_path"}.issubset(verified_facts):
        return AdmissionDecision("AUTO_ADD_MODELED", "Identity, participation, reward, and reproducible economic inputs are evidenced.")
    return AdmissionDecision("AUTO_ADD_GUIDE", "Identity, participation, and reward mechanism are evidenced; ROI remains unavailable.")


def to_json(record: DiscoveryRecord) -> dict[str, object]:
    return json.loads(json.dumps(asdict(record), default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value))) | {"discovery_id": record.discovery_id}
