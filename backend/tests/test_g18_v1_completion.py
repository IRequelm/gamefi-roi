from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from app.adapters.contract import ADAPTER_CONTRACT_VERSION, AdapterResultV1, ValueClassification
from app.api.app import create_app
from app.config.settings import Settings
from app.engine.calculator import MODEL_VERSION, calculate_strategy_roi
from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.production_recalculation import build_production_tasks
from app.monetization.models import ReferralCoverageState, ReferralTaskStatus, ReferralTaskType
from app.monetization.referral_operations import ReferralOperationsService, published_opportunities
from app.search.canonical import canonical_page_inventory
from app.storage.monetization import MonetizationRepository
from app.strategies.catalog import (
    CATALOG_REVIEWED_AT,
    list_games,
    list_opportunities,
    list_outbound_destinations,
    list_strategies,
)
from test_api_v1 import NOW, _seed_snapshots_and_scores
from test_history_storage import _migrated_engine

FIXTURE = Path(__file__).parent / "fixtures" / "v1_strategy_expansion_golden.json"
CALCULATED_AT = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def test_v1_catalog_targets_identity_and_outbound_coverage_are_complete() -> None:
    opportunities = list_opportunities()
    strategies = list_strategies()
    games = list_games()
    destinations = list_outbound_destinations()

    assert len(opportunities) >= 25
    assert len(strategies) >= 10
    assert [game.game_id for game in games] == ["defi-kingdoms", "farmers-world", "splinterlands"]
    assert {opportunity.opportunity_type for opportunity in opportunities} >= {"GAME", "DEPIN_NODE", "POINTS"}
    assert len({opportunity.opportunity_id for opportunity in opportunities}) == len(opportunities)
    assert len({strategy.strategy_id for strategy in strategies}) == len(strategies)
    assert len({destination.destination_slug for destination in destinations}) == len(destinations)

    destination_by_slug = {destination.destination_slug: destination for destination in destinations}
    strategy_ids = {strategy.strategy_id for strategy in strategies}
    for opportunity in opportunities:
        assert opportunity.status in {"active", "candidate", "watchlist"}
        assert opportunity.data_feasibility_status in {"GO", "PARTIAL", "PARKED", "REJECTED"}
        assert opportunity.reward_asset_or_points_type
        assert opportunity.official_source_references
        assert set(opportunity.strategy_ids) <= strategy_ids
        assert opportunity.outbound_destination_slugs
        for slug in opportunity.outbound_destination_slugs:
            destination = destination_by_slug[slug]
            assert destination.opportunity_id == opportunity.opportunity_id
            assert destination.status == "active"
            assert destination.verification_status == "verified"
            assert destination.official_url.startswith("https://")
            assert destination.referral_status == "NONE"
            assert destination.commercial_relationship == "none"
            assert destination.is_affiliate is False
            assert destination.reviewed_at == CATALOG_REVIEWED_AT


def test_v1_all_modeled_strategies_match_manual_golden_fixture() -> None:
    expected = json.loads(FIXTURE.read_text())["manual_expected"]
    tasks = {task.strategy_id: task for task in build_history_probe_tasks()}

    assert set(expected) == {strategy.strategy_id for strategy in list_strategies()} == set(tasks)

    for strategy_id, expected_fields in expected.items():
        task = tasks[strategy_id]
        observations = task.load_observations(CALCULATED_AT)
        adapter_result = task.adapter.build_engine_input(observations, calculated_at=CALCULATED_AT)
        roi_result = calculate_strategy_roi(adapter_result.economics_input)

        assert isinstance(adapter_result, AdapterResultV1)
        assert adapter_result.contract_version == ADAPTER_CONTRACT_VERSION
        assert adapter_result.economics_input.model_version == MODEL_VERSION
        assert adapter_result.economics_input.input_observation_ids
        for metric in adapter_result.derived_values:
            assert adapter_result.classifications[metric] is ValueClassification.DERIVED

        actual = _roi_fields(roi_result)
        assert {field: actual[field] for field in expected_fields} == {
            field: Decimal(value) if value is not None else None for field, value in expected_fields.items()
        }


def test_v1_production_task_registry_covers_modeled_strategy_catalog() -> None:
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        allow_sqlite_for_tests=True,
    )
    tasks = build_production_tasks(settings)

    assert {task.strategy_id for task in tasks} == {strategy.strategy_id for strategy in list_strategies()}
    assert len(tasks) == len(list_strategies())


