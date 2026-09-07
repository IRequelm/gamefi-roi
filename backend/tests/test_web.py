from __future__ import annotations

from types import SimpleNamespace

from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.web.seo import _diversify_ranking_items, plain_unavailable_reason, value_status_label
from test_api_v1 import _seeded_client
from sqlalchemy.exc import OperationalError


def test_web_mvp_pages_are_served_by_fastapi(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-pages.db")

    for path in (
        "/",
        "/rankings",
        "/opportunities",
        "/opportunities/grass",
        f"/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}",
        "/methodology",
    ):
        response = client.get(path)

        assert response.status_code == 200
        assert "GamCryp" in response.text
        assert "/assets/brand/gamcryp-logo.png" in response.text
        assert "/assets/app.js" in response.text
        assert "https://x.com/GamCryp" in response.text
        assert 'mailto:info@gamcryp.com">info@gamcryp.com</a>' in response.text
        assert "https://www.youtube.com/@GamCryp" in response.text
        assert "gamcryp@gmail.com" not in response.text


def test_legacy_game_route_permanently_redirects_to_canonical_opportunity(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-legacy-game-redirect.db")

    response = client.get("/games/farmers-world", follow_redirects=False)

    assert response.status_code == 301
    assert response.headers["location"] == "/opportunities/farmers-world"
    assert response.headers["cache-control"] == "public, max-age=86400"


def test_homepage_omits_internal_audit_blocks(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-home-copy.db")

    html = client.get("/").text

    assert "TOP STORED ANSWER" not in html.upper()
    assert "UNAVAILABLE ROI POLICY" not in html.upper()
    assert "DATA SOURCE" not in html.upper()
    assert "served through /api/v1" not in html
    assert "page requests do not call live providers" not in html


def test_rankings_omits_empty_filter_label_and_spreads_duplicate_opportunities(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-ranking-presentation.db")

    html = client.get("/rankings").text
    assert "No additional filters." not in html

    def item(opportunity_id: str, rank: int):
        return SimpleNamespace(
            rank=rank,
            strategy=SimpleNamespace(opportunity_id=opportunity_id, game_id=opportunity_id),
        )

    ordered = _diversify_ranking_items(
        [item("defi-kingdoms", 1), item("defi-kingdoms", 2), item("defi-kingdoms", 3), item("geodnet", 4)]
    )
    assert [row.strategy.opportunity_id for row in ordered] == [
        "defi-kingdoms",
        "geodnet",
        "defi-kingdoms",
        "defi-kingdoms",
    ]


def test_unavailable_reason_does_not_claim_priced_rewards_have_no_price() -> None:
    for opportunity_id in ("akash-provider", "filecoin-storage-provider", "illuvium", "gods-unchained"):
        opportunity = SimpleNamespace(
            opportunity_id=opportunity_id,
            value_realization_status="realizable",
            data_feasibility_status="PARTIAL",
            feasibility_summary="Current earning rate and operating costs are not reproducible.",
            roi_unavailable=None,
        )
        reason = plain_unavailable_reason(opportunity)
        assert "market price may exist" in reason.lower()
        assert "earning rate" in reason.lower()


def test_priced_reward_without_reproducible_rate_has_user_facing_status() -> None:
    assert value_status_label("realizable", 0) == "Earning rate unverified"
    assert "market price may exist" in plain_unavailable_reason(
        SimpleNamespace(
            value_realization_status="realizable",
            data_feasibility_status="PARTIAL",
            feasibility_summary="Earning rate and operating costs are not reproducible.",
        )
    )


def test_web_assets_are_served_and_point_to_api_v1(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-assets.db")

    app_js = client.get("/assets/app.js")
    styles = client.get("/assets/styles.css")
    logo = client.get("/assets/brand/gamcryp-logo.png")

    assert app_js.status_code == 200
    assert styles.status_code == 200
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"
    assert 'const API_BASE = "/api/v1";' in app_js.text
    assert "/api/v2" not in app_js.text
    assert "calculate_strategy_roi" not in app_js.text
    assert "gross_nominal_daily_reward_value" not in app_js.text


def test_ga_config_is_inert_when_absent_and_public_when_configured(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-ga-absent.db")

    html = client.get("/").text

    assert '"gaMeasurementId":null' in html
    assert '"posthogProjectApiKey":null' in html
    assert '"posthogHost":"https://us.i.posthog.com"' in html
    assert '"sentryFrontendDsn":null' in html
    assert '"sentryTracesSampleRate":0.02' in html
    assert "googletagmanager.com/gtag/js" not in html
    assert "browser.sentry-cdn.com" not in html

    from app.config.settings import clear_settings_cache

    clear_settings_cache()
    monkeypatch.setenv("GAMEFI_GA_MEASUREMENT_ID", "G-TEST1234")
    monkeypatch.setenv("GAMEFI_POSTHOG_PROJECT_API_KEY", "phc_test_key")
    monkeypatch.setenv("GAMEFI_SENTRY_FRONTEND_DSN", "https://browser@example.ingest.sentry.io/456")
    monkeypatch.setenv("GAMEFI_SENTRY_ENVIRONMENT", "production")
    configured_client, _configured_engine = _seeded_client(monkeypatch, tmp_path, "web-ga-present.db")
    configured_html = configured_client.get("/").text

    assert '"gaMeasurementId":"G-TEST1234"' in configured_html
    assert '"posthogProjectApiKey":"phc_test_key"' in configured_html
    assert '"sentryFrontendDsn":"https://browser@example.ingest.sentry.io/456"' in configured_html
    assert '"sentryEnvironment":"production"' in configured_html
    assert "googletagmanager.com/gtag/js" not in configured_html
    assert "browser.sentry-cdn.com" not in configured_html


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


def test_public_home_degrades_without_database(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "web-degraded.db")

    def fail_home(*args, **kwargs):
        raise OperationalError("select 1", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr("app.web.routes.home_page", fail_home)
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["x-gamcryp-degraded"] == "database-unavailable"
    assert "Stored opportunity data is temporarily unavailable" in response.text
    assert "No fresh or estimated values are being invented" in response.text
