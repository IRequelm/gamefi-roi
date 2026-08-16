from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.app import create_app
from app.api.v1.service import RANKING_ORDERING
from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.recalculation import ScheduledRecalculator
from app.risk.scoring import SnapshotScorer
from app.storage.history import CalculationWindow, HistoryRepository
from app.storage.models import StrategySnapshotRecord, StrategySnapshotScoreRecord
from app.storage.scoring import ScoringRepository
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from test_history_storage import _migrated_engine

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def test_api_versioned_health(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "health.db")

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["api_version"] == "v1"


def test_openapi_documents_api_v1_routes(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "openapi.db")

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/strategies/{strategy_id}/latest" in paths
    assert "/api/v1/rankings" in paths
    assert paths["/api/v1/rankings"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RankingsPage"
    )


def test_strategy_detail_includes_latest_snapshot_risk_and_confidence(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "detail.db")

    response = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}")

    assert response.status_code == 200
    payload = response.json()
    latest = payload["latest_snapshot"]
    assert payload["game_id"] == "defi-kingdoms"
    assert latest["strategy_version"] == "v1"
    assert latest["capital"]["total_capital"] == {"amount": "250.00", "currency": "USD"}
    assert latest["earnings"]["net_earnings_day"]["amount"] == "0.4885"
    assert latest["confidence"]["score"] == 82
    assert latest["confidence"]["label"] == "HIGH"
    assert latest["risk"]["score"] == 79
    assert latest["risk"]["label"] == "VERY HIGH"
    assert latest["versions"]["adapter_contract_version"] == "adapter-contract-v1"
    assert latest["versions"]["model_version"] == "roi-core-v1"
    assert latest["versions"]["scoring_methodology_version"] == "risk-confidence-v1"
    assert latest["classification_summary"]["counts"]["LIVE"] == 2
    assert latest["classification_summary"]["counts"]["CONFIG"] == 3
    assert latest["classification_summary"]["counts"]["DERIVED"] >= 4


def test_rankings_order_and_tie_breaking_policy(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "ranking.db")

    response = client.get("/api/v1/rankings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ordering"] == RANKING_ORDERING
    assert [item["rank"] for item in payload["items"]] == [1, 2, 3]
    assert [item["strategy"]["strategy_id"] for item in payload["items"]] == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
    ]


def test_rankings_filters_use_only_modeled_fields(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "filters.db")

    assert _ranking_ids(client, "/api/v1/rankings?risk_max=50") == [FARMERS_WORLD_AXE_WOOD_V1.strategy_id]
    assert _ranking_ids(client, "/api/v1/rankings?confidence_min=80") == [DFK_CJEWEL_MAX_LOCK_V1.strategy_id]
    assert _ranking_ids(client, "/api/v1/rankings?game_id=farmers-world") == [FARMERS_WORLD_AXE_WOOD_V1.strategy_id]
    assert _ranking_ids(client, "/api/v1/rankings?chain=wax") == [FARMERS_WORLD_AXE_WOOD_V1.strategy_id]
    assert _ranking_ids(client, "/api/v1/rankings?economy_type=resource-production") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id
    ]
    assert _ranking_ids(client, "/api/v1/rankings?capital_min=2&capital_max=20") == [
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id
    ]


