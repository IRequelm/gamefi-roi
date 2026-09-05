from __future__ import annotations

import json
from pathlib import Path

from app.strategies.catalog import list_opportunities
from test_api_v1 import _seeded_client


ROOT = Path(__file__).resolve().parents[2]


def test_catalog_policy_declares_source_hierarchy_and_admission_modes() -> None:
    policy = json.loads((ROOT / "config/opportunities/catalog_admission_policy.json").read_text())
    assert policy["source_hierarchy"] == [
        "OFFICIAL_PROJECT",
        "OFFICIAL_CHAIN",
        "EXECUTABLE_MARKET",
        "AGGREGATOR",
        "OTHER_PUBLIC_EVIDENCE",
    ]
    assert set(policy["admission_modes"]) == {"MODELED", "GUIDE_ONLY"}
    assert "referral" in policy["commercial_independence"].lower()


def test_research_handoff_schema_requires_mode_and_per_input_evidence() -> None:
    schema = json.loads((ROOT / "config/opportunities/work_research_handoff.schema.json").read_text())
    opportunity = schema["$defs"]["opportunity"]
    assert opportunity["properties"]["admission_mode"]["enum"] == ["MODELED", "GUIDE_ONLY"]
    assert set(opportunity["properties"]["modeling_evidence"]["properties"]) == {
        "entry_cost",
        "earning_rate",
        "realizable_reward_value",
        "executable_exit_path",
        "relevant_costs",
        "timing_or_claim_constraints",
    }


def test_existing_catalog_derives_mode_without_rejecting_unmodeled_entries() -> None:
    opportunities = list_opportunities()
    assert any(item.admission_mode == "MODELED" and item.strategy_ids for item in opportunities)
    assert any(item.admission_mode == "GUIDE_ONLY" and not item.strategy_ids for item in opportunities)
    assert {item.admission_mode for item in opportunities} == {"MODELED", "GUIDE_ONLY"}


def test_api_exposes_mode_and_source_role_without_commercial_inputs(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "admission-policy.db")
    modeled = client.get("/api/v1/opportunities/defi-kingdoms").json()
    guide_only = client.get("/api/v1/opportunities/grass").json()

    assert modeled["admission_mode"] == "MODELED"
    assert guide_only["admission_mode"] == "GUIDE_ONLY"
    assert modeled["official_source_references"][0]["source_role"] == "OFFICIAL_PROJECT"
    assert "affiliate" not in modeled["admission_mode"].lower()