def test_v1_api_history_and_search_surfaces_cover_all_modeled_strategies(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "g18-surfaces.db")
    _seed_snapshots_and_scores(engine, calculated_at=NOW)
    client = TestClient(create_app())

    rankings = client.get("/api/v1/rankings").json()
    assert rankings["page"]["total"] == len(list_strategies())
    assert {item["strategy"]["strategy_id"] for item in rankings["items"]} == {
        strategy.strategy_id for strategy in list_strategies()
    }

    for strategy in list_strategies():
        latest = client.get(f"/api/v1/strategies/{strategy.strategy_id}/latest")
        history = client.get(f"/api/v1/strategies/{strategy.strategy_id}/history")
        assert latest.status_code == 200
        assert history.status_code == 200
        assert history.json()["page"]["total"] == 1
        assert latest.json()["confidence"]["available"] is True
        assert latest.json()["risk"]["available"] is True

    sitemap = client.get("/sitemap.xml").text
    inventory_paths = {page.path for page in canonical_page_inventory(engine)}
    assert {f"/opportunities/{opportunity.opportunity_id}" for opportunity in list_opportunities()} <= inventory_paths
    assert {f"/strategies/{strategy.strategy_id}" for strategy in list_strategies()} <= inventory_paths
    assert all("/api/" not in path and "/go/" not in path and "/operator/" not in path for path in inventory_paths)
    assert "2026-08-24" in sitemap


def test_v1_referral_queue_has_explicit_coverage_for_every_published_opportunity(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "g18-referrals.db")
    repository = MonetizationRepository(engine)
    service = ReferralOperationsService(repository)

    first = service.run_health_check(at=CALCULATED_AT)
    second = service.run_health_check(at=CALCULATED_AT)
    tasks = repository.referral_tasks(status=ReferralTaskStatus.OPEN)

    assert {row.opportunity.opportunity_id for row in first.rows} == {
        opportunity.opportunity_id for opportunity in published_opportunities()
    }
    assert {row.coverage_state for row in first.rows} == {ReferralCoverageState.REFERRAL_MISSING}
    assert {task.opportunity_id for task in tasks} == {row.opportunity.opportunity_id for row in first.rows}
    assert {task.task_type for task in tasks} == {ReferralTaskType.FIND_REFERRAL_PROGRAM}
    assert len(tasks) == len(first.rows)
    assert len(second.tasks) == len(first.tasks)


def test_v1_go_redirect_official_fallback_works_for_every_destination(monkeypatch, tmp_path) -> None:
    _migrated_engine(monkeypatch, tmp_path, "g18-go.db")
    client = TestClient(create_app())

    for destination in list_outbound_destinations():
        response = client.get(f"/go/{destination.destination_slug}", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == destination.official_url
        assert response.headers["x-robots-tag"] == "noindex, nofollow"

    assert client.get("/go/not-reviewed", follow_redirects=False).status_code == 404


def test_v1_unavailable_roi_opportunities_render_without_zero_roi(monkeypatch, tmp_path) -> None:
    _migrated_engine(monkeypatch, tmp_path, "g18-unavailable.db")
    client = TestClient(create_app())

    response = client.get("/opportunities/grass")

    assert response.status_code == 200
    assert "ROI not measurable yet" in response.text
    assert "Points cannot currently be converted to cash reliably" in response.text
    assert "$0" not in response.text
    assert "0%" not in response.text


def _roi_fields(result) -> dict[str, Decimal | None]:
    return {
        "total_capital": result.total_capital.amount,
        "sunk_cost": result.sunk_cost.amount,
        "recoverable_capital": result.recoverable_capital.amount,
        "capital_at_risk": result.capital_at_risk.amount,
        "gross_nominal_earnings_day": result.gross_nominal_earnings_day.amount,
        "realizable_earnings_day": result.realizable_earnings_day.amount,
        "operating_cost_day": result.operating_cost_day.amount,
        "transaction_cost_day": result.transaction_cost_day.amount,
        "net_earnings_day": result.net_earnings_day.amount,
        "break_even_days": result.break_even.days,
        "roi_total_7d": result.roi_total_7d.value,
        "roi_total_30d": result.roi_total_30d.value,
        "roi_total_90d": result.roi_total_90d.value,
        "roi_risk_7d": result.roi_risk_7d.value,
        "roi_risk_30d": result.roi_risk_30d.value,
        "roi_risk_90d": result.roi_risk_90d.value,
        "exit_adjusted_pnl": result.exit_adjusted_pnl.amount,
    }