def test_list_pagination_is_deterministic(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "pagination.db")

    response = client.get("/api/v1/strategies?limit=1&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == {"limit": 1, "offset": 1, "total": 3}
    assert len(payload["items"]) == 1
    assert payload["items"][0]["strategy_id"] == FARMERS_WORLD_AXE_WOOD_V1.strategy_id


def test_history_is_ordered_and_paginated(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "history.db")
    _seed_snapshots_and_scores(engine, calculated_at=NOW + timedelta(hours=1))

    response = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/history?limit=1&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == {"limit": 1, "offset": 1, "total": 2}
    assert [item["calculated_at"] for item in payload["items"]] == [(NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z")]


def test_unavailable_optional_fields_and_decimal_serialization(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "optional.db")
    _delete_score(engine, DFK_CJEWEL_MAX_LOCK_V1.strategy_id)

    response = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/latest")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["capital"]["total_capital"]["amount"], str)
    assert Decimal(payload["capital"]["total_capital"]["amount"]) == Decimal("250.00")
    assert isinstance(payload["roi"]["roi_total_30d"]["value"], str)
    assert payload["uncertainty_ranges"] == []
    assert payload["confidence"]["available"] is False
    assert payload["confidence"]["score"] is None
    assert payload["risk"]["available"] is False
    assert payload["risk"]["score"] is None
    assert payload["confidence"]["unavailable_factors"][0]["factor"] == "score"


def test_uncertainty_range_payload_for_probabilistic_strategy(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "uncertainty.db")

    response = client.get(f"/api/v1/strategies/{SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id}/latest")

    assert response.status_code == 200
    ranges = response.json()["uncertainty_ranges"]
    assert ranges[0]["metric"] == "splinterlands.modern_ranked.expected_sps_day"
    assert ranges[0]["values"] == {
        "low_metric": "2.2500",
        "base_metric": "2.7500",
        "high_metric": "3.2500",
    }


def test_stale_freshness_is_exposed(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "stale-api.db")
    _mark_latest_stale(engine, DFK_CJEWEL_MAX_LOCK_V1.strategy_id)

    response = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/latest")

    assert response.status_code == 200
    assert response.json()["freshness"]["overall_status"] == "stale"


def test_invalid_ids_return_404(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "invalid.db")

    assert client.get("/api/v1/games/not-a-game").status_code == 404
    assert client.get("/api/v1/strategies/not-a-strategy").status_code == 404
    assert client.get("/api/v1/strategies/not-a-strategy/latest").status_code == 404


def test_query_validation_errors(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "validation.db")

    assert client.get("/api/v1/rankings?limit=0").status_code == 422
    assert client.get("/api/v1/rankings?confidence_min=101").status_code == 422
    assert client.get("/api/v1/rankings?capital_min=10&capital_max=1").status_code == 422
    assert client.get(
        f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/history"
        "?start_at=2026-08-16T13:00:00Z&end_at=2026-08-16T12:00:00Z"
    ).status_code == 422


def test_games_endpoints_include_strategy_catalog(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "games.db")

    list_response = client.get("/api/v1/games")
    detail_response = client.get("/api/v1/games/splinterlands")

    assert list_response.status_code == 200
    assert [item["game_id"] for item in list_response.json()["items"]] == [
        "defi-kingdoms",
        "farmers-world",
        "splinterlands",
    ]
    assert detail_response.status_code == 200
    assert detail_response.json()["strategies"][0]["strategy_id"] == SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id


def _seeded_client(monkeypatch, tmp_path, database_name: str) -> tuple[TestClient, object]:
    engine = _migrated_engine(monkeypatch, tmp_path, database_name)
    _seed_snapshots_and_scores(engine)
    return TestClient(create_app()), engine


def _seed_snapshots_and_scores(engine, *, calculated_at: datetime = NOW) -> None:
    history_repository = HistoryRepository(engine)
    run = ScheduledRecalculator(history_repository).run_once(
        build_history_probe_tasks(),
        intended_window=CalculationWindow(calculated_at, calculated_at + timedelta(minutes=5)),
        calculated_at=calculated_at,
    )
    assert not run.failures

    scoring_repository = ScoringRepository(engine)
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


def _ranking_ids(client: TestClient, path: str) -> list[str]:
    response = client.get(path)
    assert response.status_code == 200
    return [item["strategy"]["strategy_id"] for item in response.json()["items"]]


def _delete_score(engine, strategy_id: str) -> None:
    with Session(engine) as session:
        snapshot = session.scalar(
            select(StrategySnapshotRecord)
            .where(StrategySnapshotRecord.strategy_id == strategy_id)
            .order_by(StrategySnapshotRecord.calculated_at.desc())
        )
        assert snapshot is not None
        scores = session.scalars(
            select(StrategySnapshotScoreRecord).where(StrategySnapshotScoreRecord.snapshot_id == snapshot.snapshot_id)
        ).all()
        for score in scores:
            session.delete(score)
        session.commit()


def _mark_latest_stale(engine, strategy_id: str) -> None:
    with Session(engine) as session:
        record = session.scalar(
            select(StrategySnapshotRecord)
            .where(StrategySnapshotRecord.strategy_id == strategy_id)
            .order_by(StrategySnapshotRecord.calculated_at.desc())
        )
        assert record is not None
        summary = dict(record.freshness_summary_json)
        summary["status_counts"] = {"fresh": 0, "stale": 1, "invalid": 0, "missing": 0}
        record.freshness_summary_json = summary
        session.commit()
