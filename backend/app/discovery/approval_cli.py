"""Operator CLI for discovery candidate approval requests and replies."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import get_settings
from app.discovery.approval import DiscoveryApprovalEmailConfig, DiscoveryApprovalInbox, DiscoveryApprovalMailer
from app.storage.database import create_database_engine
from app.storage.discovery import DiscoveryRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage fail-closed GamCryp discovery approvals.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    request = subcommands.add_parser("request", help="Send approval email for a pending discovery record.")
    request.add_argument("discovery_id")
    enrich = subcommands.add_parser("enrich", help="Promote an approved research candidate from operator-reviewed evidence JSON.")
    enrich.add_argument("discovery_id")
    enrich.add_argument("--category", required=True, help="Canonical opportunity category, for example DEPIN_NODE or GAME.")
    enrich.add_argument("--official-url", required=True, help="Verified official HTTPS project URL.")
    enrich.add_argument("--evidence-json", required=True, type=Path, help="JSON array of reviewed evidence records.")
    enrich.add_argument("--confirm-reviewed", action="store_true", help="Confirm that every supplied source and fact was reviewed by the operator.")
    subcommands.add_parser("poll", help="Poll the configured mailbox for explicit approval replies.")
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = create_database_engine(settings)
    config = DiscoveryApprovalEmailConfig.from_environment()
    repository = DiscoveryRepository(engine, approval_mailer=DiscoveryApprovalMailer(config))
    if args.command == "poll":
        try:
            print(json.dumps({"processed": DiscoveryApprovalInbox(config).poll(repository)}, indent=2))
        finally:
            engine.dispose()
        return 0

    if args.command == "enrich":
        if not args.confirm_reviewed:
            raise SystemExit("enrich requires --confirm-reviewed so unreviewed sources cannot promote a candidate")
        try:
            raw_evidence = json.loads(args.evidence_json.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"could not read evidence JSON: {exc}") from exc
        if not isinstance(raw_evidence, list):
            raise SystemExit("evidence JSON must contain an array")
        from app.discovery.engine import EvidenceRecord

        now = datetime.now(UTC)
        evidence = []
        for item in raw_evidence:
            if not isinstance(item, dict):
                raise SystemExit("each evidence record must be an object")
            observed = item.get("observed_at")
            try:
                observed_at = datetime.fromisoformat(str(observed).replace("Z", "+00:00")) if observed else now
            except ValueError as exc:
                raise SystemExit(f"invalid evidence observed_at: {observed}") from exc
            evidence.append(EvidenceRecord(
                source_url=str(item.get("source_url") or ""),
                source_role=str(item.get("source_role") or "OFFICIAL_PROJECT"),
                fact=str(item.get("fact") or ""),
                verified=item.get("verified") is True,
                observed_at=observed_at,
                notes=str(item.get("notes") or ""),
                fact_kind=str(item.get("fact_kind") or ""),
            ))
        try:
            record, outcome = repository.enrich_research_candidate(
                args.discovery_id,
                category=args.category,
                official_url=args.official_url,
                evidence=evidence,
            )
            print(json.dumps({"discovery_id": record.discovery_id, "status": outcome, "validation_status": record.validation_status, "missing_evidence": record.missing_evidence}, indent=2, sort_keys=True))
        finally:
            engine.dispose()
        return 0

    record = next((item for item in repository.records() if item.get("discovery_id") == args.discovery_id), None)
    if record is None:
        raise SystemExit(f"unknown discovery_id: {args.discovery_id}")
    from app.discovery.engine import DiscoveryRecord, EvidenceRecord, Signal

    def parse_time(value: object) -> datetime:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    candidate = DiscoveryRecord(
        canonical_name=str(record["canonical_name"]),
        aliases=list(record.get("aliases", [])),
        category=str(record["category"]),
        official_url=record.get("official_url"),
        discovery_source=str(record["discovery_source"]),
        discovery_query=record.get("discovery_query"),
        first_seen_at=parse_time(record["first_seen_at"]),
        last_seen_at=parse_time(record["last_seen_at"]),
        signals=[Signal(**item, observed_at=parse_time(item["observed_at"])) for item in record.get("signals", [])],
        evidence=[EvidenceRecord(**item, observed_at=parse_time(item["observed_at"])) for item in record.get("evidence", [])],
        evidence_strength=str(record.get("evidence_strength", "UNKNOWN")),
        missing_evidence=list(record.get("missing_evidence", [])),
        risk_flags=list(record.get("risk_flags", [])),
        validation_status=str(record.get("validation_status", "DISCOVERED")),
        matched_opportunity_id=record.get("matched_opportunity_id"),
        discovery_score=float(record.get("discovery_score", 0)),
        research_priority=str(record.get("research_priority", "LOW")),
        why_discovered=str(record.get("why_discovered", "")),
    )
    try:
        print(json.dumps({"discovery_id": args.discovery_id, "status": repository.request_approval(candidate)}, indent=2))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
