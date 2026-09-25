from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from app.config.settings import Settings
from app.monetization.models import ReferralLifecycleStatus
from app.observability import posthog
from app.observability.sentry import initialize_sentry, reset_sentry_for_tests, sanitize_sentry_event
from app.strategies import catalog
import app.web.routes as web_routes
from test_api_v1 import _seeded_client


def _test_settings(**overrides) -> Settings:
    values = {
        "environment": "test",
        "database_url": "sqlite+pysqlite:///:memory:",
        "allow_sqlite_for_tests": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_sentry_initialization_uses_safe_defaults(monkeypatch) -> None:
    import sentry_sdk

    calls: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    reset_sentry_for_tests()
    settings = _test_settings(
        sentry_dsn="https://public@example.ingest.sentry.io/123",
        sentry_environment="production",
        sentry_release="gamcryp@abc123",
    )

    assert initialize_sentry(settings)

    assert len(calls) == 1
    assert calls[0]["dsn"] == "https://public@example.ingest.sentry.io/123"
    assert calls[0]["environment"] == "production"
    assert calls[0]["release"] == "gamcryp@abc123"
    assert calls[0]["send_default_pii"] is False
    assert calls[0]["max_request_body_size"] == "never"
    assert calls[0]["include_local_variables"] is False
    assert calls[0]["traces_sample_rate"] == 0.02
    assert calls[0]["sample_rate"] == 1.0
    assert calls[0]["before_send"] is sanitize_sentry_event
    assert len(calls[0]["integrations"]) == 2
    reset_sentry_for_tests()


def test_sentry_event_sanitizer_removes_sensitive_request_data() -> None:
    event = {
        "request": {
            "url": "https://gamcryp.com/strategies/demo?token=secret#fragment",
            "data": {"password": "secret"},
            "cookies": "session=secret",
            "query_string": "token=secret",
            "headers": {"Authorization": "Bearer secret", "User-Agent": "pytest"},
        },
        "user": {"email": "user@example.com", "username": "tester", "ip_address": "127.0.0.1", "id": "public-id"},
        "extra": {"api_key": "secret", "safe_context": "ok"},
        "contexts": {"wallet": "secret", "safe": {"status": "ok"}},
    }

    sanitized = sanitize_sentry_event(event)

    assert sanitized is event
    assert sanitized["request"]["url"] == "https://gamcryp.com/strategies/demo"
    assert "data" not in sanitized["request"]
    assert "cookies" not in sanitized["request"]
    assert "query_string" not in sanitized["request"]
    assert sanitized["request"]["headers"]["Authorization"] == "[Filtered]"
    assert sanitized["request"]["headers"]["User-Agent"] == "pytest"
    assert sanitized["user"] == {"id": "public-id"}
    assert sanitized["extra"]["api_key"] == "[Filtered]"
    assert sanitized["extra"]["safe_context"] == "ok"
    assert sanitized["contexts"]["wallet"] == "[Filtered]"


def test_posthog_capture_is_disabled_without_project_key() -> None:
    settings = _test_settings(posthog_project_api_key=None)

    assert not posthog.track_product_event(
        settings,
        event_name="ranking_view",
        distinct_id="visitor-1",
        properties={"ranking_slug": "rankings"},
    )
    assert not posthog.track_product_event(
        _test_settings(posthog_project_api_key="phc_test_key"),
        event_name="unknown_event",
        distinct_id="visitor-1",
        properties={"ranking_slug": "rankings"},
    )


def test_posthog_capture_posts_allowlisted_properties_and_no_person_profile() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "ok"})

    settings = _test_settings(posthog_project_api_key="phc_test_key")

    assert posthog.track_product_event(
        settings,
        event_name="ranking_view",
        distinct_id="visitor-1",
        properties={
            "ranking_slug": "gamefi-under-50",
            "snapshot_id": "snapshot-1",
            "snapshot_timestamp": "2026-08-16T12:00:00Z",
            "utm_content": "x-test-variant-a",
            "raw_financial_payload": "do-not-send",
            "wallet_address": "do-not-send",
        },
        transport=httpx.MockTransport(handler),
    )

    assert len(requests) == 1
    assert str(requests[0].url) == "https://us.i.posthog.com/capture/"
    payload = json.loads(requests[0].content)
    assert payload["api_key"] == "phc_test_key"
    assert payload["event"] == "ranking_view"
    assert payload["distinct_id"] == "visitor-1"
    assert payload["properties"]["ranking_slug"] == "gamefi-under-50"
    assert payload["properties"]["snapshot_id"] == "snapshot-1"
    assert payload["properties"]["snapshot_timestamp"] == "2026-08-16T12:00:00Z"
    assert payload["properties"]["utm_content"] == "x-test-variant-a"
    assert payload["properties"]["$process_person_profile"] is False
    assert "raw_financial_payload" not in payload["properties"]
    assert "wallet_address" not in payload["properties"]


