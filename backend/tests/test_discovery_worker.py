import json
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import create_engine

from app.discovery.providers import ProviderResult
from app.discovery.worker import DiscoveryWorker, DiscoveryWorkerConfig, _candidate_suggestions, _dry_run_e2e
from app.discovery.approval import DiscoveryApprovalEmailConfig, DiscoveryApprovalMailer
from app.storage.discovery import DiscoveryRepository
from app.storage.metadata import Base


def test_approval_email_readiness_is_explicit_without_exposing_secrets():
    disabled = DiscoveryApprovalEmailConfig(enabled=False)
    assert disabled.readiness_status() == "DISABLED"
    assert disabled.missing_configuration()["smtp"]
    assert disabled.missing_configuration()["imap"]
    assert DiscoveryApprovalEmailConfig(enabled=True).readiness_status() == "INCOMPLETE_SMTP_IMAP"
    ready = DiscoveryApprovalEmailConfig(
        enabled=True,
        to_address="operator@example.com",
        from_address="gamcryp@example.com",
        smtp_username="operator@example.com",
        smtp_password="smtp-secret",
        imap_username="operator@example.com",
        imap_password="imap-secret",
    )
    assert ready.readiness_status() == "READY"
    assert ready.missing_configuration() == {"smtp": [], "imap": []}


def test_research_lead_email_includes_source_locators(monkeypatch):
    captured = []

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def starttls(self, context):
            pass

        def login(self, username, password):
            pass

        def send_message(self, message):
            captured.append(message)

    monkeypatch.setattr("app.discovery.approval.smtplib.SMTP", lambda *args, **kwargs: Client())
    config = DiscoveryApprovalEmailConfig(
        enabled=True,
        to_address="operator@example.com",
        from_address="gamcryp@example.com",
        smtp_username="operator@example.com",
        smtp_password="smtp-secret",
    )
    DiscoveryApprovalMailer(config).send_research_lead(
        {
            "canonical_name": "Example News Lead",
            "discovery_source": "google_news",
            "discovery_query": "Example News Lead",
            "why_discovered": "Article lead requires official research.",
            "source_locator": "https://news.google.com/rss/articles/example",
            "search_locator": "https://news.google.com/rss/search?q=DePIN",
        },
        "a" * 24,
    )
    body = captured[0].get_content()
    assert "Source locator: https://news.google.com/rss/articles/example" in body
    assert "Search locator: https://news.google.com/rss/search?q=DePIN" in body


def test_disabled_email_writes_unsent_token_bound_outbox_draft(monkeypatch, tmp_path):
    config = DiscoveryApprovalEmailConfig(enabled=False, outbox_dir=tmp_path / "approval-outbox")
    lead = {
        "discovery_id": "lead-outbox-fixture",
        "canonical_name": "Outbox News Lead",
        "discovery_source": "google_news",
        "discovery_query": "Outbox News Lead",
        "why_discovered": "Article lead requires official research.",
        "source_locator": "https://news.google.com/rss/articles/outbox",
        "search_locator": "https://news.google.com/rss/search?q=DePIN",
    }

    path = DiscoveryApprovalMailer(config).write_research_lead_draft(lead, "a" * 24)

    assert path.parent == tmp_path / "approval-outbox"
    body = path.read_text(encoding="utf-8")
    assert "Source locator: https://news.google.com/rss/articles/outbox" in body
    assert "SITEYE_EKLE " + "a" * 24 in body
    assert "To:" not in body


def test_dry_run_e2e_exercises_token_bound_research_approval_without_external_io():
    payload = _dry_run_e2e()

    assert payload["fixture"] is True
    assert payload["external_email_sent"] is False
    assert payload["publish_performed"] is False
    assert payload["lead_persisted"] is True
    assert payload["approval_command_parsed"] is True
    assert payload["approval_status"] == "approved"
    assert payload["candidate"]["opportunity_type"] == "RESEARCH"
    assert payload["candidate"]["roi_unavailable"] is True
    assert payload["editorial_brief_created"] is True


def test_worker_once_persists_provider_state_without_publishing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.discovery.worker.GoogleTrendsProvider.probe", lambda self: type("R", (), {
        "provider": "google_trends", "status": "BLOCKED", "retrieved_at": datetime.now(UTC),
        "signals": (), "limitation": "test limitation",
    })())
    monkeypatch.setattr("app.discovery.worker.GoogleNewsResearchProvider.probe", lambda self: type("R", (), {
        "provider": "google_news", "status": "QUERY_EMPTY", "retrieved_at": datetime.now(UTC),
        "signals": (), "limitation": "test news limitation",
    })())
    path = tmp_path / "discovery" / "state.json"
    payload = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=path)).run_once()
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert payload["publish_performed"] is False
    assert persisted["state_version"] == "discovery-worker-v1"
    assert persisted["providers"][0]["status"] == "BLOCKED"


