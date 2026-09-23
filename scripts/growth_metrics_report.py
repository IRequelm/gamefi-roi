"""Read-only growth and commercial measurement report.

The report joins first-party acquisition/outbound records with the current X
and YouTube queues. It never publishes, sends mail, generates audio, or
mutates the database. Missing data is reported as unavailable rather than
converted into a zero or an inferred revenue figure.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


ROOT = Path(__file__).resolve().parents[1]
WORKER_HEARTBEAT_MAX_AGE_MINUTES = 45
sys.path.insert(0, str(ROOT / "backend"))


def _load_local_environment() -> None:
    """Load the same local configuration source as the scheduled workers."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - the application environment provides python-dotenv
        return
    load_dotenv(ROOT / ".env", override=False)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_payload(value: Any) -> dict[str, Any]:
    return {"value": value.value, "status": value.status, "reason": value.reason}


def _confirmed_x_publications() -> list[dict[str, Any]]:
    payload = _load_json(ROOT / "data/local/x/publications.json")
    records = payload.get("publications", [])
    return [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("status") == "published"
        and bool(record.get("content_id"))
    ]


def _confirmed_youtube_uploads() -> list[dict[str, Any]]:
    payload = _load_json(ROOT / "data/local/youtube/publish_state.json")
    records = payload.get("records", {})
    return [
        record
        for record in records.values()
        if isinstance(record, dict)
        and record.get("status") == "uploaded"
        and bool(record.get("video_id"))
    ]


def _queue_summary() -> dict[str, Any]:
    x_autonomous = _load_json(ROOT / "distribution/publish_queue/x_publish_queue_autonomous.json")
    x_manual = _load_json(ROOT / "distribution/manual_outbox/x_manual_ready.json")
    youtube = _load_json(ROOT / "distribution/publish_queue/youtube_short_handoff.json")
    confirmed_x = _confirmed_x_publications()
    confirmed_youtube = _confirmed_youtube_uploads()

    x_manual_items = x_manual.get("items") or ([] if not x_manual.get("item") else [x_manual["item"]])
    youtube_items = youtube.get("items", [])
    qualified_approved = [item for item in youtube_items if _has_qualified_creative_approval(item)]
    queued_qualified_approved = [item for item in qualified_approved if item.get("status") == "queued"]
    publish_state = _load_json(ROOT / "data/local/youtube/publish_state.json").get("records", {})
    uploaded_qualified = [
        item
        for item in qualified_approved
        if item.get("status") == "uploaded"
        and isinstance(publish_state.get(item.get("content_id")), dict)
        and publish_state[item.get("content_id")].get("status") == "uploaded"
        and bool(publish_state[item.get("content_id")].get("video_id"))
    ]
    return {
        "x": {
            "autonomous_green": len(x_autonomous.get("publishable", [])),
            "awaiting_human_approval": len(x_autonomous.get("awaiting_human_approval", [])),
            "blocked": len(x_autonomous.get("blocked", [])),
            "manual_pending": sum(1 for item in x_manual_items if not item.get("published", False)),
            "manual_items": [item.get("content_id") for item in x_manual_items],
            "external_publication_evidence": bool(confirmed_x),
            "confirmed_publications": len(confirmed_x),
            "live_api_publication_evidence": any(item.get("post_id") for item in confirmed_x),
            "manual_publication_evidence": any(not item.get("post_id") for item in confirmed_x),
        },
        "youtube": {
            "queued": sum(1 for item in youtube_items if item.get("status") == "queued"),
            "uploaded_historical": sum(1 for item in youtube_items if item.get("status") == "uploaded"),
            "ambiguous_historical": sum(1 for item in youtube_items if item.get("status") == "ambiguous"),
            "pending_creative_approval": sum(
                1 for item in youtube_items if item.get("creative_approval_state") == "pending_review"
            ),
            "queued_pending_creative_approval": sum(
                1
                for item in youtube_items
                if item.get("status") == "queued" and item.get("creative_approval_state") == "pending_review"
            ),
            "neural_voice_pending_review": sum(
                1
                for item in youtube_items
                if item.get("audio_mode") == "neural_voice" and item.get("creative_approval_state") == "pending_review"
            ),
            "approved": sum(1 for item in youtube_items if item.get("creative_approval_state") == "approved"),
            "qualified_approved": len(qualified_approved),
            "queued_qualified_approved": len(queued_qualified_approved),
            "policy_disqualified_approved": sum(
                1
                for item in youtube_items
                if item.get("creative_approval_state") == "approved" and not _has_qualified_creative_approval(item)
            ),
            "audio_modes": dict(Counter(item.get("audio_mode", "unknown") for item in youtube_items)),
            "live_upload_allowed": False,
            "live_upload_evidence": bool(confirmed_youtube),
            "historical_upload_evidence": bool(confirmed_youtube),
            "confirmed_uploads": len(confirmed_youtube),
            "current_approved_upload_evidence": bool(uploaded_qualified),
        },
    }


