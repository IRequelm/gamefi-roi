from __future__ import annotations

import argparse
from pathlib import Path

from app.content_enrichment.long_form import write_long_form_enrichment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write evidence-bound long-form enrichment plans.")
    parser.add_argument("--output", type=Path, default=Path("config/distribution/long_form_enrichment.json"))
    parser.add_argument("--limit", type=int, default=35)
    args = parser.parse_args(argv)
    payload = write_long_form_enrichment(args.output, limit=args.limit)
    print({"output": str(args.output), **payload["summary"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
