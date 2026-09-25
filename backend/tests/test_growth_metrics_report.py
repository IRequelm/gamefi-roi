import json
import os
from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace

from scripts import growth_metrics_report


def test_report_loads_local_env_without_printing_secret_values(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED=true\n"
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO=operator@example.com\n"
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM=gamcryp@example.com\n"
        "GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD=secret-value\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(growth_metrics_report, "ROOT", tmp_path)
    for key in (
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED",
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO",
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM",
        "GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    growth_metrics_report._load_local_environment()

    assert os.environ["GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED"] == "true"
    assert os.environ["GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO"] == "operator@example.com"


def test_queue_summary_distinguishes_manual_api_and_historical_evidence(tmp_path, monkeypatch):
    x_dir = tmp_path / "data/local/x"
    youtube_dir = tmp_path / "data/local/youtube"
    x_dir.mkdir(parents=True)
    youtube_dir.mkdir(parents=True)
    (x_dir / "publications.json").write_text(
        json.dumps(
            {
                "publications": [
                    {"content_id": "manual-1", "post_id": None, "status": "published"},
                    {"content_id": "api-1", "post_id": "123", "status": "published"},
                    {"content_id": "failed-1", "post_id": None, "status": "failed"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (youtube_dir / "publish_state.json").write_text(
        json.dumps(
            {
                "records": {
                    "uploaded": {"status": "uploaded", "video_id": "video-1"},
                    "ambiguous": {"status": "ambiguous", "video_id": None},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(growth_metrics_report, "ROOT", tmp_path)

    summary = growth_metrics_report._queue_summary()

    assert summary["x"]["external_publication_evidence"] is True
    assert summary["x"]["confirmed_publications"] == 2
    assert summary["x"]["live_api_publication_evidence"] is True
    assert summary["x"]["manual_publication_evidence"] is True
    assert summary["youtube"]["live_upload_evidence"] is True
    assert summary["youtube"]["confirmed_uploads"] == 1
    assert summary["youtube"]["current_approved_upload_evidence"] is False


def test_queue_summary_does_not_count_music_only_approval_as_publishable(tmp_path, monkeypatch):
    queue_dir = tmp_path / "distribution/publish_queue"
    queue_dir.mkdir(parents=True)
    youtube_dir = tmp_path / "data/local/youtube"
    youtube_dir.mkdir(parents=True)
    (queue_dir / "youtube_short_handoff.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "content_id": "music-only",
                        "status": "queued",
                        "creative_approval_state": "approved",
                        "creative_approved_at": "2026-09-23T00:00:00+00:00",
                        "creative_reviewed_by": "operator",
                        "video_checksum": "a" * 64,
                        "creative_approval_video_checksum": "a" * 64,
                        "audio_mode": "music_only",
                        "narration_provider": "local_music",
                        "narration_reused": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(growth_metrics_report, "ROOT", tmp_path)

    summary = growth_metrics_report._queue_summary()

    assert summary["youtube"]["approved"] == 1
    assert summary["youtube"]["queued_qualified_approved"] == 0
    assert summary["youtube"]["policy_disqualified_approved"] == 1
    assert summary["youtube"]["current_approved_upload_evidence"] is False


def test_historical_youtube_upload_does_not_satisfy_current_publication_gate(monkeypatch):
    monkeypatch.setattr(growth_metrics_report, "_load_local_environment", lambda: None)
    monkeypatch.setattr(
        growth_metrics_report,
        "_queue_summary",
        lambda: {
            "x": {"live_api_publication_evidence": False},
            "youtube": {
                "approved": 0,
                "queued_qualified_approved": 0,
                "live_upload_evidence": True,
                "current_approved_upload_evidence": False,
            },
        },
    )
    monkeypatch.setattr(
        growth_metrics_report,
        "_discovery_summary",
        lambda: {
            "cycle_state_present": True,
            "candidate_email_status": "disabled",
            "approval_email_status": "DISABLED",
        },
    )
    monkeypatch.setattr(
        growth_metrics_report,
        "_distribution_summary",
        lambda: {"status": "ok"},
    )
    monkeypatch.setattr(
        growth_metrics_report,
        "_database_summary",
        lambda: {"outbound": {"clicks": 0}, "revenue": {"verified_records": 0}},
    )

    report = growth_metrics_report.build_report()

    assert report["queues"]["youtube"]["live_upload_evidence"] is True
    assert report["closure_gates"]["youtube_live_publication_evidence"] is False


def test_distribution_summary_surfaces_degraded_worker_and_dead_letters(tmp_path, monkeypatch):
    distribution_dir = tmp_path / "data/local/distribution"
    distribution_dir.mkdir(parents=True)
    (distribution_dir / "worker_heartbeat.json").write_text(
        json.dumps(
            {
                "status": "degraded",
                "updated_at": "2026-09-21T00:00:00+00:00",
                "platform_statuses": [{"platform": "YouTubeShortHandoff", "status": "dead_letter"}],
            }
        ),
        encoding="utf-8",
    )
    (distribution_dir / "worker_state.json").write_text(
        json.dumps({"records": {"YouTubeShortHandoff": {"dead_letter": True}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(growth_metrics_report, "ROOT", tmp_path)

    summary = growth_metrics_report._distribution_summary()

    assert summary["status"] == "degraded"
    assert summary["dead_letters"] == ["YouTubeShortHandoff"]
    assert summary["platform_statuses"][0]["status"] == "dead_letter"


def test_distribution_summary_marks_expired_ok_heartbeat_stale(tmp_path, monkeypatch):
    distribution_dir = tmp_path / "data/local/distribution"
    distribution_dir.mkdir(parents=True)
    (distribution_dir / "worker_heartbeat.json").write_text(
        json.dumps(
            {
                "pid": 99999999,
                "status": "ok",
                "updated_at": "2020-01-01T00:00:00+00:00",
                "platform_statuses": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(growth_metrics_report, "ROOT", tmp_path)

    summary = growth_metrics_report._distribution_summary()

    assert summary["reported_status"] == "ok"
    assert summary["status"] == "stale"
    assert summary["health_reason"] == "heartbeat_expired"
    assert summary["worker_process_alive"] is False
    assert summary["heartbeat_age_minutes"] > summary["max_heartbeat_age_minutes"]


def test_distribution_summary_requires_live_process_for_fresh_ok_heartbeat(tmp_path, monkeypatch):
    distribution_dir = tmp_path / "data/local/distribution"
    distribution_dir.mkdir(parents=True)
    (distribution_dir / "worker_heartbeat.json").write_text(
        json.dumps(
            {
                "pid": 99999999,
                "status": "ok",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "platform_statuses": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(growth_metrics_report, "ROOT", tmp_path)

    summary = growth_metrics_report._distribution_summary()

    assert summary["heartbeat_age_minutes"] == 0
    assert summary["status"] == "stopped"
    assert summary["health_reason"] == "worker_process_not_running"


def test_public_runtime_measurement_labels_aggregate_counts(monkeypatch):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "status": "degraded",
            "generated_at": "2026-09-23T19:00:00Z",
            "measurement": {
                "status": "data_available",
                "first_party": {
                    "landing_events": 3546,
                    "outbound_clicks": 1431,
                    "content_performance_records": 0,
                },
            },
        },
    )
    monkeypatch.setattr(growth_metrics_report.httpx, "get", lambda *args, **kwargs: response)

    summary = growth_metrics_report._public_runtime_measurement("https://gamcryp.com")

    assert summary["available"] is True
    assert summary["aggregate_event_counts"]["landing_events"] == 3546
    assert "not unique human users" in summary["warning"]


def test_public_runtime_measurement_rejects_non_origin_urls():
    summary = growth_metrics_report._public_runtime_measurement("http://localhost:8000/path")

    assert summary == {"available": False, "reason": "public_status_url_must_be_an_https_origin"}


def test_referral_summary_exposes_coverage_and_open_operator_tasks(monkeypatch):
    class Repository:
        def referral_tasks(self, *, status):
            return ["task-1", "task-2"]

    monkeypatch.setattr(
        "app.monetization.referral_operations.ReferralOperationsService.coverage_summary",
        lambda self: SimpleNamespace(
            total_published_opportunities=50,
            referral_active_count=0,
            referral_missing_count=50,
            referral_pending_count=0,
            no_program_found_count=0,
            expired_count=0,
            reverify_count=0,
            referral_coverage_percentage=Decimal("0"),
        ),
    )
    from app.monetization.models import ReferralTaskStatus

    summary = growth_metrics_report._referral_summary(Repository(), ReferralTaskStatus.OPEN)

    assert summary["total_published_opportunities"] == 50
    assert summary["missing"] == 50
    assert summary["coverage_percent"] == "0"
    assert summary["open_tasks"] == 2


def test_candidate_mailbox_gate_requires_actual_delivery():
    assert growth_metrics_report._candidate_mailbox_was_exercised("sent") is True
    assert growth_metrics_report._candidate_mailbox_was_exercised("disabled") is False
    assert growth_metrics_report._candidate_mailbox_was_exercised("none") is False
    assert growth_metrics_report._candidate_mailbox_was_exercised("blocked:SMTPError") is False
