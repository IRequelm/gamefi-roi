"""Build structured content packages from READY inventory items only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from sqlalchemy.engine import Engine

from app.content_inventory.inventory import ContentInventoryItem, READY, build_content_inventory
from app.content_inventory.inventory import LONG_FORM_MIN_SECTIONS, LONG_FORM_MIN_SECONDS, LONG_FORM_MIN_WORDS, LONG_FORM_WORDS_PER_MINUTE
from app.strategies.catalog import OpportunityCatalogEntry, StrategyCatalogEntry, get_opportunity, get_strategy, list_opportunities

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
    narration_sections: tuple[dict[str, Any], ...]
    estimated_narration_words: int
    estimated_duration_seconds: int
    visual_asset_requirements: tuple[str, ...]
    thumbnail_brief: str
    generation_status: str
    evidence_fingerprint: str


def build_content_packages(*, ready_only: bool = True, engine: Engine | None = None) -> list[ContentPackage]:
    inventory = build_content_inventory(engine=engine)
    opportunities = {item.opportunity_id: item for item in list_opportunities()}
    if engine is not None:
        from app.storage.discovery import DiscoveryRepository
        opportunities.update({item.opportunity_id: item for item in DiscoveryRepository(engine).dynamic_opportunities()})
    packages: list[ContentPackage] = []
    for item in inventory:
        if ready_only and item.evidence_status != READY:
            continue
        for output_format in _eligible_formats(item):
            package = _build_package(item, output_format, opportunities=opportunities)
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
    if package.format == "LONG_FORM" and (
        len(package.narration_sections) < LONG_FORM_MIN_SECTIONS
        or package.estimated_narration_words < LONG_FORM_MIN_WORDS
        or package.estimated_duration_seconds < LONG_FORM_MIN_SECONDS
    ):
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
        # A truthful negated warning such as "does not guarantee traffic" must
        # remain publishable. Reject promise language, not the word itself.
        if any(term in text for term in ("guaranteed", "risk-free", "you will earn", "buy this", "i recommend", "guaranteed return")):
            return False
    if package.format == "LONG_FORM":
        if len({section.get("text") for section in package.narration_sections}) != len(package.narration_sections):
            return False
        if any(not section.get("text") or not section.get("evidence_paths") for section in package.narration_sections):
            return False
    return bool(package.required_source_references and package.evidence_fingerprint)


def _eligible_formats(item: ContentInventoryItem) -> tuple[str, ...]:
    formats = []
    if item.short_form_eligible:
        formats.append("SHORT_FORM")
    if item.long_form_eligible:
        formats.append("LONG_FORM")
    return tuple(formats)


def _build_package(item: ContentInventoryItem, output_format: str, *, opportunities: dict[str, OpportunityCatalogEntry] | None = None) -> ContentPackage:
    opportunity = (opportunities or {}).get(item.opportunity_id) if item.opportunity_id else None
    if opportunity is None and item.opportunity_id:
        opportunity = get_opportunity(item.opportunity_id)
    strategies = tuple(get_strategy(strategy_id) for strategy_id in item.strategy_ids if get_strategy(strategy_id) is not None)
    references = _references(opportunity, item)
    points = _talking_points(item, opportunity, strategies)
    narration_sections = _narration_sections(item, points)
    sections = _outline(item, output_format, narration_sections)
    hook = _hook(item, opportunity, strategies)
    cta = _cta(item, opportunity)
    script_text = " ".join([hook, *(str(section["text"]) for section in narration_sections), cta])
    estimated_words = len(script_text.split())
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
        hook=hook,
        factual_talking_points=tuple(points),
        required_source_references=tuple(references),
        prohibited_claims=("guaranteed returns", "investment advice", "risk-free earnings", "unsupported token prices", "invented hardware requirements"),
        cta=cta,
        narration_script_outline=tuple(sections),
        narration_sections=tuple(narration_sections),
        estimated_narration_words=estimated_words,
        estimated_duration_seconds=(estimated_words * 60) // LONG_FORM_WORDS_PER_MINUTE,
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


def _outline(item: ContentInventoryItem, output_format: str, sections: list[dict[str, Any]]) -> list[str]:
    if output_format == "SHORT_FORM":
        return ["Hook", *[str(section["text"]) for section in sections[:4]], "Evidence-aware CTA"]
    return ["Hook", *[str(section["title"]) for section in sections], "Evidence-aware CTA"]


def _narration_sections(item: ContentInventoryItem, points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if item.content_family == "STRATEGY_COMPARISON":
        titles = ["Strategy comparison"] * len(points)
    else:
        titles = ["Evidence-backed detail"] * len(points)
    return [{"title": title, "text": str(point["text"]), "evidence_paths": tuple(point["evidence_paths"])} for title, point in zip(titles, points)]


def _titles(item: ContentInventoryItem, opportunity: OpportunityCatalogEntry | None) -> tuple[str, ...]:
    name = opportunity.name if opportunity is not None else "GamCryp"
    family = item.content_family.replace("_", " ").title()
    return (f"{name}: {family}", f"GamCryp {family}: {name}")


def _hook(item: ContentInventoryItem, opportunity: OpportunityCatalogEntry | None, strategies: tuple[StrategyCatalogEntry | None, ...] = ()) -> str:
    name = opportunity.name if opportunity is not None else "GamCryp"
    if item.content_family == "WHY_ROI_UNAVAILABLE":
        return "Can this actually make money? We cannot verify it yet."
    if item.content_family == "DEPIN_SETUP" or opportunity and opportunity.opportunity_type == "DEPIN_NODE":
        # Keep the spoken/visual opening short enough for a mobile-safe first
        # card. The longer setup context belongs in later scenes.
        return "Can your PC earn while you are away?"
    if item.content_family in {"STRATEGY_COMPARISON", "LOW_COST_RANKING"} and strategies:
        return "The headline return is only the start. What does the catch look like?"
    if opportunity and opportunity.opportunity_type == "GAME":
        return "Can this game actually pay you? Let us check the earning path."
    if item.content_family == "METHODOLOGY_EXPLAINER":
        return "They say it earns. We check what can actually be measured."
    if item.content_family == "RISK_VS_CONFIDENCE":
        return "High confidence does not mean low risk. Here is the difference."
    return f"What would it take for {name} to actually earn?"


def _cta(item: ContentInventoryItem, opportunity: OpportunityCatalogEntry | None) -> str:
    if item.content_family == "WHY_ROI_UNAVAILABLE":
        return "GamCryp shows what is missing instead of inventing a number. See the full breakdown on GamCryp."
    if item.content_family in {"METHODOLOGY_EXPLAINER", "RISK_VS_CONFIDENCE", "HOW_TO_USE_GAMCRYP"}:
        return "We check the economics so you do not have to. Full framework on GamCryp."
    return "They say it earns. We check the numbers. See the full breakdown on GamCryp."


def _visuals(item: ContentInventoryItem) -> tuple[str, ...]:
    if item.content_family == "DEPIN_SETUP":
        return ("Official opportunity logo", "Official product, dashboard, device, or node visual", "Setup requirements card", "Evidence metric card", "GamCryp CTA end card")
    if item.content_family == "WHY_ROI_UNAVAILABLE":
        return ("Official opportunity logo", "Official product, dashboard, device, or game visual", "Evidence-gap card", "Missing-input list", "GamCryp CTA end card")
    return ("Official opportunity logo", "Official product, dashboard, device, or game visual", "Evidence reference card", "Key metric card", "GamCryp CTA end card")


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