def _has_qualified_creative_approval(item: dict[str, Any]) -> bool:
    checksum = item.get("video_checksum")
    return bool(
        item.get("creative_approval_state") == "approved"
        and item.get("creative_approved_at")
        and item.get("creative_reviewed_by")
        and checksum
        and item.get("creative_approval_video_checksum") == checksum
        and item.get("audio_mode") == "neural_voice"
        and item.get("narration_provider") == "elevenlabs"
        and item.get("narration_reused") is True
        and item.get("narration_voice_id")
        and item.get("narration_model_id")
    )


def _discovery_summary() -> dict[str, Any]:
    from app.discovery.approval import DiscoveryApprovalEmailConfig

    state = _load_json(ROOT / "data/local/discovery/worker_state.json")
    providers = state.get("providers", [])
    google = next((item for item in providers if item.get("provider") == "google_trends"), {})
    google_news = next((item for item in providers if item.get("provider") == "google_news"), {})
    approval_config = DiscoveryApprovalEmailConfig.from_environment()
    return {
        "cycle_state_present": bool(state),
        "updated_at": state.get("updated_at"),
        "google_trends_status": google.get("status"),
        "google_trends_limitation": google.get("limitation"),
        "google_news_status": google_news.get("status"),
        "google_news_signals": len(google_news.get("signals", [])) if isinstance(google_news.get("signals", []), list) else 0,
        "candidate_email_status": state.get("candidate_email_status", "unknown"),
        "candidate_outbox_drafts": len(state.get("drafted_candidate_keys", [])) if isinstance(state.get("drafted_candidate_keys", []), list) else 0,
        "approval_email_status": approval_config.readiness_status(),
        "approval_email_missing": approval_config.missing_configuration(),
        "candidate_suggestions": len(state.get("candidate_suggestions", [])),
    }


def _distribution_summary() -> dict[str, Any]:
    heartbeat = _load_json(ROOT / "data/local/distribution/worker_heartbeat.json")
    state = _load_json(ROOT / "data/local/distribution/worker_state.json")
    platform_statuses = heartbeat.get("platform_statuses", [])
    reported_status = heartbeat.get("status", "unknown")
    updated_at = heartbeat.get("updated_at")
    heartbeat_age_minutes = None
    status = reported_status
    health_reason = None
    if not heartbeat:
        status = "missing"
        health_reason = "heartbeat_missing"
    elif not updated_at:
        status = "stale"
        health_reason = "heartbeat_timestamp_missing"
    else:
        try:
            parsed_at = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
            if parsed_at.tzinfo is None:
                parsed_at = parsed_at.replace(tzinfo=timezone.utc)
            heartbeat_age_minutes = (datetime.now(timezone.utc) - parsed_at.astimezone(timezone.utc)).total_seconds() / 60
            if heartbeat_age_minutes < 0:
                status = "stale"
                health_reason = "heartbeat_timestamp_in_future"
            elif heartbeat_age_minutes > WORKER_HEARTBEAT_MAX_AGE_MINUTES and reported_status == "ok":
                status = "stale"
                health_reason = "heartbeat_expired"
        except (TypeError, ValueError, OverflowError):
            status = "stale"
            health_reason = "heartbeat_timestamp_invalid"
    return {
        "heartbeat_present": bool(heartbeat),
        "status": status,
        "reported_status": reported_status,
        "health_reason": health_reason,
        "heartbeat_age_minutes": round(heartbeat_age_minutes, 1) if heartbeat_age_minutes is not None else None,
        "max_heartbeat_age_minutes": WORKER_HEARTBEAT_MAX_AGE_MINUTES,
        "updated_at": updated_at,
        "platform_statuses": platform_statuses if isinstance(platform_statuses, list) else [],
        "dead_letters": sorted(
            key
            for key, record in (state.get("records", {}) or {}).items()
            if isinstance(record, dict) and record.get("dead_letter") is True
        ),
    }


