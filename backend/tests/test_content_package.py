from __future__ import annotations

from dataclasses import replace

from app.content_inventory.inventory import BLOCKED, PARTIAL, READY, build_content_inventory
from app.content_package.generator import build_content_packages, validate_package


def test_short_only_inventory_item_cannot_become_long_form_package() -> None:
    inventory = build_content_inventory()
    short_only = next(item for item in inventory if item.content_id == "inventory-depin_setup-fluxnode")
    packages = build_content_packages()

    assert short_only.evidence_status == READY
    assert short_only.short_form_eligible is True
    assert short_only.long_form_eligible is False
    assert not any(package.source_inventory_item_id == short_only.content_id and package.format == "LONG_FORM" for package in packages)


def test_rich_opportunity_can_produce_long_form_package() -> None:
    base = next(package for package in build_content_packages() if package.format == "SHORT_FORM" and package.content_family != "FINANCIAL_ROI")
    sections = tuple({"title": f"Section {index}", "text": (f"Evidence-backed detail {index} " * 220).strip(), "evidence_paths": ["opportunity.guidance.how_to_start"]} for index in range(6))
    package = replace(base, format="LONG_FORM", narration_sections=sections, narration_script_outline=tuple(section["title"] for section in sections), estimated_narration_words=1320, estimated_duration_seconds=528)

    assert validate_package(package) is True


def test_guide_only_how_to_package_is_allowed_but_financial_package_is_not() -> None:
    packages = build_content_packages()

    assert any(
        package.source_inventory_item_id == "inventory-how_to_start-hivemapper" and package.generation_status == "READY_FOR_REVIEW"
        for package in packages
    )
    assert not any("financial_roi" in package.source_inventory_item_id for package in packages)
    assert any(item.content_family == "FINANCIAL_ROI" and item.evidence_status == BLOCKED for item in build_content_inventory())


def test_comparison_topics_use_one_parent_record_per_multi_strategy_opportunity() -> None:
    inventory = build_content_inventory()
    comparisons = [item for item in inventory if item.content_family == "STRATEGY_COMPARISON"]

    assert len(comparisons) == 3
    assert all(item.strategy_id is None and len(item.strategy_ids) >= 2 for item in comparisons)
    assert len({item.content_id for item in comparisons}) == len(comparisons)


def test_partial_and_blocked_inventory_items_do_not_generate_publishable_packages() -> None:
    inventory = build_content_inventory()
    packages = build_content_packages()
    eligible_ids = {item.content_id for item in inventory if item.evidence_status == READY}

    assert all(package.source_inventory_item_id in eligible_ids for package in packages)
    assert not any(package.generation_status == "NOT_READY" for package in packages)
    assert any(item.evidence_status == PARTIAL for item in inventory)
    assert any(item.evidence_status == BLOCKED for item in inventory)


def test_evidence_binding_rejects_unsupported_claims() -> None:
    package = next(package for package in build_content_packages() if package.format == "SHORT_FORM")
    unsafe = replace(package, factual_talking_points=(
        {"text": "This opportunity guarantees returns.", "evidence_paths": ["invented.claim"]},
    ))

    assert validate_package(package) is True
    assert validate_package(unsafe) is False


def test_truthful_negated_guarantee_warning_remains_publishable() -> None:
    package = next(
        package
        for package in build_content_packages()
        if package.source_inventory_item_id == "inventory-how_you_earn-mysterium-network-node"
    )

    assert package.generation_status == "READY_FOR_REVIEW"
    assert any("does not guarantee" in point["text"] for point in package.factual_talking_points)


def test_package_output_is_deterministic_and_ids_are_unique() -> None:
    first = build_content_packages()
    second = build_content_packages()

    assert first == second
    assert len({package.package_id for package in first}) == len(first)
