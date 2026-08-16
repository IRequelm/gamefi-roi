from __future__ import annotations

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from test_api_v1 import _seeded_client


def test_web_mvp_pages_are_served_by_fastapi(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-pages.db")

    for path in (
        "/",
        "/rankings",
        "/games/farmers-world",
        f"/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}",
        "/methodology",
    ):
        response = client.get(path)

        assert response.status_code == 200
        assert "GameFi ROI" in response.text
        assert "/assets/app.js" in response.text


def test_web_assets_are_served_and_point_to_api_v1(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-assets.db")

    app_js = client.get("/assets/app.js")
    styles = client.get("/assets/styles.css")

    assert app_js.status_code == 200
    assert styles.status_code == 200
    assert 'const API_BASE = "/api/v1";' in app_js.text
    assert "/api/v2" not in app_js.text
    assert "calculate_strategy_roi" not in app_js.text
    assert "gross_nominal_daily_reward_value" not in app_js.text


def test_unknown_static_route_uses_web_not_found_state(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-not-found.db")

    response = client.get("/does-not-exist")

    assert response.status_code == 404