def test_posthog_capture_failure_is_safe() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"status": "down"})

    assert not posthog.track_product_event(
        _test_settings(posthog_project_api_key="phc_test_key"),
        event_name="ranking_view",
        distinct_id="visitor-1",
        properties={"ranking_slug": "rankings"},
        transport=httpx.MockTransport(handler),
    )


def test_outbound_redirect_tracks_official_and_referral_product_events(monkeypatch, tmp_path) -> None:
    captured: list[dict] = []

    def capture_event(settings, *, event_name: str, distinct_id: str, properties: dict) -> bool:
        captured.append({"settings": settings, "event_name": event_name, "distinct_id": distinct_id, "properties": properties})
        return True

    monkeypatch.setattr(web_routes.product_analytics, "track_product_event", capture_event)
    mutated = tuple(
        replace(
            destination,
            referral_url="https://defikingdoms.com/?ref=gamcryp",
            referral_code="gamcryp",
            affiliate_program="DFK Partner Test",
            is_affiliate=True,
            commercial_relationship="affiliate",
            referral_status=ReferralLifecycleStatus.ACTIVE.value,
            disclosure_text="Test affiliate link; analytical outputs must remain unchanged.",
        )
        if destination.destination_slug == "defi-kingdoms-play"
        else destination
        for destination in catalog.OUTBOUND_DESTINATIONS
    )
    monkeypatch.setattr(catalog, "OUTBOUND_DESTINATIONS", mutated)
    client, _engine = _seeded_client(monkeypatch, tmp_path, "observability-outbound.db")

    referral_response = client.get(
        "/go/defi-kingdoms-play?source_page=rankings&placement=strategy_card",
        headers={"x-gamcryp-session": "coarse-session-1"},
        follow_redirects=False,
    )
    official_response = client.get(
        "/go/farmers-world-play?source_page=home&placement=top_opportunity",
        follow_redirects=False,
    )

    assert referral_response.status_code == 302
    assert referral_response.headers["location"] == "https://defikingdoms.com/?ref=gamcryp"
    assert official_response.status_code == 302
    assert [item["event_name"] for item in captured] == [
        "outbound_go_click",
        "referral_outbound_click",
        "outbound_go_click",
        "official_fallback_outbound_click",
    ]
    assert captured[0]["distinct_id"] == "coarse-session-1"
    assert captured[0]["properties"]["target_url_kind"] == "referral"
    assert captured[0]["properties"]["commercial_relationship"] == "affiliate"
    assert captured[0]["properties"]["is_affiliate"] is True
    assert captured[0]["properties"]["event_origin"] == "server_redirect"
    assert captured[0]["properties"]["traffic_class"] == "human_or_unknown"
    assert captured[2]["properties"]["target_url_kind"] == "official"
    assert captured[2]["properties"]["source_page"] == "home"
    assert captured[2]["properties"]["placement"] == "top_opportunity"


def test_outbound_product_analytics_failure_does_not_break_redirect(monkeypatch, tmp_path) -> None:
    def boom(*_args, **_kwargs) -> bool:
        raise RuntimeError("posthog down")

    monkeypatch.setattr(web_routes.product_analytics, "track_product_event", boom)
    client, _engine = _seeded_client(monkeypatch, tmp_path, "observability-outbound-failsafe.db")

    response = client.get("/go/defi-kingdoms-play", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://defikingdoms.com/"
