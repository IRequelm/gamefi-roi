from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.api.v1.service as api_service
from app.api.app import create_app
from app.api.v1.service import RANKING_ORDERING
from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.recalculation import ScheduledRecalculator
from app.risk.scoring import SnapshotScorer
from app.storage.history import CalculationWindow, HistoryRepository
from app.storage.models import StrategySnapshotRecord, StrategySnapshotScoreRecord
from app.storage.scoring import ScoringRepository
from app.strategies import catalog
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
    assert response.headers["x-content-type-options"] == "nosniff"


def test_ops_status_exposes_database_scheduler_and_strategy_health(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "ops.db")

    response = client.get("/api/v1/ops/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == {"status": "ok"}
    assert payload["failed_calculation_count"] == 0
    assert payload["stale_strategy_count"] == 0
    assert payload["scheduler"]["cadence_minutes"] == 30
    assert payload["scheduler"]["last_successful_run_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert {item["strategy_id"] for item in payload["strategies"]} == {
        strategy.strategy_id for strategy in catalog.list_strategies()
    }
    assert {item["freshness_status"] for item in payload["strategies"]} == {"fresh"}


def test_production_security_headers_are_enabled(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "production")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/gamefi")
    monkeypatch.setenv("GAMEFI_COINGECKO_API_KEY", "secret-test-key")
    monkeypatch.setenv("GAMEFI_DFK_CHAIN_RPC_URL", "https://dedicated-rpc.example/dfk")
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "https://gamefi-roi-web.onrender.com")

    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["x-frame-options"] == "DENY"


def test_openapi_documents_api_v1_routes(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "openapi.db")

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/strategies/{strategy_id}/latest" in paths
    assert "/api/v1/rankings" in paths
    assert "/api/v1/opportunities" in paths
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
    assert payload["opportunity_id"] == "defi-kingdoms"
    assert payload["opportunity_type"] == "GAME"
    assert payload["primary_destination"]["redirect_url"] == "/go/defi-kingdoms-play"
    assert latest["strategy_version"] == "v1"
    assert latest["opportunity_id"] == "defi-kingdoms"
    assert latest["opportunity_type"] == "GAME"
    assert latest["capital"]["total_capital"] == {"amount": "250.00", "currency": "USD"}
    assert Decimal(latest["earnings"]["net_earnings_day"]["amount"]) == Decimal("0.4885")
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


def test_logo_metadata_is_optional_and_parent_scoped(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "logo.db")

    grass = client.get("/api/v1/opportunities/grass").json()
    dfk = client.get("/api/v1/opportunities/defi-kingdoms").json()

    assert grass["logo"] == {
        "asset": "/assets/logos/grass.png",
        "alt": "Grass logo",
        "source_reference": {
            "label": "Grass official media kit",
            "url": "https://www.grass.io/media-kit/",
            "source_role": "OFFICIAL_PROJECT",
        },
    }
    assert dfk["logo"] is None


def test_catalog_logo_assets_are_local_and_present() -> None:
    asset_root = Path(__file__).parents[2] / "frontend" / "assets"

    for opportunity in catalog.list_opportunities():
        if opportunity.logo_asset is None:
            continue
        assert opportunity.logo_asset.startswith("/assets/logos/")
        asset_path = asset_root / opportunity.logo_asset.removeprefix("/assets/")
        assert asset_path.is_file(), opportunity.opportunity_id
        assert asset_path.stat().st_size > 0


