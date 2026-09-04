from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from app.monetization.models import (
    ReferralCoverageState,
    ReferralLifecycleStatus,
    ReferralTaskStatus,
    ReferralTaskType,
    RevenueAttributionStatus,
)
from app.monetization.referral_operations import ReferralOperationsService, ReferralValidationError
from app.config.settings import clear_settings_cache
from app.storage.monetization import MonetizationRepository
from test_api_v1 import NOW, _seeded_client


def test_published_opportunity_without_referral_remains_published_with_official_fallback(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "referral-published.db")

    opportunity = client.get("/api/v1/opportunities/defi-kingdoms").json()
    redirect = client.get("/go/defi-kingdoms-play", follow_redirects=False)
    row = _row(engine, "defi-kingdoms")

    assert opportunity["name"] == "DeFi Kingdoms"
    assert opportunity["primary_destination"]["redirect_url"] == "/go/defi-kingdoms-play"
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://defikingdoms.com/"
    assert row.coverage_state is ReferralCoverageState.REFERRAL_MISSING


def test_missing_referral_generates_task_without_duplicates(monkeypatch, tmp_path) -> None:
    _client, engine = _seeded_client(monkeypatch, tmp_path, "referral-missing-task.db")
    service = _service(engine)

    first = service.run_health_check(at=NOW)
    second = service.run_health_check(at=NOW + timedelta(minutes=1))

    tasks = MonetizationRepository(engine).referral_tasks(status=ReferralTaskStatus.OPEN)
    assert any(task.opportunity_id == "defi-kingdoms" and task.task_type is ReferralTaskType.FIND_REFERRAL_PROGRAM for task in tasks)
    assert len(tasks) == len({(task.opportunity_id, task.task_type) for task in tasks})
    assert len(second.tasks) == len(first.tasks)


def test_adding_active_referral_resolves_missing_task_and_upgrades_go_redirect(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "referral-active.db")
    service = _service(engine)
    service.run_health_check(at=NOW)

    program = service.save_program(
        destination_slug="defi-kingdoms-play",
        referral_status=ReferralLifecycleStatus.ACTIVE,
        referral_url="https://defikingdoms.com/?ref=gamcryp",
        referral_code="gamcryp",
        affiliate_program="DFK Partner",
        evidence_url="https://defikingdoms.com/partners",
        last_checked_at=NOW,
        verified_at=NOW,
    )
    redirect = client.get("/go/defi-kingdoms-play", follow_redirects=False)
    tasks = MonetizationRepository(engine).referral_tasks(status=ReferralTaskStatus.OPEN, opportunity_id="defi-kingdoms")

    assert program.referral_status is ReferralLifecycleStatus.ACTIVE
    assert _row(engine, "defi-kingdoms").coverage_state is ReferralCoverageState.REFERRAL_ACTIVE
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://defikingdoms.com/?ref=gamcryp"
    assert all(task.task_type is not ReferralTaskType.FIND_REFERRAL_PROGRAM for task in tasks)


def test_expired_and_old_verification_create_operator_tasks(monkeypatch, tmp_path) -> None:
    _client, engine = _seeded_client(monkeypatch, tmp_path, "referral-health.db")
    service = _service(engine)
    service.save_program(
        destination_slug="farmers-world-play",
        referral_status=ReferralLifecycleStatus.ACTIVE,
        referral_url="https://farmersworld.io/?ref=gamcryp",
        affiliate_program="Farmers Partner",
        evidence_url="https://farmersworld.io/",
        verified_at=NOW - timedelta(days=40),
        last_checked_at=NOW - timedelta(days=40),
    )
    service.save_program(
        destination_slug="splinterlands-play",
        referral_status=ReferralLifecycleStatus.ACTIVE,
        referral_url="https://splinterlands.com/?ref=gamcryp",
        affiliate_program="Splinterlands Partner",
        evidence_url="https://splinterlands.com/",
        verified_at=NOW,
        last_checked_at=NOW,
        expires_at=NOW - timedelta(days=1),
    )

    result = service.run_health_check(at=NOW)
    tasks = {(task.opportunity_id, task.task_type) for task in result.tasks}

    assert _row(engine, "farmers-world", at=NOW).coverage_state is ReferralCoverageState.REFERRAL_REVERIFY
    assert _row(engine, "splinterlands", at=NOW).coverage_state is ReferralCoverageState.REFERRAL_EXPIRED
    assert ("farmers-world", ReferralTaskType.REVERIFY_PROGRAM) in tasks
    assert ("splinterlands", ReferralTaskType.REPLACE_EXPIRED_LINK) in tasks