def _database_summary() -> dict[str, Any]:
    from app.storage.database import create_database_engine
    from app.monetization.models import ReferralTaskStatus
    from app.storage.monetization import MonetizationRepository

    repository = MonetizationRepository(create_database_engine())
    landings = repository.landing_visits()
    clicks = repository.outbound_clicks()
    attributions = repository.revenue_attributions()
    performance = repository.content_performance()
    metrics = repository.metrics()
    verified = [item for item in attributions if item.attribution_status.value == "VERIFIED"]
    performance_by_platform: dict[str, dict[str, Any]] = {}
    for item in performance:
        bucket = performance_by_platform.setdefault(item.platform.value, {"records": 0})
        bucket["records"] += 1
        for field in (
            "impressions",
            "views",
            "engagements",
            "link_clicks",
            "profile_visits",
            "followers_gained",
            "subscribers_gained",
        ):
            value = getattr(item, field)
            if value is not None:
                bucket[field] = bucket.get(field, 0) + value
        if item.average_retention_percent is not None:
            bucket["retention_records"] = bucket.get("retention_records", 0) + 1
    return {
        "inbound": {
            "landing_events": len(landings),
            "channels": dict(Counter(item.channel for item in landings)),
            "utm_sources": dict(Counter(item.utm_source or "(none)" for item in landings)),
            "utm_campaigns": dict(Counter(item.utm_campaign or "(none)" for item in landings)),
        },
        "outbound": {
            "clicks": len(clicks),
            "destinations": dict(Counter(item.destination_slug for item in clicks)),
            "source_pages": dict(Counter(item.source_page or "(none)" for item in clicks)),
            "target_kinds": dict(Counter(item.target_url_kind for item in clicks)),
        },
        "revenue": {
            "attribution_records": len(attributions),
            "verified_records": len(verified),
            "metrics": {
                "outbound_clicks": metrics.outbound_clicks,
                "verified_conversions": _metric_payload(metrics.verified_conversions),
                "verified_revenue": _metric_payload(metrics.verified_revenue),
                "earnings_per_click": _metric_payload(metrics.earnings_per_click),
                "verified_conversion_rate": _metric_payload(metrics.verified_conversion_rate),
            },
        },
        "referrals": _referral_summary(repository, ReferralTaskStatus.OPEN),
        "content_performance": {
            "records": len(performance),
            "by_platform": performance_by_platform,
        },
    }


def _referral_summary(repository: Any, open_task_status: Any) -> dict[str, Any]:
    from app.monetization.referral_operations import ReferralOperationsService

    summary = ReferralOperationsService(repository).coverage_summary()
    open_tasks = repository.referral_tasks(status=open_task_status)
    return {
        "total_published_opportunities": summary.total_published_opportunities,
        "active": summary.referral_active_count,
        "missing": summary.referral_missing_count,
        "pending": summary.referral_pending_count,
        "no_program_found": summary.no_program_found_count,
        "expired": summary.expired_count,
        "reverify": summary.reverify_count,
        "coverage_percent": str(summary.referral_coverage_percentage),
        "open_tasks": len(open_tasks),
    }


