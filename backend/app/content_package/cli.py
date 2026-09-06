"""CLI for deterministic evidence-bound content package templates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.content_package.generator import build_content_packages, summarize_content_packages, write_content_packages

DEFAULT_PATH = Path("config/distribution/content_packages.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or report deterministic GamCryp content packages.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    build = subcommands.add_parser("build", help="Build packages from READY inventory items.")
    build.add_argument("--ready-only", action="store_true", default=True)
    build.add_argument("--output", type=Path, default=DEFAULT_PATH)
    report = subcommands.add_parser("report", help="Report generated package counts.")
    report.add_argument("--input", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    if args.command == "build":
        payload = write_content_packages(args.output, ready_only=args.ready_only)
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        print(f"Wrote {len(payload['packages'])} content packages to {args.output}")
        return
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
