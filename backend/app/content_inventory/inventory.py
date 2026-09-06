"""Build a content opportunity inventory without generating content."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.search.canonical import CURATED_RANKING_PAGES, canonical_path
from app.strategies.catalog import OpportunityCatalogEntry, StrategyCatalogEntry, list_opportunities, list_strategies

SCHEMA_VERSION = "content-inventory-v1"
INVENTORY_VERSION = "catalog-derived-v1"
READY = "READY"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"


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


def build_content_inventory() -> list[ContentInventoryItem]:
    opportunities = list_opportunities()
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
        "by_content_family": dict(sorted(families.items())),
    }


def _site_items() -> list[ContentInventoryItem]:
    items = [
        _item("/", "SITE_PAGE", "HOW_TO_USE_GAMCRYP", ("The current public home and catalog navigation.",), (), READY, True, True),
        _item("/methodology", "SITE_PAGE", "METHODOLOGY_EXPLAINER", ("Published methodology and trust-boundary content.",), (), READY, True, True),
        _item("/methodology", "SITE_PAGE", "RISK_VS_CONFIDENCE", ("Published risk, confidence, and methodology explanations.",), (), READY, True, True),
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
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", family,
                (required_text, "At least one official source reference."),
                () if complete and opportunity.official_source_references else ("One or more structured guidance sections are incomplete.",),
                READY if complete and opportunity.official_source_references else PARTIAL,
                True, complete and bool(opportunity.official_source_references),
                opportunity_id=opportunity.opportunity_id,
            )
        )
    if opportunity.roi_unavailable is not None:
        explanation = opportunity.roi_unavailable
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "WHY_ROI_UNAVAILABLE",
                ("Structured ROI-unavailable reason and missing evidence.",),
                () if explanation.missing_evidence else ("Missing-evidence list.",),
                READY if explanation.missing_evidence else BLOCKED,
                True, bool(explanation.missing_evidence and explanation.modeling_requirements),
                opportunity_id=opportunity.opportunity_id,
            )
        )
    if guidance is not None and opportunity.opportunity_type == "DEPIN_NODE" and guidance.how_to_start and guidance.what_you_need:
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "DEPIN_SETUP",
                ("DePIN platform, setup, and hardware or account requirements.",), (), READY, True,
                bool(guidance.how_you_earn and guidance.how_to_exit_or_claim), opportunity_id=opportunity.opportunity_id,
            )
        )
    if len(opportunity.strategy_ids) >= 2:
        items.append(
            _item(
                f"/opportunities/{opportunity.opportunity_id}", "OPPORTUNITY_CATALOG", "STRATEGY_COMPARISON",
                ("At least two distinct modeled strategies under one opportunity.",), (), READY, True, True,
                opportunity_id=opportunity.opportunity_id, strategy_ids=opportunity.strategy_ids,
            )
        )
    return items


def _strategy_items(strategy: StrategyCatalogEntry, opportunities: tuple[OpportunityCatalogEntry, ...]) -> list[ContentInventoryItem]:
    opportunity = next((item for item in opportunities if item.opportunity_id == strategy.opportunity_id), None)
    if opportunity is None or not opportunity.strategy_ids:
        return []
    return [
        _item(
            f"/strategies/{strategy.strategy_id}", "MODELED_STRATEGY", "STRATEGY_COMPARISON",
            ("A modeled strategy definition and its current snapshot evidence.",),
            ("A current successful snapshot is required before making financial claims.",),
            PARTIAL, False, False, opportunity_id=strategy.opportunity_id, strategy_id=strategy.strategy_id,
            strategy_ids=(strategy.strategy_id,),
        )
    ]


def _item(
    source_url: str, source_type: str, family: str, required: tuple[str, ...], missing: tuple[str, ...],
    status: str, short: bool, long: bool, *, opportunity_id: str | None = None,
    strategy_id: str | None = None, strategy_ids: tuple[str, ...] = (),
) -> ContentInventoryItem:
    source_fingerprint = hashlib.sha256(json.dumps({
        "source_url": canonical_path(source_url), "source_type": source_type,
        "opportunity_id": opportunity_id, "strategy_id": strategy_id, "strategy_ids": strategy_ids,
        "content_family": family, "required": required, "missing": missing,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    scope = strategy_id or opportunity_id or source_url.strip("/").replace("/", "-") or "home"
    return ContentInventoryItem(
        content_id=f"inventory-{family.lower()}-{scope}", source_url=canonical_path(source_url), source_type=source_type,
        opportunity_id=opportunity_id, strategy_id=strategy_id, content_family=family, evidence_status=status,
        short_form_eligible=short, long_form_eligible=long, required_evidence=required, missing_evidence=missing,
        generation_status="NOT_STARTED", source_reference_fingerprint=source_fingerprint, strategy_ids=strategy_ids,
    )
