"""Import source-backed X or YouTube content performance metrics.

This command records operator-supplied platform dashboard data only. It does
not call either platform, infer missing values, or change ROI/revenue records.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("X", "YOUTUBE"), required=True)
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--period-start", required=True, help="ISO-8601 timestamp")
    parser.add_argument("--period-end", required=True, help="ISO-8601 timestamp")
    parser.add_argument("--impressions", type=int)
    parser.add_argument("--views", type=int)
    parser.add_argument("--engagements", type=int)
    parser.add_argument("--link-clicks", type=int)
    parser.add_argument("--profile-visits", type=int)
    parser.add_argument("--followers-gained", type=int)
    parser.add_argument("--subscribers-gained", type=int)
    parser.add_argument("--average-retention-percent", type=Decimal)
    parser.add_argument("--evidence-url")
    parser.add_argument("--evidence-reference", help="Dashboard export, screenshot, or operator record reference")
    parser.add_argument("--notes")
    args = parser.parse_args()

    from app.storage.database import create_database_engine
    from app.storage.monetization import MonetizationRepository

    record = MonetizationRepository(create_database_engine()).save_content_performance(
        platform=args.platform,
        content_id=args.content_id,
        period_start=_datetime(args.period_start),
        period_end=_datetime(args.period_end),
        impressions=args.impressions,
        views=args.views,
        engagements=args.engagements,
        link_clicks=args.link_clicks,
        profile_visits=args.profile_visits,
        followers_gained=args.followers_gained,
        subscribers_gained=args.subscribers_gained,
        average_retention_percent=args.average_retention_percent,
        evidence_url=args.evidence_url,
        evidence_reference=args.evidence_reference,
        notes=args.notes,
    )
    print(json.dumps(asdict(record), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
