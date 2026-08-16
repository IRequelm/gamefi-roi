"""Local deterministic probe for the G10 read API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.recalculation import ScheduledRecalculator, hourly_window
from app.risk.scoring import SnapshotScorer
from app.storage.database import create_database_engine
from app.storage.history import HistoryRepository
from app.storage.scoring import ScoringRepository
from app.strategies.catalog import list_strategies


def main() -> int:
    engine = create_database_engine()
    try:
        ensure_sample_snapshots(engine)
    finally:
        engine.dispose()

    client = TestClient(create_app())
    paths = (
        "/api/v1/health",
        "/api/v1/games",
        "/api/v1/strategies",
        "/api/v1/rankings",
    )
    for path in paths:
        response = client.get(path)
        print(f"[OK] {path} status={response.status_code}")
        if response.status_code != 200:
            print(response.text)
            return 1

    rankings = client.get("/api/v1/rankings").json()
    print(
        "api probe "
        f"strategies={rankings['page']['total']} "
        f"ordering={','.join(rankings['ordering'])}"
    )
    for item in rankings["items"]:
        snapshot = item["latest_snapshot"]
        print(
            f"[RANK] {item['rank']} {snapshot['strategy_id']} "
            f"roi_30d={snapshot['roi']['roi_total_30d']['value']} "
            f"confidence={snapshot['confidence']['score']} {snapshot['confidence']['label']} "
            f"risk={snapshot['risk']['score']} {snapshot['risk']['label']} "
            f"freshness={snapshot['freshness']['overall_status']}"
        )
    return 0


def ensure_sample_snapshots(engine) -> None:
    history_repository = HistoryRepository(engine)
    if _has_all_sample_snapshots(history_repository):
        return

    scoring_repository = ScoringRepository(engine)
    calculated_at = datetime.now(UTC)
    run = ScheduledRecalculator(history_repository).run_once(
        build_history_probe_tasks(),
        intended_window=hourly_window(calculated_at),
        calculated_at=calculated_at,
    )
    if run.failures:
        if _has_all_sample_snapshots(history_repository):
            return
        for failure in run.failures:
            print(f"[FAILURE] {failure.strategy_id}@{failure.strategy_version} {failure.error_type}: {failure.error_message}")
        raise RuntimeError("API probe sample snapshot creation failed")

    scorer = SnapshotScorer()
    for snapshot in run.snapshots:
        history = history_repository.ordered_time_series(
            snapshot.strategy_id,
            start=snapshot.calculated_at - timedelta(days=30),
            end=snapshot.calculated_at,
            strategy_version=snapshot.strategy_version,
            model_version=snapshot.model_version,
        )
        scoring_repository.save_score(scorer.score(snapshot, history=history, scored_at=calculated_at))


def _has_all_sample_snapshots(history_repository: HistoryRepository) -> bool:
    expected = {strategy.strategy_id for strategy in list_strategies()}
    actual = {snapshot.strategy_id for snapshot in history_repository.latest_snapshots()}
    return expected.issubset(actual)


if __name__ == "__main__":
    raise SystemExit(main())
