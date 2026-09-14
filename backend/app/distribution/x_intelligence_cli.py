"""Operator CLI for live X discovery and engagement intelligence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from app.distribution.x_intelligence import (
    DEFAULT_STATE_FILE,
    XIntelligenceCollector,
    XIntelligenceConfig,
    intelligence_is_live_and_fresh,
    load_intelligence_state,
)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(dotenv_path=Path(".env"), encoding="utf-8-sig")
    parser = argparse.ArgumentParser(description="Collect and inspect X-only GamCryp intelligence.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    collect = subcommands.add_parser("collect", help="Collect live X discovery and engagement signals.")
    collect.add_argument("--json", action="store_true")
    status = subcommands.add_parser("status", help="Show the last X intelligence state without calling X.")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    config = XIntelligenceConfig.from_environment()
    if args.command == "collect":
        payload = XIntelligenceCollector(config=config).collect()
    else:
        payload = load_intelligence_state(config.state_file) or {
            "status": "NOT_RUN",
            "state_file": str(config.state_file),
        }
        payload = {
            **payload,
            "live_and_fresh": intelligence_is_live_and_fresh(
                config.state_file,
                max_age_hours=config.freshness_hours,
            ),
        }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    else:
        print(f"X INTELLIGENCE: {payload.get('status')}")
        print(f"OBSERVATIONS: {payload.get('observation_count', 0)}")
        print(f"HIGH ENGAGEMENT: {payload.get('high_engagement_count', 0)}")
        if payload.get("limitation"):
            print(f"LIMITATION: {payload['limitation']}")
        print("PUBLISH PERFORMED: NO")
    return 0 if payload.get("status") in {"LIVE", "NOT_RUN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
