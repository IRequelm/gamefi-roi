"""Build the X-only content batch and queue without touching YouTube artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from app.distribution.content_pack import write_batch
from app.distribution.learning_batch import LEARNING_BATCH_ID, build_learning_batch
from app.distribution.x_queue import build_x_publish_queue, editorial_order_from_handoff, write_x_queue


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the X-only GamCryp content batch and queue.")
    parser.add_argument("--rankings-url", default="https://gamcryp.com/api/v1/rankings?limit=100")
    parser.add_argument("--opportunities-url", default="https://gamcryp.com/api/v1/opportunities?limit=100")
    parser.add_argument("--base-url", default="https://gamcryp.com")
    parser.add_argument("--output", default="distribution/content_packs/x_learning_batch_001.json")
    parser.add_argument("--queue-output", default="distribution/publish_queue/x_publish_queue_autonomous.json")
    parser.add_argument("--handoff", default="distribution/publish_queue/next_publish_queue.json")
    args = parser.parse_args()

    rankings = _fetch_json(args.rankings_url)
    opportunities = _fetch_json(args.opportunities_url)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    packs = build_learning_batch(
        rankings,
        opportunities,
        base_url=args.base_url,
        created_at=generated_at,
        include_x_guides=True,
    )
    output = Path(args.output)
    write_batch(
        output,
        packs,
        batch_id=f"{LEARNING_BATCH_ID}-x",
        generated_at=generated_at,
        source_dataset=f"{args.rankings_url} + {args.opportunities_url}",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    source_bytes = output.read_bytes()
    queue = build_x_publish_queue(
        batch_payload=payload,
        packs=tuple(packs),
        source_batch_bytes=source_bytes,
        editorial_order=editorial_order_from_handoff(Path(args.handoff)),
    )
    write_x_queue(Path(args.queue_output), queue)
    print(json.dumps({
        "content_pack_file": str(output),
        "queue_file": args.queue_output,
        "pack_count": len(packs),
        "publishable": [item.content_id for item in queue.publishable],
        "awaiting_human_approval": [item.content_id for item in queue.awaiting_human_approval],
        "blocked": [item.content_id for item in queue.blocked],
    }, indent=2))


def _fetch_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
