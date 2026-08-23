from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.monetization.models import (
    ReferralLifecycleStatus,
    RevenueAttributionStatus,
    SponsoredPlacementStatus,
)
from app.storage.monetization import MonetizationPersistenceError, MonetizationRepository
from app.strategies import catalog
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from test_api_v1 import NOW, _seeded_client
from test_history_storage import _migrated_engine


def test_go_redirect_persists_privacy_minimal_outbound_click_event(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "monetization-click.db")

    response = client.get(
        "/go/defi-kingdoms-play?source_page=home&placement=top_opportunity",
        headers={"user-agent": "Mobile Safari", "x-gamcryp-session": "coarse-session-1"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://defikingdoms.com/"
    assert "set-cookie" not in response.headers
    click = MonetizationRepository(engine).outbound_clicks(destination_slug="defi-kingdoms-play")[0]
    assert click.destination_slug == "defi-kingdoms-play"
    assert click.opportunity_id == "defi-kingdoms"
    assert click.strategy_id is None
    assert click.referral_status is ReferralLifecycleStatus.NONE
    assert click.target_url_kind == "official"
    assert click.source_page == "home"
    assert click.placement == "top_opportunity"
    assert click.coarse_session_id == "coarse-session-1"
    assert click.user_agent_category == "mobile"


def test_referral_redirect_uses_active_referral_and_official_fallback(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "monetization-referral.db")
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

    referral_response = client.get("/go/defi-kingdoms-play", follow_redirects=False)
    fallback_response = client.get("/go/farmers-world-play", follow_redirects=False)

    assert referral_response.status_code == 302
    assert referral_response.headers["location"] == "https://defikingdoms.com/?ref=gamcryp"
    assert fallback_response.headers["location"] == "https://farmersworld.io/"
    clicks = MonetizationRepository(engine).outbound_clicks()
    assert [click.target_url_kind for click in clicks] == ["referral", "official"]


def test_invalid_redirect_fails_closed_without_click_event(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "monetization-invalid.db")

    response = client.get("/go/not-a-reviewed-destination", follow_redirects=False)

    assert response.status_code == 404
    assert MonetizationRepository(engine).outbound_clicks() == []


def test_referral_lifecycle_statuses_are_explicit_and_validated(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "monetization-status.db")
    repository = MonetizationRepository(engine)

    for status in ReferralLifecycleStatus:
        program = repository.save_referral_program(
            destination_slug=f"status-{status.value.lower()}",
            referral_status=status,
            commercial_relationship="affiliate" if status is ReferralLifecycleStatus.ACTIVE else "none",
            disclosure_text="Lifecycle status test.",
            verification_status="verified" if status is ReferralLifecycleStatus.ACTIVE else "review",
            evidence={"status": status.value},
            last_checked_at=NOW,
        )
        assert program.referral_status is status

    with pytest.raises(MonetizationPersistenceError):
        repository.save_referral_program(
            destination_slug="bad-status",
            referral_status="MAYBE",
            disclosure_text="Invalid status test.",
        )


def test_verified_revenue_metrics_do_not_invent_unverified_conversions(monkeypatch, tmp_path) -> None:
    engine = _migrated_engine(monkeypatch, tmp_path, "monetization-metrics.db")
    repository = MonetizationRepository(engine)
    destination = catalog.get_outbound_destination("defi-kingdoms-play")
    assert destination is not None
    for index in range(2):
        repository.record_outbound_click(
            destination=destination,
            target_url_kind=destination.target_url_kind,
            coarse_session_id=f"session-{index}",
            occurred_at=NOW + timedelta(minutes=index),
        )
    repository.save_revenue_attribution(
        destination_slug="defi-kingdoms-play",
        click_period_start=NOW,
        click_period_end=NOW + timedelta(hours=1),
        attribution_status=RevenueAttributionStatus.PENDING,
        verified_conversion_count=10,
        revenue_amount=Decimal("999.00"),
        revenue_currency="USD",
        source_program="pending-partner-file",
    )
    repository.save_revenue_attribution(
        destination_slug="defi-kingdoms-play",
        click_period_start=NOW,
        click_period_end=NOW + timedelta(hours=1),
        attribution_status=RevenueAttributionStatus.VERIFIED,
        verified_conversion_count=1,
        revenue_amount=Decimal("3.00"),
        revenue_currency="USD",
        source_program="verified-manual-import",
    )

    metrics = repository.metrics(destination_slug="defi-kingdoms-play", impressions=20)
    empty_metrics = repository.metrics(destination_slug="farmers-world-play")

    assert metrics.outbound_clicks == 2
    assert metrics.coarse_sessions.value == "2"
    assert metrics.click_through_rate.value == "0.1"
    assert metrics.verified_conversions.value == "1"
    assert metrics.verified_revenue.value == "3.00 USD"
    assert metrics.earnings_per_click.value == "1.50 USD"
    assert metrics.verified_conversion_rate.value == "0.5"
    assert empty_metrics.verified_revenue.status == "unavailable"
    assert empty_metrics.verified_conversions.status == "unavailable"
    assert empty_metrics.earnings_per_click.status == "unavailable"


def test_commercial_records_are_separate_from_organic_rankings_and_scores(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "monetization-boundary.db")
    repository = MonetizationRepository(engine)
    before = client.get("/api/v1/rankings").json()
    before_organic = [
        (
            item["strategy"]["strategy_id"],
            item["latest_snapshot"]["roi"]["roi_total_30d"]["value"],
            item["latest_snapshot"]["confidence"]["score"],
            item["latest_snapshot"]["risk"]["score"],
        )
        for item in before["items"]
    ]

    repository.save_referral_program(
        destination_slug="splinterlands-play",
        opportunity_id="splinterlands",
        strategy_id="splinterlands-modern-ranked-sps-ev",
        affiliate_program="Sponsored Test",
        referral_status=ReferralLifecycleStatus.ACTIVE,
        commercial_relationship="affiliate",
        disclosure_text="Commercial test metadata.",
        verification_status="verified",
        evidence={"reviewed_by": "test"},
        verified_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    repository.save_sponsored_placement(
        opportunity_id="splinterlands",
        strategy_id="splinterlands-modern-ranked-sps-ev",
        surface="rankings",
        status=SponsoredPlacementStatus.ACTIVE,
        label="Sponsored test placement",
        disclosure_text="Sponsored placement test.",
        campaign_name="test-campaign",
        sponsor_name="test-sponsor",
        audit_trail={"created_for": "regression-test"},
    )
    repository.save_revenue_attribution(
        destination_slug="splinterlands-play",
        opportunity_id="splinterlands",
        strategy_id="splinterlands-modern-ranked-sps-ev",
        click_period_start=NOW,
        click_period_end=NOW + timedelta(hours=1),
        attribution_status=RevenueAttributionStatus.VERIFIED,
        verified_conversion_count=4,
        revenue_amount=Decimal("40.00"),
        revenue_currency="USD",
    )

    after = client.get("/api/v1/rankings").json()

    assert [
        (
            item["strategy"]["strategy_id"],
            item["latest_snapshot"]["roi"]["roi_total_30d"]["value"],
            item["latest_snapshot"]["confidence"]["score"],
            item["latest_snapshot"]["risk"]["score"],
        )
        for item in after["items"]
    ] == before_organic
    assert after["sponsored_placements"][0]["label"] == "Sponsored test placement"
    assert after["items"][0]["strategy"]["strategy_id"] != "splinterlands-modern-ranked-sps-ev"
