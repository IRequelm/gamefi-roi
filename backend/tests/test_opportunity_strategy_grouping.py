from __future__ import annotations

from app.strategies.catalog import get_opportunity, list_opportunities, list_strategies
from test_api_v1 import _seeded_client


def test_catalog_has_one_parent_entry_and_retains_all_child_strategies() -> None:
    opportunities = list_opportunities()
    assert len({item.opportunity_id for item in opportunities}) == len(opportunities)
    for opportunity in opportunities:
        child_ids = {strategy.strategy_id for strategy in list_strategies() if strategy.opportunity_id == opportunity.opportunity_id}
        assert set(opportunity.strategy_ids) == child_ids


def test_opportunity_detail_groups_strategies_under_parent_label(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "strategy-grouping.db")
    payload = client.get("/api/v1/opportunities/defi-kingdoms").json()
    html = client.get("/opportunities/defi-kingdoms").text

    assert payload["strategy_count"] == len(payload["strategies"])
    assert "Strategies in this opportunity" in html
    assert "Opportunity" in html
    assert "/strategies/dfk-crystalvale-jeweler-cjewel-max-lock" in html
