from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.content_inventory.inventory import BLOCKED, PARTIAL, READY, build_content_inventory, summarize_content_inventory
from app.search.canonical import CURATED_RANKING_PAGES
from app.strategies.catalog import list_opportunities, list_strategies


def test_inventory_is_deterministic_and_has_unique_content_ids() -> None:
    first = [asdict(item) for item in build_content_inventory()]
    second = [asdict(item) for item in build_content_inventory()]

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert len({item["content_id"] for item in first}) == len(first)


def test_guide_only_opportunity_supports_how_to_content_but_not_financial_roi() -> None:
    items = build_content_inventory()
    guide = [item for item in items if item.opportunity_id == "hivemapper"]
    grass = [item for item in items if item.opportunity_id == "grass"]

    assert any(item.content_family == "HOW_TO_START" and item.evidence_status == READY for item in guide)
    assert any(item.content_family == "DEPIN_SETUP" for item in guide)
    assert not any(item.content_family in {"ROI", "ROI_CLAIM"} and item.evidence_status == READY for item in grass)
    assert any(item.content_family == "FINANCIAL_ROI" and item.evidence_status == BLOCKED for item in grass)
    assert any(item.content_family == "WHY_ROI_UNAVAILABLE" for item in grass)


def test_modeled_strategy_comparison_and_missing_evidence_are_explicit() -> None:
    items = build_content_inventory()

    assert any(
        item.opportunity_id == "defi-kingdoms" and item.content_family == "STRATEGY_COMPARISON" and item.evidence_status == READY
        for item in items
    )
    assert any(item.content_family == "LOW_COST_RANKING" and item.evidence_status == PARTIAL for item in items)


def test_long_form_requires_a_real_evidence_backed_budget() -> None:
    items = build_content_inventory()

    assert summarize_content_inventory(items)["ready_long_form_count"] == 0
    assert summarize_content_inventory(items)["ready_short_only_count"] == 143
    assert all(item.long_form_word_count < 1200 for item in items if item.opportunity_id)


def test_inventory_paths_and_summary_are_valid() -> None:
    items = build_content_inventory()
    summary = summarize_content_inventory(items)
    valid_paths = {"/", "/methodology"}
    valid_paths.update(f"/opportunities/{item.opportunity_id}" for item in list_opportunities())
    valid_paths.update(f"/strategies/{item.strategy_id}" for item in list_strategies())
    valid_paths.update(page.path for page in CURATED_RANKING_PAGES)

    assert all(item.source_url in valid_paths for item in items)
    assert all(item.generation_status == "NOT_STARTED" for item in items)
    assert summary["total_topic_candidates"] == len(items)
    assert summary["blocked_count"] == sum(item.evidence_status == BLOCKED for item in items)
    assert summary["partial_count"] > 0


def test_committed_artifact_has_the_inventory_schema_shape() -> None:
    root = Path(__file__).resolve().parents[2]
    artifact = json.loads((root / "config/distribution/content_inventory.json").read_text(encoding="utf-8"))
    schema = json.loads((root / "config/distribution/content_inventory.schema.json").read_text(encoding="utf-8"))

    assert artifact["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert artifact["inventory_version"] == "catalog-derived-v1"
    assert artifact["items"]
    assert {"content_id", "source_url", "content_family", "evidence_status", "generation_status"} <= set(artifact["items"][0])