def test_google_news_candidate_reason_does_not_claim_trend_volume():
    result = ProviderResult(
        "google_news",
        "LIVE_RESEARCH",
        datetime.now(UTC),
        signals=(
            {
                "name": "related_query",
                "keyword": "Example DePIN article",
                "candidate_hint": "Example DePIN project",
                "value": None,
                "source": "google_news",
                "source_locator": "https://news.example/depin",
                "search_locator": "https://news.google.com/rss/search?q=DePIN",
                "status": "LIVE_GOOGLE_NEWS_RESEARCH_LEAD",
            },
        ),
    )
    suggestions = _candidate_suggestions((result,))
    assert suggestions[0]["discovery_source"] == "google_news"
    assert "not trend volume" in suggestions[0]["reason"]
    assert suggestions[0]["source_locator"] == "https://news.example/depin"
    assert suggestions[0]["search_locator"] == "https://news.google.com/rss/search?q=DePIN"


def test_google_trends_candidate_suggestions_reject_generic_explainers():
    result = ProviderResult(
        "google_trends",
        "LIVE",
        datetime.now(UTC),
        signals=(
            {"name": "related_query", "keyword": "what is a crypto node", "value": 100},
            {"name": "related_query", "keyword": "Example Node Protocol", "value": 80},
        ),
    )
    suggestions = _candidate_suggestions((result,))
    assert [item["candidate_name"] for item in suggestions] == ["Example Node Protocol"]


def test_worker_rejects_dangerously_fast_loop(tmp_path):
    worker = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=tmp_path / "state.json", interval_seconds=299))
    try:
        worker.run_forever()
    except ValueError as exc:
        assert "at least 300" in str(exc)
    else:
        raise AssertionError("worker accepted an unsafe interval")


def test_market_provider_preserves_decimal_quote_and_provenance(monkeypatch):
    class Observation:
        value = "0.5450487089203774"
        source_locator = "https://api.coingecko.com/api/v3/simple/price"
        observed_at = datetime.now(UTC)
        retrieved_at = datetime.now(UTC)
        status = type("Status", (), {"value": "fresh"})()

    class Source:
        def __init__(self, settings):
            pass

        def get_token_prices(self, request):
            return [Observation()]

        def close(self):
            pass

    monkeypatch.setattr("app.discovery.providers.get_settings", lambda: type("Settings", (), {"market_data_price_freshness_seconds": 300})())
    monkeypatch.setattr("app.discovery.providers.CoinGeckoMarketDataSource", Source)
    from app.discovery.providers import CoinGeckoMarketProvider

    result = CoinGeckoMarketProvider().query(("akash-network",))
    assert result.status == "LIVE"
    assert result.signals[0]["value"] == "0.5450487089203774"
    assert result.signals[0]["source_locator"].startswith("https://api.coingecko.com")


def test_worker_persists_token_bound_research_lead_before_email(monkeypatch, tmp_path):
    db_engine = create_engine(f"sqlite:///{tmp_path / 'discovery.db'}")
    Base.metadata.create_all(db_engine)
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED", "true")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO", "operator@example.com")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM", "gamcryp@example.com")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_SMTP_USERNAME", "operator@example.com")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD", "test-password")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_USERNAME", "operator@example.com")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_PASSWORD", "test-password")
    monkeypatch.setattr(
        "app.discovery.worker.get_settings",
        lambda: SimpleNamespace(sqlalchemy_database_url=f"sqlite:///{tmp_path / 'discovery.db'}", database_backend="sqlite"),
    )
    monkeypatch.setattr("app.discovery.worker.create_database_engine", lambda settings: db_engine)
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.discovery.worker.DiscoveryApprovalMailer.send_research_lead",
        lambda self, lead, token, **kwargs: sent.append((str(lead["canonical_name"]), token)),
    )

    worker = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=tmp_path / "state.json"))
    status, _keys, _drafts = worker._notify_new_suggestions(
        [{
            "candidate_name": "Example Trend Project",
            "discovery_source": "google_trends",
            "discovery_query": "Example Trend Project",
            "trend_value": 72,
            "reason": "Research lead",
        }],
        now=datetime.now(UTC),
    )

    assert status == "sent"
    assert sent and sent[0][0] == "Example Trend Project"
    records = DiscoveryRepository(db_engine).records()
    assert records[0]["approval_status"] == "PENDING"
    assert records[0]["admission_outcome"] == "RESEARCH_CANDIDATE"
    assert DiscoveryRepository(db_engine).decide_token(sent[0][1], approve=True)["status"] == "approved"
    assert DiscoveryRepository(db_engine).dynamic_opportunities()[0].status == "candidate"
    db_engine.dispose()


