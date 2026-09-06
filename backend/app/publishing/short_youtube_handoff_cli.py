"""Prepare and report review-only short-form YouTube handoffs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config.settings import get_settings
from app.publishing.short_youtube_handoff import prepare_short_handoff, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare validated short-form renders for YouTube handoff.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--limit", type=int, default=13)
    commands.add_parser("report")
    args = parser.parse_args(argv)
    if args.command == "report":
        print(json.dumps(report(), indent=2, sort_keys=True))
    else:
        queue = prepare_short_handoff(settings=get_settings(), limit=args.limit)
        print(json.dumps({"status": "prepared", **report(), "queue_items": len(queue.items)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
