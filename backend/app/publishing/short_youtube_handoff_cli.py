"""Prepare and report review-only short-form YouTube handoffs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config.settings import get_settings
from app.storage.database import create_database_engine
from app.publishing.short_youtube_handoff import audit_handoff, approve_handoff_item, prepare_short_handoff, report, revoke_handoff_approval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare validated short-form renders for YouTube handoff.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--limit", type=int, default=13)
    prepare.add_argument("--force-rerender", action="store_true", help="rebuild existing local renders and reset their checksum-bound review state")
    commands.add_parser("report")
    commands.add_parser("audit")
    approve = commands.add_parser("approve")
    approve.add_argument("package_id")
    approve.add_argument("--confirm-reviewed", action="store_true", help="Confirm that the full render and representative frames were reviewed by a human")
    approve.add_argument("--reviewed-by", help="Human reviewer name or operator identifier")
    approve.add_argument("--review-note", help="Short note recording the creative review")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("package_id")
    args = parser.parse_args(argv)
    if args.command == "report":
        print(json.dumps(report(), indent=2, sort_keys=True))
    elif args.command == "audit":
        print(json.dumps(audit_handoff(), indent=2, sort_keys=True))
    elif args.command == "approve":
        settings = get_settings()
        engine = create_database_engine(settings)
        try:
            item = approve_handoff_item(
                args.package_id,
                engine=engine,
                confirm_reviewed=args.confirm_reviewed,
                reviewed_by=args.reviewed_by,
                review_note=args.review_note,
            )
        finally:
            engine.dispose()
        print(json.dumps({"status": "approved", "package_id": item.package_id, "video_checksum": item.video_checksum, "reviewed_by": item.creative_reviewed_by, "review_note": item.creative_review_note}, indent=2, sort_keys=True))
    elif args.command == "revoke":
        item = revoke_handoff_approval(args.package_id)
        print(json.dumps({"status": "revoked", "package_id": item.package_id}, indent=2, sort_keys=True))
    else:
        queue = prepare_short_handoff(settings=get_settings(), limit=args.limit, force_rerender=args.force_rerender)
        print(json.dumps({"status": "prepared", **report(), "queue_items": len(queue.items)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