def test_worker_persists_research_lead_when_email_is_disabled(monkeypatch, tmp_path):
    db_engine = create_engine(f"sqlite:///{tmp_path / 'discovery-disabled-email.db'}")
    Base.metadata.create_all(db_engine)
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED", "false")
    monkeypatch.setenv("GAMEFI_DISCOVERY_APPROVAL_OUTBOX_DIR", str(tmp_path / "approval-outbox"))
    monkeypatch.setattr(
        "app.discovery.worker.get_settings",
        lambda: SimpleNamespace(sqlalchemy_database_url=f"sqlite:///{tmp_path / 'discovery-disabled-email.db'}", database_backend="sqlite"),
    )
    monkeypatch.setattr("app.discovery.worker.create_database_engine", lambda settings: db_engine)

    worker = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=tmp_path / "state.json"))
    status, emailed_keys, drafted_keys = worker._notify_new_suggestions(
        [{
            "candidate_name": "Persisted News Lead",
            "discovery_source": "google_news",
            "discovery_query": "Persisted News Lead",
            "trend_value": None,
            "reason": "Article lead requires official-source research.",
            "source_locator": "https://news.example/article",
            "search_locator": "https://news.google.com/rss/search?q=DePIN",
        }],
        now=datetime.now(UTC),
    )

    records = DiscoveryRepository(db_engine).records()
    assert status == "outbox"
    assert emailed_keys == []
    assert drafted_keys
    assert len(list((tmp_path / "approval-outbox").glob("*.eml"))) == 1
    assert records[0]["approval_status"] == "PENDING"
    assert records[0]["admission_outcome"] == "RESEARCH_CANDIDATE"
    assert records[0]["signals"][0]["name"] == "search_momentum"
    assert records[0]["source_locator"] == "https://news.example/article"
    assert records[0]["search_locator"] == "https://news.google.com/rss/search?q=DePIN"
    db_engine.dispose()


def test_worker_retries_pending_lead_after_email_delivery_failure(monkeypatch, tmp_path):
    db_engine = create_engine(f"sqlite:///{tmp_path / 'discovery-retry.db'}")
    Base.metadata.create_all(db_engine)
    for key, value in {
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED": "true",
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO": "operator@example.com",
        "GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM": "gamcryp@example.com",
        "GAMEFI_DISCOVERY_APPROVAL_SMTP_USERNAME": "operator@example.com",
        "GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD": "test-password",
        "GAMEFI_DISCOVERY_APPROVAL_IMAP_USERNAME": "operator@example.com",
        "GAMEFI_DISCOVERY_APPROVAL_IMAP_PASSWORD": "test-password",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        "app.discovery.worker.get_settings",
        lambda: SimpleNamespace(sqlalchemy_database_url=f"sqlite:///{tmp_path / 'discovery-retry.db'}", database_backend="sqlite"),
    )
    monkeypatch.setattr("app.discovery.worker.create_database_engine", lambda settings: db_engine)
    sent: list[str] = []
    attempts = {"count": 0}

    def send_research_lead(_self, _lead, token, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("simulated SMTP outage")
        sent.append(token)

    monkeypatch.setattr("app.discovery.worker.DiscoveryApprovalMailer.send_research_lead", send_research_lead)
    suggestion = {
        "candidate_name": "Retry Trend Project",
        "discovery_source": "google_trends",
        "discovery_query": "Retry Trend Project",
        "trend_value": 74,
        "reason": "Research lead",
    }
    worker = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=tmp_path / "retry-state.json"))

    first_status, _, _ = worker._notify_new_suggestions([suggestion], now=datetime.now(UTC))
    second_status, _, _ = worker._notify_new_suggestions([suggestion], now=datetime.now(UTC))

    assert first_status.startswith("blocked:")
    assert second_status == "sent"
    assert len(sent) == 1
    assert DiscoveryRepository(db_engine).decide_token(sent[0], approve=True)["status"] == "approved"
    db_engine.dispose()
