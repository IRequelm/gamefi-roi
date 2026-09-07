"""Local smoke probe for the public web MVP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.v1_probe import ensure_sample_snapshots
from app.storage.database import create_database_engine
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1


def main() -> int:
    engine = create_database_engine()
    try:
        ensure_sample_snapshots(engine)
    finally:
        engine.dispose()

    client = TestClient(create_app())
    paths = (
        "/",
        "/rankings",
        "/rankings/gamefi",
        "/opportunities",
        "/opportunities/grass",
        f"/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}",
        "/methodology",
        "/robots.txt",
        "/sitemap.xml",
        "/assets/app.js",
        "/assets/styles.css",
        "/api/v1/rankings",
    )
    for path in paths:
        response = client.get(path)
        print(f"[OK] {path} status={response.status_code}")
        if response.status_code != 200:
            print(response.text)
            return 1

    legacy = client.get("/games/farmers-world", follow_redirects=False)
    if legacy.status_code != 301 or legacy.headers.get("location") != "/opportunities/farmers-world":
        print(f"[FAIL] /games/farmers-world status={legacy.status_code} location={legacy.headers.get('location')}")
        return 1

    rankings = client.get("/api/v1/rankings").json()
    opportunities = client.get("/api/v1/opportunities").json()
    print(f"web probe pages=10 assets=2 opportunities={opportunities['page']['total']} strategies={rankings['page']['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
