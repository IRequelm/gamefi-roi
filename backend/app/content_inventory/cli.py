"""Operator CLI for the deterministic content inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.content_inventory.inventory import build_content_inventory, summarize_content_inventory, write_content_inventory

DEFAULT_PATH = Path("config/distribution/content_inventory.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or report the GamCryp content inventory.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    build = subcommands.add_parser("build", help="Build the deterministic inventory artifact.")
    build.add_argument("--output", type=Path, default=DEFAULT_PATH)
    report = subcommands.add_parser("report", help="Report inventory counts and top READY topics.")
    report.add_argument("--input", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    if args.command == "build":
        payload = write_content_inventory(args.output)
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        print(f"Wrote {len(payload['items'])} content topic candidates to {args.output}")
        return
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print("Top READY candidates:")
    for item in sorted((item for item in payload["items"] if item["evidence_status"] == "READY"), key=lambda item: item["content_id"])[:10]:
        print(f"- {item['content_id']} ({item['source_url']})")


if __name__ == "__main__":
    main()