def test_pending_and_application_required_tasks(monkeypatch, tmp_path) -> None:
    _client, engine = _seeded_client(monkeypatch, tmp_path, "referral-pending.db")
    service = _service(engine)
    service.save_program(
        destination_slug="defi-kingdoms-play",
        referral_status=ReferralLifecycleStatus.APPLICATION_REQUIRED,
        last_checked_at=NOW,
    )
    service.save_program(
        destination_slug="farmers-world-play",
        referral_status=ReferralLifecycleStatus.PENDING,
        applied_at=NOW - timedelta(days=20),
        last_checked_at=NOW - timedelta(days=20),
    )

    result = service.run_health_check(at=NOW)
    tasks = {(task.opportunity_id, task.task_type) for task in result.tasks}

    assert _row(engine, "defi-kingdoms", at=NOW).coverage_state is ReferralCoverageState.REFERRAL_RESEARCH_REQUIRED
    assert _row(engine, "farmers-world", at=NOW).coverage_state is ReferralCoverageState.REFERRAL_PENDING
    assert ("defi-kingdoms", ReferralTaskType.APPLY_TO_PROGRAM) in tasks
    assert ("farmers-world", ReferralTaskType.RECHECK_PENDING_APPLICATION) in tasks


def test_verified_program_generates_link_verification_task(monkeypatch, tmp_path) -> None:
    _client, engine = _seeded_client(monkeypatch, tmp_path, "referral-verified.db")
    service = _service(engine)
    service.save_program(
        destination_slug="splinterlands-play",
        referral_status=ReferralLifecycleStatus.VERIFIED,
        referral_url="https://splinterlands.com/?ref=gamcryp",
        affiliate_program="Splinterlands Partner",
        evidence_url="https://splinterlands.com/",
        verified_at=NOW,
        last_checked_at=NOW,
    )

    result = service.run_health_check(at=NOW)
    tasks = {(task.opportunity_id, task.task_type) for task in result.tasks}

    assert _row(engine, "splinterlands", at=NOW).coverage_state is ReferralCoverageState.REFERRAL_REVERIFY
    assert ("splinterlands", ReferralTaskType.VERIFY_REFERRAL_LINK) in tasks


def test_no_program_found_is_explicit_coverage_state(monkeypatch, tmp_path) -> None:
    _client, engine = _seeded_client(monkeypatch, tmp_path, "referral-no-program.db")
    service = _service(engine)

    service.save_program(
        destination_slug="grass-official",
        referral_status=ReferralLifecycleStatus.NO_PROGRAM_FOUND,
        evidence_url="https://www.grass.io/terms-and-conditions/",
        last_checked_at=NOW,
        operator_notes="No affiliate program found during review.",
    )

    assert _row(engine, "grass", at=NOW).coverage_state is ReferralCoverageState.NO_PROGRAM_FOUND


def test_invalid_referral_url_cannot_become_active_and_go_falls_back(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "referral-invalid.db")
    service = _service(engine)

    with pytest.raises(ReferralValidationError):
        service.save_program(
            destination_slug="defi-kingdoms-play",
            referral_status=ReferralLifecycleStatus.ACTIVE,
            referral_url="javascript:alert(1)",
            affiliate_program="Unsafe Partner",
            evidence_url="https://defikingdoms.com/",
        )

    redirect = client.get("/go/defi-kingdoms-play", follow_redirects=False)
    assert redirect.headers["location"] == "https://defikingdoms.com/"


def test_referral_edits_do_not_alter_organic_analytics(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "referral-integrity.db")
    before = _ranking_signature(client)

    _service(engine).save_program(
        destination_slug="splinterlands-play",
        referral_status=ReferralLifecycleStatus.ACTIVE,
        referral_url="https://splinterlands.com/?ref=gamcryp",
        referral_code="gamcryp",
        affiliate_program="Splinterlands Partner",
        evidence_url="https://splinterlands.com/",
        verified_at=NOW,
        last_checked_at=NOW,
    )

    assert _ranking_signature(client) == before


