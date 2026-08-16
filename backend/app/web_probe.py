"""Local smoke probe for the G11 web MVP."""

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
        "/games/farmers-world",
        f"/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}",
        "/methodology",
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

    rankings = client.get("/api/v1/rankings").json()
    print(f"web probe pages=5 assets=2 strategies={rankings['page']['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