def test_rankings_order_and_tie_breaking_policy(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "ranking.db")

    response = client.get("/api/v1/rankings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ordering"] == RANKING_ORDERING
    assert [item["rank"] for item in payload["items"]] == list(range(1, len(catalog.list_strategies()) + 1))
    assert [item["strategy"]["strategy_id"] for item in payload["items"]] == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
        "geodnet-empty-hex-triple-band-base-station",
        "splinterlands-modern-ranked-active-sps-ev",
        "dfk-crystalvale-jeweler-cjewel-5000-max-lock",
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
        "dfk-crystalvale-jeweler-cjewel-100-max-lock",
        "splinterlands-modern-ranked-grinder-sps-ev",
        "weatherxm-d1-wifi-station",
        "mysterium-b2b-existing-device",
        "splinterlands-modern-ranked-casual-sps-ev",
        "storj-existing-hardware-storage-node",
        "dimo-software-only-compatible-car",
    ]


def test_rankings_filters_use_only_modeled_fields(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "filters.db")

    assert _ranking_ids(client, "/api/v1/rankings?risk_max=50") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?confidence_min=80") == [
        "dfk-crystalvale-jeweler-cjewel-5000-max-lock",
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        "dfk-crystalvale-jeweler-cjewel-100-max-lock",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?game_id=farmers-world") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?opportunity_id=farmers-world") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?opportunity_type=GAME") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
        "splinterlands-modern-ranked-active-sps-ev",
        "dfk-crystalvale-jeweler-cjewel-5000-max-lock",
        DFK_CJEWEL_MAX_LOCK_V1.strategy_id,
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
        "dfk-crystalvale-jeweler-cjewel-100-max-lock",
        "splinterlands-modern-ranked-grinder-sps-ev",
        "splinterlands-modern-ranked-casual-sps-ev",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?opportunity_type=DEPIN_NODE") == [
        "geodnet-empty-hex-triple-band-base-station",
        "weatherxm-d1-wifi-station",
        "mysterium-b2b-existing-device",
        "storj-existing-hardware-storage-node",
        "dimo-software-only-compatible-car",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?chain=wax") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?economy_type=resource-production") == [
        FARMERS_WORLD_AXE_WOOD_V1.strategy_id,
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
    ]
    assert _ranking_ids(client, "/api/v1/rankings?capital_min=2&capital_max=20") == [
        "farmers-world-axe-wood-production-10x",
        "farmers-world-axe-wood-production-3x",
        "splinterlands-modern-ranked-active-sps-ev",
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
        "splinterlands-modern-ranked-grinder-sps-ev",
        "mysterium-b2b-existing-device",
        "splinterlands-modern-ranked-casual-sps-ev",
        "dimo-software-only-compatible-car",
    ]


