from __future__ import annotations

import json
from pathlib import Path

from app.strategies.catalog import list_opportunities, list_outbound_destinations


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "config" / "opportunities" / "work_research_handoff.schema.json"
EXAMPLE = ROOT / "config" / "opportunities" / "work_research_handoff.example.json"
QUEUE_POLICY = ROOT / "config" / "opportunities" / "modeling_queue_policy.json"
EXPANSION_BATCH_1 = ROOT / "config" / "opportunities" / "expansion_batch_1_recommendation.json"


def test_work_handoff_files_are_parseable_and_do_not_request_roi_calculation() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    assert schema["properties"]["opportunities"]["items"]["$ref"] == "#/$defs/opportunity_candidate"
    assert example["handoff_version"] == "work-research-handoff-v1"
    assert example["opportunities"][0]["financial_model_feasibility"] == "PARTIAL"

    text = json.dumps(schema).lower()
    assert "calculated_roi" not in text
    assert "projected_roi" not in text
    assert "roi_amount" not in text


def test_modeling_queue_policy_excludes_commercial_inputs() -> None:
    policy = json.loads(QUEUE_POLICY.read_text(encoding="utf-8"))
    factor_names = {factor["name"] for factor in policy["modeling_priority_factors"]}

    assert sum(factor["weight"] for factor in policy["modeling_priority_factors"]) == 100
    assert factor_names == {
        "entry_cost_reproducibility",
        "earning_rate_reproducibility",
        "realizable_value_route",
        "cost_observability",
        "timing_caps_and_change_detection",
        "machine_readability_and_terms_feasibility",
    }

    disallowed = set(policy["disallowed_priority_inputs"])
    assert {"referral_status", "affiliate_program", "sponsor_status", "revenue"} <= disallowed
    assert not any("referral" in name or "affiliate" in name or "sponsor" in name for name in factor_names)


def test_current_catalog_is_ready_for_reviewed_expansion_without_fake_referrals() -> None:
    opportunities = list_opportunities()
    destinations = {destination.destination_slug: destination for destination in list_outbound_destinations()}

    assert len(opportunities) == 26
    assert sum(len(opportunity.strategy_ids) for opportunity in opportunities) == 10

    for opportunity in opportunities:
        assert opportunity.status in {"active", "candidate"}
        assert opportunity.opportunity_type in {"GAME", "DEPIN_NODE", "POINTS"}
        assert opportunity.reward_asset_or_points_type
        assert opportunity.official_source_references
        assert opportunity.outbound_destination_slugs

        destination = destinations[opportunity.outbound_destination_slugs[0]]
        assert destination.official_url.startswith("https://")
        assert destination.status == "active"
        assert destination.verification_status == "verified"
        assert destination.referral_url is None
        assert destination.referral_status == "NONE"
        assert destination.commercial_relationship == "none"
        assert destination.is_affiliate is False


def test_expansion_batch_one_recommendation_is_quality_gated() -> None:
    recommendation = json.loads(EXPANSION_BATCH_1.read_text(encoding="utf-8"))
    opportunities = {opportunity.opportunity_id for opportunity in list_opportunities()}
    batch = recommendation["batch_1"]
    modeling_queue = recommendation["top_modeling_queue"]

    assert recommendation["validation"]["strict_schema_valid"] is False
    assert recommendation["validation"]["content_reviewed_against_schema"] is True
    assert recommendation["validation"]["referral_not_used_for_admission"] is True
    assert recommendation["validation"]["commercial_inputs_used_for_modeling_priority"] == []

    assert 10 <= len(batch) <= 15
    assert len({candidate["opportunity_id"] for candidate in batch}) == len(batch)
    assert {candidate["opportunity_id"] for candidate in batch}.isdisjoint(opportunities)

    for candidate in batch:
        assert candidate["reviewed_opportunity"] is True
        assert candidate["opportunity_type"] in {"GAME", "DEPIN_NODE", "POINTS"}
        assert candidate["roi_modeling_status"] in {"GO", "RESEARCH REQUIRED", "NOT REPRODUCIBLE"}
        assert candidate["referral"] in {"AVAILABLE", "APPLICATION REQUIRED", "NONE FOUND", "UNKNOWN"}
        assert candidate["required_human_action"]
        assert candidate["reason_for_inclusion"]
        assert candidate["evidence_urls"]
        assert all(url.startswith("https://") for url in candidate["evidence_urls"])

    assert len(modeling_queue) == 10
    assert [item["rank"] for item in modeling_queue] == list(range(1, 11))
    assert all(item["referral_status_not_used_for_priority"] is True for item in modeling_queue)
    assert all(item["policy_band"] == "MODEL_NEXT" for item in modeling_queue)
