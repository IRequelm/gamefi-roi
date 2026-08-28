from __future__ import annotations

import json
from pathlib import Path

from app.strategies.catalog import list_opportunities, list_outbound_destinations


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "config" / "opportunities" / "work_research_handoff.schema.json"
EXAMPLE = ROOT / "config" / "opportunities" / "work_research_handoff.example.json"
QUEUE_POLICY = ROOT / "config" / "opportunities" / "modeling_queue_policy.json"


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
