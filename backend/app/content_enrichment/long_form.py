"""Build deterministic, source-bound long-form research plans.

This module plans deeper content from catalog evidence. It never invents facts,
prices, earnings, or missing sections, and it never changes admission or ROI.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.content_inventory.inventory import LONG_FORM_MIN_SECTIONS, LONG_FORM_MIN_WORDS, LONG_FORM_WORDS_PER_MINUTE
from app.strategies.catalog import CATALOG_REVIEWED_AT, OpportunityCatalogEntry, get_strategy, list_opportunities

SCHEMA_VERSION = "long-form-enrichment-v1"
DEFAULT_CANDIDATE_LIMIT = 35


@dataclass(frozen=True)
class EnrichmentSection:
    section_id: str
    supported_claims: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    source_references: tuple[dict[str, str], ...]
    unresolved_evidence: tuple[str, ...]
    word_budget_estimate: int


@dataclass(frozen=True)
class LongFormEnrichment:
    opportunity_id: str
    opportunity_name: str
    opportunity_type: str
    admission_mode: str
    data_feasibility_status: str
    canonical_source_set: tuple[dict[str, str], ...]
    reviewed_at: str
    sections: tuple[EnrichmentSection, ...]
    supported_claims: tuple[str, ...]
    unresolved_evidence: tuple[str, ...]
    word_budget_estimate: int
    estimated_duration_seconds: int
    long_form_eligible: bool
    eligibility_reasons: tuple[str, ...]


def build_long_form_enrichment(*, limit: int = DEFAULT_CANDIDATE_LIMIT, opportunities: tuple[OpportunityCatalogEntry, ...] | None = None) -> list[LongFormEnrichment]:
    if limit < 1:
        raise ValueError("long-form enrichment limit must be positive")
    candidates = sorted(opportunities or list_opportunities(), key=_candidate_sort_key)[:limit]
    return [_build_entry(opportunity) for opportunity in candidates]


def write_long_form_enrichment(path: Path, *, limit: int = DEFAULT_CANDIDATE_LIMIT) -> dict[str, Any]:
    entries = build_long_form_enrichment(limit=limit)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "reviewed_at": CATALOG_REVIEWED_AT.isoformat(),
        "candidate_limit": limit,
        "candidates": [asdict(entry) for entry in entries],
        "summary": {
            "candidate_count": len(entries),
            "eligible_count": sum(entry.long_form_eligible for entry in entries),
            "blocked_count": sum(not entry.long_form_eligible for entry in entries),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _candidate_sort_key(opportunity: OpportunityCatalogEntry) -> tuple[int, int, int, str]:
    guidance = opportunity.guidance
    guidance_count = sum(bool(getattr(guidance, field, ())) for field in ("how_to_start", "what_you_need", "how_you_earn", "how_to_exit_or_claim")) if guidance else 0
    return (0 if opportunity.strategy_ids else 1, 0 if opportunity.official_source_references else 1, -guidance_count, opportunity.opportunity_id)


def _build_entry(opportunity: OpportunityCatalogEntry) -> LongFormEnrichment:
    sources = tuple({"label": ref.label, "url": ref.url, "source_role": ref.source_role} for ref in opportunity.official_source_references)
    sections: list[EnrichmentSection] = []
    _add_section(sections, "what_it_is", (opportunity.feasibility_summary,), ("opportunity.feasibility_summary",), sources)
    guidance = opportunity.guidance
    for section_id, field, evidence_path in (
        ("how_to_start", "how_to_start", "opportunity.guidance.how_to_start"),
        ("what_you_need", "what_you_need", "opportunity.guidance.what_you_need"),
        ("how_you_earn", "how_you_earn", "opportunity.guidance.how_you_earn"),
        ("claim_or_exit", "how_to_exit_or_claim", "opportunity.guidance.how_to_exit_or_claim"),
    ):
        values = tuple(getattr(guidance, field, ()) or ()) if guidance else ()
        _add_section(sections, section_id, values, (evidence_path,), sources, missing=f"{field.replace('_', ' ')} evidence is not present in the catalog.")
    if opportunity.strategy_ids:
        claims = tuple(
            f"{get_strategy(strategy_id).name}: {get_strategy(strategy_id).description}"
            for strategy_id in opportunity.strategy_ids
            if get_strategy(strategy_id) is not None
        )
        _add_section(sections, "modeled_economics", claims, tuple(f"strategy.{strategy_id}" for strategy_id in opportunity.strategy_ids), sources, missing="Strategy-level live snapshot evidence is required before making current financial claims.")
    elif opportunity.roi_unavailable is not None:
        explanation = opportunity.roi_unavailable
        claims = (explanation.reason, *(explanation.missing_evidence or ()))
        _add_section(sections, "roi_or_value_status", claims, ("opportunity.roi_unavailable.reason", "opportunity.roi_unavailable.missing_evidence"), sources, missing="A lawful, reproducible financial value route is not currently evidenced.")
    _add_section(
        sections,
        "risk_confidence_freshness",
        (f"Data feasibility status: {opportunity.data_feasibility_status}.", f"Value realization status: {opportunity.value_realization_status}.", f"Catalog review date: {CATALOG_REVIEWED_AT.date().isoformat()} UTC."),
        ("opportunity.data_feasibility_status", "opportunity.value_realization_status", "catalog.reviewed_at"),
        sources,
    )
    all_claims = tuple(claim for section in sections for claim in section.supported_claims)
    unresolved = tuple(dict.fromkeys(value for section in sections for value in section.unresolved_evidence))
    words = sum(section.word_budget_estimate for section in sections)
    substantive = sum(bool(section.supported_claims) for section in sections)
    reasons = []
    if words < LONG_FORM_MIN_WORDS:
        reasons.append(f"At least {LONG_FORM_MIN_WORDS} evidence-backed narration words; available {words}.")
    if substantive < LONG_FORM_MIN_SECTIONS:
        reasons.append(f"At least {LONG_FORM_MIN_SECTIONS} substantive supported sections; available {substantive}.")
    if unresolved:
        reasons.append("Unresolved evidence remains; do not pad or invent content.")
    return LongFormEnrichment(
        opportunity_id=opportunity.opportunity_id,
        opportunity_name=opportunity.name,
        opportunity_type=opportunity.opportunity_type,
        admission_mode=opportunity.admission_mode,
        data_feasibility_status=opportunity.data_feasibility_status,
        canonical_source_set=sources,
        reviewed_at=CATALOG_REVIEWED_AT.isoformat(),
        sections=tuple(sections),
        supported_claims=all_claims,
        unresolved_evidence=unresolved,
        word_budget_estimate=words,
        estimated_duration_seconds=(words * 60) // LONG_FORM_WORDS_PER_MINUTE,
        long_form_eligible=not reasons,
        eligibility_reasons=tuple(reasons),
    )


def _add_section(sections: list[EnrichmentSection], section_id: str, claims: tuple[str, ...], evidence_paths: tuple[str, ...], sources: tuple[dict[str, str], ...], *, missing: str | None = None) -> None:
    claims = tuple(str(claim).strip() for claim in claims if str(claim).strip())
    sections.append(EnrichmentSection(section_id, claims, evidence_paths if claims else (), sources if claims else (), (missing,) if missing and not claims else (), sum(len(claim.split()) for claim in claims)))
