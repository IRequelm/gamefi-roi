"""Build a content opportunity inventory without generating content."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from sqlalchemy.engine import Engine

from app.search.canonical import CURATED_RANKING_PAGES, canonical_path
from app.strategies.catalog import (
    CATALOG_REVIEWED_AT,
    OpportunityCatalogEntry,
    StrategyCatalogEntry,
    get_outbound_destination,
    list_opportunities,
    list_strategies,
)

SCHEMA_VERSION = "content-inventory-v1"
INVENTORY_VERSION = "catalog-derived-v1"
READY = "READY"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"
LONG_FORM_MIN_WORDS = 1200
LONG_FORM_WORDS_PER_MINUTE = 150
LONG_FORM_MIN_SECONDS = 8 * 60
LONG_FORM_MIN_SECTIONS = 6


@dataclass(frozen=True)
class ContentInventoryItem:
    content_id: str
    source_url: str
    source_type: str
    opportunity_id: str | None
    strategy_id: str | None
    content_family: str
    evidence_status: str
    short_form_eligible: bool
    long_form_eligible: bool
    required_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    generation_status: str
    source_reference_fingerprint: str
    strategy_ids: tuple[str, ...] = ()
    freshness_status: str = "CATALOG_REVIEWED"
    destination_status: str = "NOT_APPLICABLE"
    publication_status: str = "CANONICAL_CATALOG_ROUTE"
    long_form_word_count: int = 0
    long_form_estimated_seconds: int = 0
    long_form_missing_evidence: tuple[str, ...] = ()


def build_content_inventory(engine: Engine | None = None) -> list[ContentInventoryItem]:
    opportunities = list_opportunities()
    if engine is not None:
        from app.storage.discovery import DiscoveryRepository
        static_ids = {opportunity.opportunity_id for opportunity in opportunities}
        opportunities = tuple(opportunities) + tuple(
            opportunity for opportunity in DiscoveryRepository(engine).dynamic_opportunities()
            if opportunity.opportunity_id not in static_ids
        )
    strategies = list_strategies()
    items: list[ContentInventoryItem] = _site_items()
    for opportunity in opportunities:
        items.extend(_opportunity_items(opportunity))
    for strategy in strategies:
        items.extend(_strategy_items(strategy, opportunities))
    return sorted(items, key=lambda item: item.content_id)


def write_content_inventory(path: Path) -> dict[str, Any]:
    items = build_content_inventory()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "inventory_version": INVENTORY_VERSION,
        "items": [asdict(item) for item in items],
        "summary": summarize_content_inventory(items),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def summarize_content_inventory(items: list[ContentInventoryItem]) -> dict[str, Any]:
    families: dict[str, int] = {}
    for item in items:
        families[item.content_family] = families.get(item.content_family, 0) + 1
    return {
        "total_topic_candidates": len(items),
        "ready_short_form_count": sum(item.evidence_status == READY and item.short_form_eligible for item in items),
        "ready_long_form_count": sum(item.evidence_status == READY and item.long_form_eligible for item in items),
        "partial_count": sum(item.evidence_status == PARTIAL for item in items),
        "blocked_count": sum(item.evidence_status == BLOCKED for item in items),
        "ready_short_only_count": sum(item.evidence_status == READY and item.short_form_eligible and not item.long_form_eligible for item in items),
        "by_content_family": dict(sorted(families.items())),
    }


def _site_items() -> list[ContentInventoryItem]:
    items = [
        _item("/", "SITE_PAGE", "HOW_TO_USE_GAMCRYP", ("The current public home and catalog navigation.",), (), READY, True, False),
        _item("/methodology", "SITE_PAGE", "METHODOLOGY_EXPLAINER", ("Published methodology and trust-boundary content.",), (), READY, True, False),
        _item("/methodology", "SITE_PAGE", "RISK_VS_CONFIDENCE", ("Published risk, confidence, and methodology explanations.",), (), READY, True, False),
    ]
    for page in CURATED_RANKING_PAGES:
        if "capital_max" in page.filters:
            items.append(
                _item(
                    canonical_path(page.path), "RANKING_PAGE", "LOW_COST_RANKING",
                    ("A published ranking page with current successful modeled snapshots.",),
                    ("Current ranking snapshot eligibility is evaluated at sitemap publication time.",),
                    PARTIAL, False, False,
                )
            )
    return items


def _opportunity_items(opportunity: OpportunityCatalogEntry) -> list[ContentInventoryItem]:
    guidance = opportunity.guidance
    items: list[ContentInventoryItem] = []
    freshness_status, destination_status, publication_status = _opportunity_context(opportunity)
    context_ready = all(status in {"CATALOG_REVIEWED", "VALIDATED", "CANONICAL_CATALOG_ROUTE"} for status in (freshness_status, destination_status, publication_status))
    long_words, long_sections = _long_form_material(opportunity, guidance)
    long_missing = _long_form_missing(long_words, long_sections, context_ready, freshness_status, destination_status, publication_status)
    rich_long_form = not long_missing
    fields = (
        ("HOW_TO_START", "how_to_start", "How to start instructions."),
        ("WHAT_YOU_NEED", "what_you_need", "Setup or purchase requirements."),
        ("HOW_YOU_EARN", "how_you_earn", "Documented earning mechanism."),
        ("HOW_TO_CLAIM_OR_EXIT", "how_to_exit_or_claim", "Documented claim or exit path."),
    )
    for family, attribute, required_text in fields:
        if guidance is None or not getattr(guidance, attribute):
            continue
        complete = all(getattr(guidance, field) for _, field, _ in fields)
        missing = []
        if not complete or not opportunity.official_source_references:
            missing.append("One or more structured guidance sections are incomplete.")
        if not context_ready:
            missing.extend(_context_missing(freshness_status, destination_status, publication_status))
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", family,
                (required_text, "At least one official source reference."),
                tuple(missing), READY if complete and opportunity.official_source_references and context_ready else PARTIAL,
                True, rich_long_form,
                opportunity_id=opportunity.opportunity_id,
                freshness_status=freshness_status, destination_status=destination_status, publication_status=publication_status,
                long_form_word_count=long_words, long_form_estimated_seconds=(long_words * 60) // LONG_FORM_WORDS_PER_MINUTE,
                long_form_missing_evidence=long_missing,
            )
        )
    if opportunity.roi_unavailable is not None:
        explanation = opportunity.roi_unavailable
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "WHY_ROI_UNAVAILABLE",
                ("Structured ROI-unavailable reason and missing evidence.",),
                () if explanation.missing_evidence else ("Missing-evidence list.",),
                READY if explanation.missing_evidence and context_ready else (PARTIAL if explanation.missing_evidence else BLOCKED),
                True, bool(explanation.missing_evidence and explanation.modeling_requirements and rich_long_form),
                opportunity_id=opportunity.opportunity_id,
                freshness_status=freshness_status, destination_status=destination_status, publication_status=publication_status,
                long_form_word_count=long_words, long_form_estimated_seconds=(long_words * 60) // LONG_FORM_WORDS_PER_MINUTE,
                long_form_missing_evidence=long_missing,
            )
        )
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "FINANCIAL_ROI",
                ("A modeled opportunity with reproducible financial evidence.",),
                ("GUIDE_ONLY opportunities cannot produce financial ROI claims without a validated strategy model.",),
                BLOCKED, False, False, opportunity_id=opportunity.opportunity_id,
            )
        )
    if guidance is not None and opportunity.opportunity_type == "DEPIN_NODE" and guidance.how_to_start and guidance.what_you_need:
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "DEPIN_SETUP",
                ("DePIN platform, setup, and hardware or account requirements.",),
                tuple(_context_missing(freshness_status, destination_status, publication_status)) if not context_ready else (),
                READY if context_ready else PARTIAL, True, rich_long_form, opportunity_id=opportunity.opportunity_id,
                freshness_status=freshness_status, destination_status=destination_status, publication_status=publication_status,
                long_form_word_count=long_words, long_form_estimated_seconds=(long_words * 60) // LONG_FORM_WORDS_PER_MINUTE,
                long_form_missing_evidence=long_missing,
            )
        )
    if len(opportunity.strategy_ids) >= 2:
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "STRATEGY_COMPARISON",
                ("At least two distinct modeled strategies under one opportunity.",),
                tuple(_context_missing(freshness_status, destination_status, publication_status)) if not context_ready else (),
                READY if context_ready else PARTIAL, True, rich_long_form,
                opportunity_id=opportunity.opportunity_id, strategy_ids=opportunity.strategy_ids,
                freshness_status=freshness_status, destination_status=destination_status, publication_status=publication_status,
                long_form_word_count=long_words, long_form_estimated_seconds=(long_words * 60) // LONG_FORM_WORDS_PER_MINUTE,
                long_form_missing_evidence=long_missing,
            )
        )
    return items


def _strategy_items(strategy: StrategyCatalogEntry, opportunities: tuple[OpportunityCatalogEntry, ...]) -> list[ContentInventoryItem]:
    # Strategy IDs remain supporting references on the single parent comparison item.
    return []


def _opportunity_context(opportunity: OpportunityCatalogEntry) -> tuple[str, str, str]:
    freshness_status = "CATALOG_REVIEWED" if CATALOG_REVIEWED_AT is not None else "MISSING"
    destination = get_outbound_destination(opportunity.outbound_destination_slugs[0]) if opportunity.outbound_destination_slugs else None
    destination_status = "VALIDATED" if destination is not None and CATALOG_REVIEWED_AT is not None and destination.is_active(now=CATALOG_REVIEWED_AT) else "MISSING"
    publication_status = "CANONICAL_CATALOG_ROUTE"
    return freshness_status, destination_status, publication_status


def _context_missing(freshness_status: str, destination_status: str, publication_status: str) -> list[str]:
    missing = []
    if freshness_status != "CATALOG_REVIEWED":
        missing.append("Catalog/source freshness evidence.")
    if destination_status != "VALIDATED":
        missing.append("Validated official destination liveness.")
    if publication_status != "CANONICAL_CATALOG_ROUTE":
        missing.append("Canonical/public sitemap publication evidence.")
    return missing


def _long_form_material(opportunity: OpportunityCatalogEntry, guidance: Any) -> tuple[int, int]:
    sections = [
        ("context", (opportunity.name, opportunity.feasibility_summary)),
        ("start", getattr(guidance, "how_to_start", ()) if guidance else ()),
        ("requirements", getattr(guidance, "what_you_need", ()) if guidance else ()),
        ("earning", getattr(guidance, "how_you_earn", ()) if guidance else ()),
        ("claim_exit", getattr(guidance, "how_to_exit_or_claim", ()) if guidance else ()),
    ]
    if opportunity.strategy_ids:
        sections.append(("strategies", tuple(strategy_id for strategy_id in opportunity.strategy_ids)))
    if opportunity.roi_unavailable:
        sections.append(("roi_status", (opportunity.roi_unavailable.reason, *(opportunity.roi_unavailable.missing_evidence or ()))) )
    words = sum(len(str(value).split()) for _, values in sections for value in values if value)
    return words, sum(bool(tuple(value for value in values if value)) for _, values in sections)


def _long_form_missing(words: int, sections: int, context_ready: bool, freshness_status: str, destination_status: str, publication_status: str) -> tuple[str, ...]:
    missing: list[str] = []
    if words < LONG_FORM_MIN_WORDS:
        missing.append(f"At least {LONG_FORM_MIN_WORDS} evidence-backed narration words; available {words}.")
    if sections < LONG_FORM_MIN_SECTIONS:
        missing.append(f"At least {LONG_FORM_MIN_SECTIONS} substantive supported sections; available {sections}.")
    if not context_ready:
        missing.extend(_context_missing(freshness_status, destination_status, publication_status))
    return tuple(missing)


def _item(
    source_url: str, source_type: str, family: str, required: tuple[str, ...], missing: tuple[str, ...],
    status: str, short: bool, long: bool, *, opportunity_id: str | None = None,
    strategy_id: str | None = None, strategy_ids: tuple[str, ...] = (),
    freshness_status: str = "CATALOG_REVIEWED", destination_status: str = "NOT_APPLICABLE",
    publication_status: str = "CANONICAL_CATALOG_ROUTE",
    long_form_word_count: int = 0, long_form_estimated_seconds: int = 0,
    long_form_missing_evidence: tuple[str, ...] = (),
) -> ContentInventoryItem:
    source_fingerprint = hashlib.sha256(json.dumps({
        "source_url": canonical_path(source_url), "source_type": source_type,
        "opportunity_id": opportunity_id, "strategy_id": strategy_id, "strategy_ids": strategy_ids,
        "content_family": family, "required": required, "missing": missing,
        "freshness_status": freshness_status, "destination_status": destination_status,
        "publication_status": publication_status,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    scope = strategy_id or opportunity_id or source_url.strip("/").replace("/", "-") or "home"
    return ContentInventoryItem(
        content_id=f"inventory-{family.lower()}-{scope}", source_url=canonical_path(source_url), source_type=source_type,
        opportunity_id=opportunity_id, strategy_id=strategy_id, content_family=family, evidence_status=status,
        short_form_eligible=short, long_form_eligible=long, required_evidence=required, missing_evidence=missing,
        generation_status="NOT_STARTED", source_reference_fingerprint=source_fingerprint, strategy_ids=strategy_ids,
        freshness_status=freshness_status, destination_status=destination_status,
        publication_status=publication_status,
        long_form_word_count=long_form_word_count, long_form_estimated_seconds=long_form_estimated_seconds,
        long_form_missing_evidence=long_form_missing_evidence,
    )
