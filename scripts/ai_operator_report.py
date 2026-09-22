"""Dependency-light read-only/draft bridge for the Hybrid AI Agent.

This script intentionally uses only the Python standard library so the
Open-Terminal runtime can inspect the live distribution artifacts even when
the full application virtualenv is not mounted.  It never publishes.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "distribution" / "content_packs" / "learning_batch_001.json"
X_QUEUE = ROOT / "distribution" / "publish_queue" / "x_publish_queue.json"
Y_QUEUE = ROOT / "distribution" / "publish_queue" / "youtube_publish_queue.json"
OUT = Path("/workspace/outputs/gamcryp")


def load(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def report() -> dict:
    batch = load(CONTENT)
    packs = batch.get("packs", [])
    counts = {state: sum(1 for pack in packs if pack.get("editorial", {}).get("readiness") == state) for state in ("GREEN", "YELLOW", "RED")}
    return {
        "status": "PASS",
        "read_only": True,
        "content_pack": str(CONTENT),
        "pack_count": len(packs),
        "readiness_counts": counts,
        "x_queue_present": X_QUEUE.is_file(),
        "youtube_queue_present": Y_QUEUE.is_file(),
        "public_publish": "NOT_PERFORMED_APPROVAL_REQUIRED",
    }


def prepare(limit: int) -> dict:
    batch = load(CONTENT)
    packs = batch.get("packs", [])
    selected = [
        {
            "content_id": pack.get("content_id"),
            "title": pack.get("editorial", {}).get("hook") or pack.get("content_id"),
            "source_url": pack.get("distribution", {}).get("canonical_site_url"),
            "readiness": pack.get("editorial", {}).get("readiness"),
            "public_publish": "REQUIRES_APPROVAL",
        }
        for pack in packs
        if pack.get("editorial", {}).get("readiness") in {"GREEN", "YELLOW"}
    ][: max(1, min(limit, 20))]
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "distribution-draft.json"
    payload = {
        "status": "PASS",
        "kind": "distribution_draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_batch": str(CONTENT),
        "items": selected,
        "public_publish": "NOT_PERFORMED_APPROVAL_REQUIRED",
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**payload, "artifact": str(target), "item_count": len(selected)}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report")
    prep = sub.add_parser("prepare")
    prep.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    payload = report() if args.command == "report" else prepare(args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
