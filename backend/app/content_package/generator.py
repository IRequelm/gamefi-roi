"""Build structured content packages from READY inventory items only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.content_inventory.inventory import ContentInventoryItem, READY, build_content_inventory
from app.strategies.catalog import OpportunityCatalogEntry, StrategyCatalogEntry, get_opportunity, get_strategy

PACKAGE_SCHEMA_VERSION = "content-package-v1"


@dataclass(frozen=True)
class ContentPackage:
    package_id: str
    source_inventory_item_id: str
    format: str
    content_family: str
    canonical_source_url: str
    opportunity_id: str | None
    strategy_ids: tuple[str, ...]
    title_candidates: tuple[str, ...]
    hook: str
    factual_talking_points: tuple[dict[str, Any], ...]
    required_source_references: tuple[dict[str, str], ...]
    prohibited_claims: tuple[str, ...]
    cta: str
    narration_script_outline: tuple[str, ...]
    visual_asset_requirements: tuple[str, ...]
    thumbnail_brief: str
    generation_status: str
    evidence_fingerprint: str


def build_content_packages(*, ready_only: bool = True) -> list[ContentPackage]:
    inventory = build_content_inventory()
    packages: list[ContentPackage] = []
    for item in inventory:
        if ready_only and item.evidence_status != READY:
            continue
        for output_format in _eligible_formats(item):
            package = _build_package(item, output_format)
            packages.append(package if validate_package(package) else _not_ready(package))
    return sorted(packages, key=lambda package: package.package_id)


def write_content_packages(path: Path, *, ready_only: bool = True) -> dict[str, Any]:
    packages = build_content_packages(ready_only=ready_only)
    payload = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "packages": [asdict(package) for package in packages],
        "summary": summarize_content_packages(packages),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def summarize_content_packages(packages: list[ContentPackage]) -> dict[str, Any]:
    return {
        "generated_short_packages": sum(package.format == "SHORT_FORM" and package.generation_status == "READY_FOR_REVIEW" for package in packages),
        "generated_long_packages": sum(package.format == "LONG_FORM" and package.generation_status == "READY_FOR_REVIEW" for package in packages),
        "not_ready_packages": sum(package.generation_status == "NOT_READY" for package in packages),
        "by_content_family": dict(sorted(_count_families(packages).items())),
        "evidence_validation_failures": sum(package.generation_status == "NOT_READY" for package in packages),
    }


def validate_package(package: ContentPackage) -> bool:
    if package.format not in {"SHORT_FORM", "LONG_FORM"} or not package.factual_talking_points:
        return False
    if package.format == "LONG_FORM" and len(package.narration_script_outline) < 5:
        return False
    if package.content_family == "FINANCIAL_ROI":
        return False
    for point in package.factual_talking_points:
        evidence_paths = point.get("evidence_paths") or ()
        if not point.get("text") or not evidence_paths:
            return False
        if not all(str(path).startswith(("opportunity.", "strategy.", "/")) for path in evidence_paths):
            return False
        text = str(point["text"]).lower()
        if any(term in text for term in ("guarantee", "risk-free", "you will earn", "buy this", "i recommend", "guaranteed return")):
            return False
    return bool(package.required_source_references and package.evidence_fingerprint)


def _eligible_formats(item: ContentInventoryItem) -> tuple[str, ...]:
    formats = []
    if item.short_form_eligible:
        formats.append("SHORT_FORM")
    if item.long_form_eligible:
        formats.append("LONG_FORM")
    return tuple(formats)


def _build_package(item: ContentInventoryItem, output_format: str) -> ContentPackage:
    opportunity = get_opportunity(item.opportunity_id) if item.opportunity_id else None
    strategies = tuple(get_strategy(strategy_id) for strategy_id in item.strategy_ids if get_strategy(strategy_id) is not None)
    references = _references(opportunity, item)
    points = _talking_points(item, opportunity, strategies)
    sections = _outline(item, output_format, points)
    canonical = item.source_url
    evidence = hashlib.sha256(json.dumps({
        "inventory": item.content_id,
        "source": item.source_reference_fingerprint,
        "points": points,
        "references": references,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    package_id = f"package-{output_format.lower()}-{item.content_id.removeprefix('inventory-')}"
    return ContentPackage(
        package_id=package_id,
        source_inventory_item_id=item.content_id,
        format=output_format,
        content_family=item.content_family,
        canonical_source_url=canonical,
        opportunity_id=item.opportunity_id,
        strategy_ids=item.strategy_ids,
        title_candidates=_titles(item, opportunity),
        hook=_hook(item, opportunity),
        factual_talking_points=tuple(points),
        required_source_references=tuple(references),
        prohibited_claims=("guaranteed returns", "investment advice", "risk-free earnings", "unsupported token prices", "invented hardware requirements"),
        cta=f"Review the evidence on {canonical}.",
        narration_script_outline=tuple(sections),
        visual_asset_requirements=_visuals(item),
        thumbnail_brief=f"Clean GamCryp title card focused on {item.content_family.replace('_', ' ').lower()} with no financial promise.",
        generation_status="READY_FOR_REVIEW",
        evidence_fingerprint=evidence,
    )


def _not_ready(package: ContentPackage) -> ContentPackage:
    return ContentPackage(**{**asdict(package), "generation_status": "NOT_READY"})


def _references(opportunity: OpportunityCatalogEntry | None, item: ContentInventoryItem) -> list[dict[str, str]]:
    if opportunity is not None:
        return [{"label": reference.label, "url": reference.url} for reference in opportunity.official_source_references]
    return [{"label": "GamCryp canonical page", "url": item.source_url}]


def _talking_points(item: ContentInventoryItem, opportunity: OpportunityCatalogEntry | None, strategies: tuple[StrategyCatalogEntry | None, ...]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    if opportunity is None:
        return [{"text": _site_fact(item), "evidence_paths": [item.source_url]}]
    if item.content_family == "WHY_ROI_UNAVAILABLE" and opportunity.roi_unavailable is not None:
        explanation = opportunity.roi_unavailable
        points.append({"text": explanation.reason, "evidence_paths": ["opportunity.roi_unavailable.reason"]})
        for value in explanation.missing_evidence or ():
            points.append({"text": f"Missing evidence: {value}", "evidence_paths": ["opportunity.roi_unavailable.missing_evidence"]})
        return points
    if item.content_family == "STRATEGY_COMPARISON":
        points.append({"text": f"{opportunity.name} has {len(strategies) or len(item.strategy_ids)} modeled strategies available for comparison.", "evidence_paths": ["opportunity.strategy_ids"]})
        for strategy_id in item.strategy_ids:
            strategy = get_strategy(strategy_id)
            if strategy is not None:
                points.append({"text": f"{strategy.name}: {strategy.description}", "evidence_paths": [f"strategy.{strategy_id}.description"]})
        return points
    guidance = opportunity.guidance
    attribute = {
        "HOW_TO_START": "how_to_start", "WHAT_YOU_NEED": "what_you_need", "HOW_YOU_EARN": "how_you_earn", "HOW_TO_CLAIM_OR_EXIT": "how_to_exit_or_claim",
        "DEPIN_SETUP": "how_to_start",
    }.get(item.content_family)
    values = getattr(guidance, attribute, ()) if guidance is not None and attribute else ()
    for value in values:
        points.append({"text": value, "evidence_paths": [f"opportunity.guidance.{attribute}"]})
    if item.content_family == "DEPIN_SETUP" and guidance is not None:
        for value in guidance.what_you_need or ():
            points.append({"text": value, "evidence_paths": ["opportunity.guidance.what_you_need"]})
    return points


def _outline(item: ContentInventoryItem, output_format: str, points: list[dict[str, Any]]) -> list[str]:
    if output_format == "SHORT_FORM":
        return ["Hook", *[str(point["text"]) for point in points[:4]], "Evidence-aware CTA"]
    return ["Hook", "Opportunity or method context", "How to start and what you need", "How the mechanism works", "Claim, exit, or limitation", "Risk, confidence, and evidence boundary", "Practical summary", "Evidence-aware CTA"]


def _titles(item: ContentInventoryItem, opportunity: OpportunityCatalogEntry | None) -> tuple[str, ...]:
    name = opportunity.name if opportunity is not None else "GamCryp"
    family = item.content_family.replace("_", " ").title()
    return (f"{name}: {family}", f"GamCryp {family}: {name}")


def _hook(item: ContentInventoryItem, opportunity: OpportunityCatalogEntry | None) -> str:
    name = opportunity.name if opportunity is not None else "GamCryp"
    return f"Start with the evidence behind {name}'s {item.content_family.replace('_', ' ').lower()} topic."


def _visuals(item: ContentInventoryItem) -> tuple[str, ...]:
    if item.content_family == "DEPIN_SETUP":
        return ("Opportunity identity card", "Setup requirements card", "Source reference end card")
    if item.content_family == "WHY_ROI_UNAVAILABLE":
        return ("Evidence-gap card", "Missing-input list", "Methodology end card")
    return ("Clean canonical page or catalog card", "Evidence reference card", "GamCryp CTA end card")


def _site_fact(item: ContentInventoryItem) -> str:
    return {
        "HOW_TO_USE_GAMCRYP": "GamCryp's public home explains how to navigate the catalog and inspect available opportunity information.",
        "METHODOLOGY_EXPLAINER": "GamCryp's methodology page explains strategy-specific evidence, ROI boundaries, risk, confidence, and freshness.",
        "RISK_VS_CONFIDENCE": "GamCryp presents risk and confidence as separate concepts for economic risk and model or data confidence.",
    }.get(item.content_family, "GamCryp provides a canonical public page for this topic.")


def _count_families(packages: list[ContentPackage]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for package in packages:
        counts[package.content_family] = counts.get(package.content_family, 0) + 1
    return counts
