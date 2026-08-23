"""Manual IndexNow submission CLI."""

from __future__ import annotations

import argparse

from app.config.settings import get_settings
from app.search.canonical import canonical_page_inventory, canonical_url
from app.search.indexnow import IndexNowClient
from app.storage.database import create_database_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit canonical GamCryp URLs to IndexNow.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", action="append", help="Submit one canonical URL. May be provided multiple times.")
    group.add_argument("--all", action="store_true", help="Submit all canonical public URLs.")
    group.add_argument("--changed-file", help="Submit newline-delimited canonical URLs from a file.")
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = create_database_engine(settings)
    try:
        if args.all:
            urls = [canonical_url(settings, page.path) for page in canonical_page_inventory(engine)]
        elif args.changed_file:
            with open(args.changed_file, encoding="utf-8") as handle:
                urls = [line.strip() for line in handle if line.strip()]
        else:
            urls = args.url or []
        result = IndexNowClient(settings=settings, engine=engine).submit_urls(urls)
    finally:
        engine.dispose()

    print(f"submitted={len(result.submitted_urls)} status={result.status_code}")
    for url in result.submitted_urls:
        print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
