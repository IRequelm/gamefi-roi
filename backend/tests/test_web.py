from __future__ import annotations

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from test_api_v1 import _seeded_client


def test_web_mvp_pages_are_served_by_fastapi(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-pages.db")

    for path in (
        "/",
        "/rankings",
        "/opportunities",
        "/opportunities/grass",
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


def test_outbound_redirect_resolves_reviewed_destination_without_tracking_cookie(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-redirect.db")

    response = client.get("/go/defi-kingdoms-play", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://defikingdoms.com/"
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers


def test_outbound_redirect_fails_closed_for_unknown_destination(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-redirect-404.db")

    response = client.get("/go/not-a-reviewed-destination", follow_redirects=False)

    assert response.status_code == 404


def test_unknown_static_route_uses_web_not_found_state(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-not-found.db")

    response = client.get("/does-not-exist")

    assert response.status_code == 404
