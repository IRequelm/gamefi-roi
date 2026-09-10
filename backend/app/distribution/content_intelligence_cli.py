"""Operator-only dry-run commands for discovery and content intelligence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from app.discovery.content_intelligence import brief_json, build_editorial_brief
from app.discovery.engine import DiscoveryRecord, EvidenceRecord, Signal, evaluate_admission, score_discovery
from app.discovery.providers import GoogleTrendsProvider, UnavailableProvider
from app.content_inventory.inventory import READY, build_content_inventory
from app.strategies.catalog import get_opportunity


def demo_record() -> DiscoveryRecord:
    now = datetime.now(UTC)
    record = DiscoveryRecord(
        canonical_name="ExampleGrid",
        aliases=["ExampleGrid", "Example Grid Network"],
        category="DEPIN_NODE",
        official_url="https://example.com/",
        discovery_source="fixture",
        discovery_query="bandwidth sharing",
        evidence_strength="MEDIUM",
        signals=[
            Signal("search_momentum", 72, "fixture", now, "FIXTURE", "Demo breakout search signal."),
            Signal("youtube_outlier", 61, "fixture", now, "FIXTURE", "Demo channel-relative outlier signal."),
            Signal("audience_fit", 80, "policy", now, "DERIVED", "DePIN opportunity matches GamCryp scope."),
            Signal("visual_potential", 55, "policy", now, "DERIVED", "A node dashboard could support a visual explainer."),
            Signal("novelty", 90, "policy", now, "DERIVED", "No matching static catalog entry in this demo."),
        ],
        evidence=[
            EvidenceRecord("https://examplegrid.invalid/", "OFFICIAL_PROJECT", "identity", True, now),
            EvidenceRecord("https://examplegrid.invalid/docs", "OFFICIAL_PROJECT", "participation", True, now),
            EvidenceRecord("https://examplegrid.invalid/rewards", "OFFICIAL_PROJECT", "reward_mechanism", True, now),
        ],
        why_discovered="Fixture only; not a live claim.",
    )
    return score_discovery(record)


def main() -> None:
    parser = argparse.ArgumentParser(description="GamCryp discovery and content-intelligence dry-run commands.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    daily = subcommands.add_parser("daily-plan", help="Show a no-publish daily intelligence plan.")
    daily.add_argument("--json", action="store_true")
    daily.add_argument("--dry-run-e2e", action="store_true", help="Run the complete fixture discovery-to-brief path.")
    status = subcommands.add_parser("status", help="Show provider and intelligence status.")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args()
    trends = GoogleTrendsProvider().probe()
    providers = [trends, UnavailableProvider("youtube_data_api", "No authorized live API credentials configured." ).probe(), UnavailableProvider("x_api", "No authorized live API credentials configured.").probe()]
    record = demo_record() if args.command == "daily-plan" and args.dry_run_e2e else None
    decision = evaluate_admission(record) if record else None
    current_candidates = []
    for item in build_content_inventory():
        if item.evidence_status != READY or not item.opportunity_id or item.content_family == "FINANCIAL_ROI":
            continue
        opportunity = get_opportunity(item.opportunity_id)
        if opportunity is None:
            continue
        current_candidates.append({
            "candidate_id": item.content_id,
            "opportunity_id": item.opportunity_id,
            "platform": "YOUTUBE_SHORT" if item.short_form_eligible else "X_ONLY",
            "score": 50 if item.short_form_eligible else 42,
            "confidence": "MEDIUM",
            "why_now": ["catalog evidence is available", "existing content inventory candidate"],
            "angle": item.content_family.replace("_", " ").title(),
            "preferred_window": "20:00–22:00 Europe/Istanbul",
        })
    current_candidates = sorted(current_candidates, key=lambda item: (-item["score"], item["candidate_id"]))[:5]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "publish_performed": False,
        "providers": [p.__dict__ for p in providers],
        "content_to_produce_today": ([brief_json(build_editorial_brief(record))] if record else current_candidates),
        "new_discoveries": [{"name": record.canonical_name, "score": record.discovery_score, "status": decision.outcome, "source": "fixture"}] if record and decision else [],
        "catalog_gaps": [{"project": record.canonical_name, "coverage": "NONE", "priority": record.research_priority}] if record else [],
        "auto_added_opportunities": ([{"name": record.canonical_name, "admission_mode": decision.outcome.removeprefix("AUTO_ADD_")}] if record and decision and decision.outcome.startswith("AUTO_ADD") else []),
        "research_queue": [record.canonical_name] if record else [],
        "quarantined_rejected": [],
        "source_failures": [p.limitation for p in providers if p.status == "BLOCKED"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
        return
    print("CONTENT TO PRODUCE TODAY")
    for item in payload["content_to_produce_today"]:
        print(f"- {item['platform']}: {item['hook']} | score={item['content_score']}")
    print("NEW DISCOVERIES")
    for item in payload["new_discoveries"]:
        print(f"- {item['name']} | score={item['score']} | {item['status']}")
    print("CATALOG GAPS")
    for item in payload["catalog_gaps"]:
        print(f"- {item['project']} | coverage={item['coverage']} | priority={item['priority']}")
    print("SOURCE FAILURES")
    for failure in payload["source_failures"]:
        print(f"- {failure}")
    print("PUBLISH PERFORMED: NO")


if __name__ == "__main__":
    main()
