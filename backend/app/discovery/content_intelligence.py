"""Explainable content scoring and platform-native editorial briefs."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime

from app.discovery.engine import DiscoveryRecord


@dataclass(frozen=True)
class EditorialBrief:
    candidate_id: str
    opportunity_id: str | None
    strategy_ids: tuple[str, ...]
    platform: str
    content_score: float
    confidence: str
    why_now: tuple[str, ...]
    editorial_angle: str
    hook: str
    title_candidates: tuple[str, ...]
    required_facts: tuple[str, ...]
    required_visuals: tuple[str, ...]
    cta: str
    prohibited_claims: tuple[str, ...]
    source_references: tuple[str, ...]
    preferred_publish_window: str
    decision_explanation: str


def build_editorial_brief(record: DiscoveryRecord, *, platform: str = "X_ONLY") -> EditorialBrief:
    score = round(record.discovery_score, 2)
    angle = "Everyone is talking about this — what is actually verified?" if record.validation_status != "VERIFIED" else "How it actually works"
    return EditorialBrief(
        candidate_id=record.discovery_id,
        opportunity_id=record.matched_opportunity_id,
        strategy_ids=(),
        platform=platform,
        content_score=score,
        confidence="MEDIUM" if record.evidence_strength in {"MEDIUM", "STRONG"} else "LOW",
        why_now=tuple(filter(None, (record.why_discovered, "Verified uncertainty is itself a useful editorial angle."))),
        editorial_angle=angle,
        hook=f"{record.canonical_name}: what can we actually verify?",
        title_candidates=(f"{record.canonical_name}: what is actually verified?", f"{record.canonical_name} explained with evidence"),
        required_facts=tuple(e.fact for e in record.evidence if e.verified),
        required_visuals=("official product visual when available", "GamCryp evidence card"),
        cta="Review the source-backed GamCryp opportunity page.",
        prohibited_claims=("guaranteed earnings", "invented ROI", "unsupported token price", "investment advice"),
        source_references=tuple(e.source_url for e in record.evidence if e.verified),
        preferred_publish_window="20:00–22:00 Europe/Istanbul",
        decision_explanation="Score is a discovery/content priority, not ROI or a financial recommendation.",
    )


def brief_json(brief: EditorialBrief) -> dict[str, object]:
    return asdict(brief)