def _public_runtime_measurement(public_status_url: str) -> dict[str, Any]:
    parsed = urlparse(public_status_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return {"available": False, "reason": "public_status_url_must_be_an_https_origin"}
    try:
        response = httpx.get(f"{public_status_url.rstrip('/')}/api/v1/ops/status", timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        measurement = payload.get("measurement", {})
        first_party = measurement.get("first_party", {})
        return {
            "available": True,
            "source": "public_ops_status",
            "api_status": payload.get("status"),
            "generated_at": payload.get("generated_at"),
            "measurement_status": measurement.get("status"),
            "aggregate_event_counts": {
                "landing_events": first_party.get("landing_events"),
                "outbound_redirect_events": first_party.get("outbound_clicks"),
                "content_performance_records": first_party.get("content_performance_records"),
            },
            "warning": "Aggregate application event counts are not unique human users, verified partner clicks, conversions, or revenue.",
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"available": False, "source": "public_ops_status", "error_type": type(exc).__name__}


def build_report(*, public_status_url: str | None = None) -> dict[str, Any]:
    _load_local_environment()
    report: dict[str, Any] = {
        "status": "PASS",
        "read_only": True,
        "source_root": str(ROOT),
        "queues": _queue_summary(),
        "discovery": _discovery_summary(),
        "distribution": _distribution_summary(),
    }
    try:
        report["database"] = _database_summary()
    except Exception as exc:  # pragma: no cover - operational failure path
        report["status"] = "DEGRADED"
        report["database"] = {"available": False, "error_type": type(exc).__name__}
    if report["distribution"].get("status") != "ok":
        report["status"] = "DEGRADED"
    database = report["database"]
    queues = report["queues"]
    report["business_status"] = "INCOMPLETE"
    report["closure_gates"] = {
        "discovery_cycle_executed": report["discovery"]["cycle_state_present"],
        "distribution_worker_healthy": report["distribution"]["status"] == "ok",
        "mailbox_candidate_loop_exercised": _candidate_mailbox_was_exercised(report["discovery"]["candidate_email_status"]),
        "approval_mailbox_ready": report["discovery"]["approval_email_status"] == "READY",
        "human_creative_approval": queues["youtube"]["queued_qualified_approved"] > 0,
        "x_live_publication_evidence": queues["x"]["live_api_publication_evidence"],
        # Historical uploads prove only that an old item was uploaded.  The
        # current growth gate must require a checksum-bound creative approval
        # for the current queue; otherwise a stale upload could make the plan
        # look complete while every current Short is still review-only.
        "youtube_live_publication_evidence": queues["youtube"]["current_approved_upload_evidence"],
        "commercial_click_data": database.get("outbound", {}).get("clicks", 0) > 0,
        "verified_revenue_data": database.get("revenue", {}).get("verified_records", 0) > 0,
    }
    report["measurement"] = {
        "acquisition_data_available": database.get("inbound", {}).get("landing_events", 0) > 0,
        "outbound_click_data_available": database.get("outbound", {}).get("clicks", 0) > 0,
        "verified_revenue_available": database.get("revenue", {}).get("verified_records", 0) > 0,
        "local_store_scope": "The database queried by this script's current environment; it is not assumed to be production.",
        "production_runtime": _public_runtime_measurement(public_status_url) if public_status_url else {
            "available": False,
            "reason": "not_requested",
        },
        "revenue_target_reached": False,
        "note": "No revenue target is credited without verified partner evidence. Production event counts are aggregate and do not prove unique people or human clicks.",
    }
    return report


def _candidate_mailbox_was_exercised(status: object) -> bool:
    """Return true only after the candidate notification was actually sent."""
    return str(status or "").strip().casefold() == "sent"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON output path; report remains read-only.")
    parser.add_argument(
        "--public-status-url",
        help="Optional public HTTPS origin (for example https://gamcryp.com) for aggregate production measurement status.",
    )
    args = parser.parse_args()
    payload = json.dumps(
        build_report(public_status_url=args.public_status_url),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    ) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
