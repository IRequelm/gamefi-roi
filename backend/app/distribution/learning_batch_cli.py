"""CLI for generating the first file-based distribution learning batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from app.distribution.content_pack import write_batch
from app.distribution.learning_batch import LEARNING_BATCH_CREATED_AT, LEARNING_BATCH_ID, build_learning_batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GamCryp Content Pack Lite learning batch.")
    parser.add_argument("--rankings-url", default="https://gamcryp.com/api/v1/rankings?limit=100")
    parser.add_argument("--opportunities-url", default="https://gamcryp.com/api/v1/opportunities?limit=100")
    parser.add_argument("--base-url", default="https://gamcryp.com")
    parser.add_argument("--output", default="distribution/content_packs/learning_batch_001.json")
    args = parser.parse_args()

    rankings_payload = _fetch_json(args.rankings_url)
    opportunities_payload = _fetch_json(args.opportunities_url)
    packs = build_learning_batch(rankings_payload, opportunities_payload, base_url=args.base_url)
    write_batch(
        Path(args.output),
        packs,
        batch_id=LEARNING_BATCH_ID,
        generated_at=LEARNING_BATCH_CREATED_AT,
        source_dataset=f"{args.rankings_url} + {args.opportunities_url}",
    )
    print(f"Wrote {len(packs)} content packs to {args.output}")


def _fetch_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
