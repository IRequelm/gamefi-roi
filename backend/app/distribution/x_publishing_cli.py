"""Operator CLI for the GamCryp X publishing and approval workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.distribution.x_publisher import (
    XPublisherConfig,
    XPublisherError,
    XPublishingService,
    safe_error,
)
from app.distribution.x_queue import (
    build_x_publish_queue,
    editorial_order_from_handoff,
    load_content_pack_batch,
    write_x_queue,
)

DEFAULT_HANDOFF_FILE = Path("distribution/publish_queue/next_publish_queue.json")
DEFAULT_APPROVAL_REPORT = Path("distribution/publish_queue/x_yellow_approval_report.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operate the fail-closed GamCryp X publishing layer.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    queue = subcommands.add_parser("queue", help="Regenerate the canonical X queue from validated content packs.")
    queue.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF_FILE)

    preview = subcommands.add_parser("preview", help="Preview final copy and all current publish blockers.")
    preview.add_argument("content_id")

    report = subcommands.add_parser("approval-report", help="Write the compact YELLOW human-review report.")
    report.add_argument("--output", type=Path, default=DEFAULT_APPROVAL_REPORT)

    approve = subcommands.add_parser("approve", help="Approve the exact safe copy for one YELLOW item.")
    approve.add_argument("content_id")
    approve.add_argument("--copy-file", type=Path, help="Optional reviewed final-copy text file.")

    revoke = subcommands.add_parser("revoke", help="Revoke an active YELLOW approval.")
    revoke.add_argument("content_id")

    publish = subcommands.add_parser("publish", help="Dry-run or explicitly publish one queue item.")
    publish.add_argument("content_id")
    publish.add_argument("--dry-run", action="store_true")
    publish.add_argument("--confirm-publish", action="store_true")

    publish_next = subcommands.add_parser("publish-next", help="Dry-run or publish the next eligible item.")
    publish_next.add_argument("--dry-run", action="store_true")
    publish_next.add_argument("--confirm-publish", action="store_true")

    subcommands.add_parser("status", help="Show safe OAuth and local publisher state.")
    subcommands.add_parser("authorize-url", help="Create the OAuth 2.0 PKCE authorization URL.")
    authorize = subcommands.add_parser("authorize", help="Exchange an approved OAuth callback URL for tokens.")
    authorize.add_argument("--callback-url", required=True)

    args = parser.parse_args(argv)
    config = XPublisherConfig.from_environment()

    try:
        if args.command == "queue":
            _write_queue(config, handoff=args.handoff)
            _print_json(XPublishingService(config).queue_summary())
            return 0

        service = XPublishingService(config)
        if args.command == "preview":
            _print_json(service.preview(args.content_id).model_dump(mode="json"))
            return 0
        if args.command == "approval-report":
            report_payload = _write_approval_report(service, config, args.output)
            _print_json({"status": "written", "output": str(args.output), "items": len(report_payload["items"])})
            return 0
        if args.command == "approve":
            edited_copy = args.copy_file.read_text(encoding="utf-8") if args.copy_file else None
            record = service.approve(args.content_id, edited_copy=edited_copy)
            _print_json(
                {
                    "content_id": record.content_id,
                    "approved_at": record.approved_at,
                    "approved_content_checksum": record.approved_content_checksum,
                    "state": record.state,
                }
            )
            return 0
        if args.command == "revoke":
            record = service.revoke(args.content_id)
            _print_json({"content_id": record.content_id, "state": record.state, "revoked_at": record.revoked_at})
            return 0
        if args.command == "publish":
            _require_publish_mode(args.dry_run, args.confirm_publish)
            result = service.publish(
                args.content_id,
                dry_run=args.dry_run,
                confirm_publish=args.confirm_publish,
            )
            _print_json(result.model_dump(mode="json"))
            return 0
        if args.command == "publish-next":
            _require_publish_mode(args.dry_run, args.confirm_publish)
            result = service.publish_next(dry_run=args.dry_run, confirm_publish=args.confirm_publish)
            _print_json(result.model_dump(mode="json"))
            return 0
        if args.command == "status":
            _print_json(
                {
                    "oauth": service.oauth.safe_status(),
                    "queue": service.queue_summary(),
                    "automatic_scheduling_enabled": False,
                    "actual_publish_requires_confirmation": True,
                    "detail": "No scheduler is active; actual publishing requires --confirm-publish.",
                }
            )
            return 0
        if args.command == "authorize-url":
            _print_json({"authorization_url": service.oauth.authorization_url(), "external_action_required": True})
            return 0
        if args.command == "authorize":
            _print_json(service.oauth.complete_authorization(args.callback_url))
            return 0
    except (XPublisherError, OSError, ValueError, json.JSONDecodeError) as exc:
        _print_json({"status": "error", "error": safe_error(exc)})
        return 1
    return 1


def _write_queue(config: XPublisherConfig, *, handoff: Path) -> None:
    source_bytes = config.content_pack_file.read_bytes()
    batch_payload, packs = load_content_pack_batch(config.content_pack_file)
    queue = build_x_publish_queue(
        batch_payload=batch_payload,
        packs=packs,
        source_batch_bytes=source_bytes,
        editorial_order=editorial_order_from_handoff(handoff),
    )
    write_x_queue(config.queue_file, queue)


def _write_approval_report(
    service: XPublishingService,
    config: XPublisherConfig,
    output: Path,
) -> dict[str, Any]:
    queue, packs = service._load_context()  # Operator report uses the same validated context as publishing.
    pack_by_id = {pack.content_id: pack for pack in packs}
    items: list[dict[str, Any]] = []
    for item in queue.awaiting_human_approval:
        preview = service.preview(item.content_id)
        non_approval_blockers = [
            blocker for blocker in preview.blockers if "requires explicit checksum-bound human approval" not in blocker
        ]
        recommendation = "APPROVE"
        if any("stale" in blocker for blocker in non_approval_blockers):
            recommendation = "REJECT"
        elif non_approval_blockers:
            recommendation = "EDIT"
        pack = pack_by_id[item.content_id]
        items.append(
            {
                "attribution_url": item.attribution_url,
                "content_id": item.content_id,
                "exact_copy": preview.exact_final_copy,
                "numeric_claims": [claim.model_dump(mode="json") for claim in pack.claims],
                "project": item.project,
                "reason_yellow": item.risk_caveat,
                "recommendation": recommendation,
                "review_blockers": non_approval_blockers,
                "risk_caveat": item.risk_caveat,
                "snapshot_timestamp": item.snapshot_timestamp,
                "weighted_character_count": preview.weighted_character_count,
            }
        )
    payload = {
        "report_version": "x-yellow-approval-report-v1",
        "source_batch_id": queue.source_batch_id,
        "generated_at": queue.generated_at,
        "items": items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _require_publish_mode(dry_run: bool, confirm_publish: bool) -> None:
    if dry_run == confirm_publish:
        raise XPublisherError("Choose exactly one: --dry-run or --confirm-publish")


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