def test_manual_revenue_defaults_unverified_and_epc_uses_verified_revenue_only(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "referral-revenue.db")
    repository = MonetizationRepository(engine)
    destination = client.get("/go/defi-kingdoms-play", follow_redirects=False)
    assert destination.status_code == 302
    service = _service(engine)

    service.save_revenue_attribution(
        destination_slug="defi-kingdoms-play",
        click_period_start=NOW,
        click_period_end=NOW + timedelta(days=1),
        verified_conversion_count=9,
        revenue_amount=Decimal("90.00"),
        revenue_currency="USD",
        settlement_reference_id=None,
        evidence_reference=None,
    )
    service.save_revenue_attribution(
        destination_slug="defi-kingdoms-play",
        click_period_start=NOW,
        click_period_end=NOW + timedelta(days=1),
        verified_conversion_count=1,
        revenue_amount=Decimal("10.00"),
        revenue_currency="USD",
        settlement_reference_id="settled-1",
        evidence_reference="partner-report",
        attribution_status=RevenueAttributionStatus.VERIFIED,
    )
    metrics = repository.metrics(destination_slug="defi-kingdoms-play")

    assert repository.revenue_attributions()[0].attribution_status is RevenueAttributionStatus.PENDING
    assert metrics.verified_conversions.value == "1"
    assert metrics.verified_revenue.value == "10.00 USD"
    assert metrics.earnings_per_click.value == "10.00 USD"


def test_operator_routes_require_auth_and_are_noindex(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-auth-disabled.db")
    assert client.get("/operator/referrals").status_code == 503

    monkeypatch.setenv("GAMEFI_OPERATOR_USERNAME", "ops")
    monkeypatch.setenv("GAMEFI_OPERATOR_PASSWORD", "secret")
    clear_settings_cache()
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-auth.db")

    unauthenticated = client.get("/operator/referrals")
    authenticated = client.get("/operator/referrals", auth=("ops", "secret"))

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated.headers["x-robots-tag"] == "noindex, nofollow"
    assert '<meta name="robots" content="noindex,nofollow">' in authenticated.text
    assert "Referral Work Queue" in authenticated.text


def test_operator_editor_updates_referral_and_shows_validation_errors(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_OPERATOR_USERNAME", "ops")
    monkeypatch.setenv("GAMEFI_OPERATOR_PASSWORD", "secret")
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-editor.db")

    bad = client.post(
        "/operator/referrals/defi-kingdoms",
        auth=("ops", "secret"),
        data={"referral_status": "ACTIVE", "referral_url": "https://evil.example/ref", "evidence_url": "https://evil.example/proof"},
    )
    good = client.post(
        "/operator/referrals/defi-kingdoms",
        auth=("ops", "secret"),
        data={
            "referral_status": "ACTIVE",
            "referral_url": "https://defikingdoms.com/?ref=gamcryp",
            "affiliate_program": "DFK Partner",
            "evidence_url": "https://defikingdoms.com/",
            "verified_at": NOW.isoformat(),
            "last_checked_at": NOW.isoformat(),
        },
        follow_redirects=False,
    )

    assert bad.status_code == 400
    assert "host must match" in bad.text
    assert good.status_code == 303


def test_operator_write_rejects_cross_origin_form_posts(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_OPERATOR_USERNAME", "ops")
    monkeypatch.setenv("GAMEFI_OPERATOR_PASSWORD", "secret")
    clear_settings_cache()
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-csrf.db")
    response = client.post(
        "/operator/referrals/health",
        auth=("ops", "secret"),
        headers={"Origin": "https://untrusted.example"},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_operator_editor_reports_invalid_dates_as_bad_request(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_OPERATOR_USERNAME", "ops")
    monkeypatch.setenv("GAMEFI_OPERATOR_PASSWORD", "secret")
    clear_settings_cache()
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-invalid-date.db")
    response = client.post(
        "/operator/referrals/defi-kingdoms",
        auth=("ops", "secret"),
        data={"applied_at": "not-a-date"},
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_operator_urls_are_excluded_from_search_surfaces(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-search.db")

    robots = client.get("/robots.txt").text
    sitemap = client.get("/sitemap.xml").text

    assert "Disallow: /operator/" in robots
    assert "/operator" not in sitemap


def test_public_go_remains_fail_closed_for_unknown_destination(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "referral-go-closed.db")

    response = client.get("/go/not-reviewed", follow_redirects=False)

    assert response.status_code == 404


def _service(engine) -> ReferralOperationsService:
    return ReferralOperationsService(MonetizationRepository(engine), reverify_days=30, pending_recheck_days=14)


def _row(engine, opportunity_id: str, *, at=NOW):
    return next(row for row in _service(engine).coverage_rows(at=at) if row.opportunity.opportunity_id == opportunity_id)


def _ranking_signature(client) -> list[tuple]:
    return [
        (
            item["strategy"]["strategy_id"],
            item["latest_snapshot"]["roi"]["roi_total_30d"]["value"],
            item["latest_snapshot"]["confidence"]["score"],
            item["latest_snapshot"]["risk"]["score"],
        )
        for item in client.get("/api/v1/rankings").json()["items"]
    ]