def test_list_pagination_is_deterministic(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "pagination.db")

    response = client.get("/api/v1/strategies?limit=1&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == {"limit": 1, "offset": 1, "total": len(catalog.list_strategies())}
    assert len(payload["items"]) == 1
    assert payload["items"][0]["strategy_id"] == catalog.list_strategies()[1].strategy_id


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


def test_old_otherwise_valid_snapshot_ages_into_stale_without_mutating_source_summary(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "aged-stale-api.db")
    monkeypatch.setattr(api_service, "_utc_now", lambda: NOW + timedelta(minutes=6))

    response = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/latest")
    rankings = client.get("/api/v1/rankings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["freshness"]["overall_status"] == "stale"
    assert payload["freshness"]["status_counts"]["stale"] == 0
    assert any(
        item["strategy"]["strategy_id"] == DFK_CJEWEL_MAX_LOCK_V1.strategy_id for item in rankings.json()["items"]
    )

    with Session(engine) as session:
        record = session.scalar(
            select(StrategySnapshotRecord)
            .where(StrategySnapshotRecord.strategy_id == DFK_CJEWEL_MAX_LOCK_V1.strategy_id)
            .order_by(StrategySnapshotRecord.calculated_at.desc())
        )
        assert record is not None
        assert record.freshness_summary_json["status_counts"]["stale"] == 0


def test_ops_status_counts_aged_snapshots_as_stale(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "aged-stale-ops.db")
    monkeypatch.setattr(api_service, "_utc_now", lambda: NOW + timedelta(minutes=6))

    response = client.get("/api/v1/ops/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stale_strategy_count"] == len(catalog.list_strategies())
    assert {item["freshness_status"] for item in payload["strategies"]} == {"stale"}


def test_invalid_ids_return_404(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "invalid.db")

    assert client.get("/api/v1/games/not-a-game").status_code == 404
    assert client.get("/api/v1/opportunities/not-an-opportunity").status_code == 404
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
    assert {item["opportunity_type"] for item in list_response.json()["items"]} == {"GAME"}
    assert detail_response.status_code == 200
    assert detail_response.json()["strategy_count"] == 4
    assert {strategy["strategy_id"] for strategy in detail_response.json()["strategies"]} >= {
        SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id
    }
    assert detail_response.json()["primary_destination"]["redirect_url"] == "/go/splinterlands-play"


def test_opportunities_catalog_includes_non_game_candidates_without_financial_snapshots(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "opportunities.db")

    list_response = client.get("/api/v1/opportunities")
    grass_response = client.get("/api/v1/opportunities/grass")
    teneo_response = client.get("/api/v1/opportunities/teneo")
    aro_response = client.get("/api/v1/opportunities/aro-network")

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["page"]["total"] >= 25
    assert {item["opportunity_type"] for item in payload["items"]} == {"GAME", "DEPIN_NODE", "POINTS"}
    assert {item["opportunity_id"] for item in payload["items"]} >= {
        "grass",
        "teneo",
        "aro-network",
        "pixels",
        "datagram",
    }
    assert grass_response.status_code == 200
    grass = grass_response.json()
    assert grass["opportunity_type"] == "DEPIN_NODE"
    assert grass["data_feasibility_status"] == "PARTIAL"
    assert grass["value_realization_status"] == "non_transferable_points"
    assert grass["strategies"] == []
    assert teneo_response.json()["data_feasibility_status"] == "PARTIAL"
    assert aro_response.json()["value_realization_status"] == "future_airdrop_claim"


def test_referral_metadata_cannot_change_rankings_or_scores(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "commercial-boundary.db")
    before = client.get("/api/v1/rankings").json()
    before_ids = [item["strategy"]["strategy_id"] for item in before["items"]]
    before_scores = {
        item["strategy"]["strategy_id"]: (
            item["latest_snapshot"]["confidence"]["score"],
            item["latest_snapshot"]["risk"]["score"],
            item["latest_snapshot"]["roi"]["roi_total_30d"]["value"],
        )
        for item in before["items"]
    }

    mutated_destinations = tuple(
        replace(
            destination,
            referral_url="https://farmersworld.io/?ref=gamefi-roi-test",
            referral_code="gamefi-roi-test",
            affiliate_program="test-affiliate",
            is_affiliate=True,
            commercial_relationship="affiliate",
            disclosure_text="Test affiliate metadata; must not affect organic analytics.",
        )
        if destination.destination_slug == "farmers-world-play"
        else destination
        for destination in catalog.OUTBOUND_DESTINATIONS
    )
    monkeypatch.setattr(catalog, "OUTBOUND_DESTINATIONS", mutated_destinations)

    after = client.get("/api/v1/rankings").json()

    assert [item["strategy"]["strategy_id"] for item in after["items"]] == before_ids
    assert {
        item["strategy"]["strategy_id"]: (
            item["latest_snapshot"]["confidence"]["score"],
            item["latest_snapshot"]["risk"]["score"],
            item["latest_snapshot"]["roi"]["roi_total_30d"]["value"],
        )
        for item in after["items"]
    } == before_scores
    assert after["items"][0]["latest_snapshot"].get("affiliate_program") is None


def _seeded_client(monkeypatch, tmp_path, database_name: str) -> tuple[TestClient, object]:
    engine = _migrated_engine(monkeypatch, tmp_path, database_name)
    _seed_snapshots_and_scores(engine)
    monkeypatch.setattr(api_service, "_utc_now", lambda: NOW + timedelta(minutes=1))
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
