from datetime import UTC, datetime
import json
from urllib.error import HTTPError

from sqlalchemy import create_engine

from app.discovery.content_intelligence import build_editorial_brief
from app.discovery.approval import DiscoveryApprovalEmailConfig, parse_approval_command
from app.discovery.engine import DiscoveryRecord, EvidenceRecord, Signal, evaluate_admission, normalize_entity, score_discovery
from app.discovery.providers import GoogleNewsResearchProvider, GoogleTrendsProvider, _google_news_candidate_hint
from app.discovery.providers import _google_news_researchable_title
from app.content_package.generator import build_content_packages
from app.storage.discovery import DiscoveryRepository
from app.storage.metadata import Base
from app.api.v1.service import ApiDataService


def _record(*facts: str, url: str = "https://example.com") -> DiscoveryRecord:
    now = datetime.now(UTC)
    return DiscoveryRecord(
        canonical_name="Grass.io",
        aliases=["Grass", "GetGrass"],
        category="DEPIN_NODE",
        official_url=url,
        discovery_source="test",
        evidence_strength="MEDIUM",
        signals=[Signal("search_momentum", 80, "test", now, "FIXTURE", "high demand")],
        evidence=[EvidenceRecord(url, "OFFICIAL_PROJECT", fact, True, now) for fact in facts],
    )


def test_normalization_is_deterministic_for_aliases():
    assert normalize_entity("Grass.io") == normalize_entity("Grass")
    assert normalize_entity("GetGrass") == normalize_entity("Grass")


def test_guide_admission_does_not_require_roi():
    record = score_discovery(_record("identity", "participation", "reward_mechanism"))
    assert evaluate_admission(record).outcome == "AUTO_ADD_GUIDE"


def test_admission_outcomes_fail_closed_for_missing_or_conflicting_evidence():
    assert evaluate_admission(_record("identity")).outcome == "KEEP_RESEARCHING"
    assert evaluate_admission(_record("identity", "participation", "reward_mechanism", url="http://bad.example")).outcome == "QUARANTINE"
    assert evaluate_admission(_record("identity", "participation", "reward_mechanism", "entry_cost", "realizable_reward_value", "exit_path")).outcome == "AUTO_ADD_MODELED"


def test_dynamic_catalog_persists_and_brief_is_explainable():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    record = score_discovery(_record("identity", "participation", "reward_mechanism"))
    class FakeMailer:
        config = DiscoveryApprovalEmailConfig(enabled=True)

        def __init__(self):
            self.token = None

        def send(self, record, decision, token):
            self.token = token

    mailer = FakeMailer()
    repository = DiscoveryRepository(engine, approval_mailer=mailer)
    _, outcome = repository.upsert(record)
    assert outcome == "AUTO_ADD_GUIDE"
    assert repository.dynamic_opportunities() == ()
    assert mailer.token
    assert repository.decide_token(mailer.token, approve=True)["status"] == "approved"
    assert repository.decide_token(mailer.token, approve=True)["status"] == "invalid"
    assert [item.name for item in repository.dynamic_opportunities()] == ["Grass.io"]
    assert any(package.opportunity_id == "discovered-grass" for package in build_content_packages(engine=engine))
    page, total = ApiDataService(engine).opportunities_page(limit=100, offset=0)
    assert total == len(page)
    assert any(item.name == "Grass.io" and item.admission_mode == "GUIDE_ONLY" for item in page)
    assert build_editorial_brief(record).prohibited_claims


def test_trend_lead_approval_adds_only_a_research_candidate_without_roi():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = DiscoveryRepository(engine)
    payload, token, is_new = repository.upsert_research_lead({
        "candidate_name": "Example Trend Project",
        "discovery_source": "google_trends",
        "discovery_query": "Example Trend Project",
        "trend_value": 78,
        "reason": "Related query requires official-source research.",
        "source_locator": "https://news.example/article",
        "search_locator": "https://news.google.com/rss/search?q=Example",
    })

    assert is_new is True
    assert token
    assert repository.dynamic_opportunities() == ()
    assert repository.decide_token(token, approve=True)["status"] == "approved"
    assert repository.decide_token(token, approve=True)["status"] == "invalid"

    candidate = repository.dynamic_opportunities()[0]
    assert candidate.name == payload["canonical_name"]
    assert candidate.opportunity_type == "RESEARCH"
    assert candidate.status == "candidate"
    assert [(source.label, source.url, source.source_role) for source in candidate.official_source_references] == [
        ("Discovery article lead (not official)", "https://news.example/article", "OTHER_PUBLIC_EVIDENCE"),
        ("Discovery search source (not official)", "https://news.google.com/rss/search?q=Example", "OTHER_PUBLIC_EVIDENCE"),
    ]
    assert candidate.admission_mode == "GUIDE_ONLY"
    assert candidate.roi_unavailable is not None
    assert candidate.outbound_destination_slugs == ()


def test_approved_research_candidate_enrichment_promotes_guide_and_feeds_content():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = DiscoveryRepository(engine)
    payload, token, _is_new = repository.upsert_research_lead({
        "candidate_name": "Evidence Project",
        "discovery_source": "google_trends",
        "discovery_query": "Evidence Project",
        "trend_value": 82,
        "reason": "Research lead",
    })
    assert repository.decide_token(token, approve=True)["status"] == "approved"
    reviewed = datetime.now(UTC)
    evidence = [
        EvidenceRecord("https://official.example/", "OFFICIAL_PROJECT", "The official project identity is documented.", True, reviewed, fact_kind="identity"),
        EvidenceRecord("https://official.example/start", "OFFICIAL_PROJECT", "Operators follow the documented participation steps.", True, reviewed, fact_kind="participation"),
        EvidenceRecord("https://official.example/requirements", "OFFICIAL_PROJECT", "A compatible host and account are required.", True, reviewed, fact_kind="requirements"),
        EvidenceRecord("https://official.example/rewards", "OFFICIAL_PROJECT", "The project documents its reward mechanism.", True, reviewed, fact_kind="reward_mechanism"),
        EvidenceRecord("https://official.example/exit", "OFFICIAL_PROJECT", "The documented claim or exit path is described here.", True, reviewed, fact_kind="exit_path"),
    ]
    record, outcome = repository.enrich_research_candidate(
        str(payload["discovery_id"]),
        category="DEPIN_NODE",
        official_url="https://official.example/",
        evidence=evidence,
    )

    assert outcome == "AUTO_ADD_GUIDE"
    assert record.validation_status == "VERIFIED"
    candidate = next(item for item in repository.dynamic_opportunities() if item.name == "Evidence Project")
    assert candidate.status == "active"
    assert candidate.guidance is not None
    assert candidate.guidance.how_you_earn == ("The project documents its reward mechanism.",)
    packages = build_content_packages(engine=engine)
    matching = [package for package in packages if package.opportunity_id == candidate.opportunity_id and package.content_family == "HOW_YOU_EARN"]
    assert matching and matching[0].generation_status == "READY_FOR_REVIEW"
    assert any("reward mechanism" in point["text"] for point in matching[0].factual_talking_points)


def test_approval_parser_requires_explicit_token_command():
    assert parse_approval_command("please SITEYE_EKLE abcdefghijklmnopqrst") is not None
    assert parse_approval_command("siteye ekle abcdefghijklmnopqrst").command == "APPROVE"
    assert parse_approval_command("REDDET abcdefghijklmnopqrst").command == "REJECT"
    assert parse_approval_command("I approve this candidate") is None


def test_approval_parser_preserves_urlsafe_token_endings():
    for token in ("a" * 20 + "_", "a" * 20 + "-"):
        parsed = parse_approval_command(f"SITEYE_EKLE {token}")
        assert parsed is not None
        assert parsed.token == token


def test_trends_provider_is_explicit_when_query_values_are_not_safe_to_infer(monkeypatch):
    monkeypatch.setattr("app.discovery.providers.urlopen", lambda *args, **kwargs: type("R", (), {"status": 200, "read": lambda self: b"not-json", "__enter__": lambda self: self, "__exit__": lambda *args: None})())
    result = GoogleTrendsProvider(session_enabled=False).probe()
    assert result.status == "BLOCKED"
    assert not result.signals


def test_trends_query_normalizes_relative_series_without_calling_it_volume(monkeypatch):
    class Response:
        status = 200

        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.body

    explore = {"widgets": [{"id": "TIMESERIES", "token": "token", "request": {"series": "fixture"}}]}
    series = {"default": {"timelineData": [
        {"value": [10, 20]}, {"value": [20, 25]}, {"value": [40, 30]}, {"value": [50, 35]},
    ]}}
    responses = iter([
        Response((")]}'" + "," + json.dumps(explore)).encode()),
        Response((")]}'" + "," + json.dumps(series)).encode()),
    ])
    monkeypatch.setattr("app.discovery.providers.urlopen", lambda *args, **kwargs: next(responses))
    result = GoogleTrendsProvider(session_enabled=False).query(("GameFi", "DePIN"))
    assert result.status == "LIVE"
    assert result.signals[0]["status"] == "LIVE_RELATIVE_INDEX"
    assert "not absolute search volume" in result.signals[0]["explanation"]


def test_trends_query_exposes_related_queries_as_research_leads(monkeypatch):
    class Response:
        status = 200

        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.body

    explore = {"widgets": [{"id": "RELATED_QUERIES_0", "token": "token", "request": {"query": "fixture"}}]}
    related = {"default": {"rankedList": [{"rankedKeyword": [{"query": "new gamefi node", "value": 100}]}]}}
    responses = iter([
        Response((")]}'" + "," + json.dumps(explore)).encode()),
        Response((")]}'" + "," + json.dumps(related)).encode()),
    ])
    monkeypatch.setattr("app.discovery.providers.urlopen", lambda *args, **kwargs: next(responses))
    result = GoogleTrendsProvider(session_enabled=False).query(("GameFi",))
    assert result.status == "LIVE"
    assert result.signals[0]["name"] == "related_query"
    assert result.signals[0]["status"] == "LIVE_RELATED_QUERY"
    assert "research only" in result.signals[0]["explanation"]


def test_trends_rate_limit_uses_official_rss_research_fallback(monkeypatch):
    class Response:
        status = 200

        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.body

    rss = b'''<?xml version="1.0"?><rss><channel><item><title>depin provider</title><approx_traffic>500+</approx_traffic></item><item><title>unrelated sports</title><approx_traffic>20000+</approx_traffic></item></channel></rss>'''
    rate_limit = HTTPError("https://trends.google.com", 429, "rate limited", {}, None)
    calls = iter(("rate_limit", "rss"))

    def fake_urlopen(*args, **kwargs):
        if next(calls) == "rate_limit":
            raise rate_limit
        return Response(rss)

    monkeypatch.setattr("app.discovery.providers.urlopen", fake_urlopen)

    result = GoogleTrendsProvider(session_enabled=False).query(("GameFi",), geo="US")

    assert result.status == "LIVE_RSS"
    assert [signal["keyword"] for signal in result.signals] == ["depin provider"]
    assert result.signals[0]["status"] == "LIVE_RSS_RESEARCH_LEAD"
    assert "not absolute search volume" in result.signals[0]["explanation"]


def test_google_news_fallback_exposes_article_leads_without_trend_volume(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'''<?xml version="1.0"?><rss><channel><item><title>What Is DePIN and How Does It Work?</title><link>https://news.example/explainer</link></item><item><title>New DePIN provider launches compute node</title><link>https://news.example/depin</link><pubDate>Mon, 21 Sep 2026 00:00:00 GMT</pubDate></item><item><title>Old DePIN provider update</title><link>https://news.example/old</link><pubDate>Mon, 21 Sep 2025 00:00:00 GMT</pubDate></item><item><title>Unrelated sports result</title><link>https://news.example/sports</link></item></channel></rss>'''

    monkeypatch.setattr("app.discovery.providers.urlopen", lambda *args, **kwargs: Response())
    result = GoogleNewsResearchProvider().probe()

    assert result.status == "LIVE_RESEARCH"
    assert result.provider == "google_news"
    assert [signal["keyword"] for signal in result.signals] == ["New DePIN provider launches compute node"]
    assert result.signals[0]["value"] is None
    assert result.signals[0]["status"] == "LIVE_GOOGLE_NEWS_RESEARCH_LEAD"
    assert "not Google Trends volume" in result.signals[0]["explanation"]


def test_google_news_research_filter_rejects_macro_headlines_but_keeps_project_leads():
    assert not _google_news_researchable_title("GameFi News: Gaming Sector Rallies, Funding Slips YoY")
    assert not _google_news_researchable_title("What Are the Top Crypto Trends in 2026?")
    assert not _google_news_researchable_title("Alby Hub Security Flaw: How to Check Whether Your Node Is Reachable")
    assert not _google_news_researchable_title("DeFi Superapp Legend Shuts Down After Failing to Scale")
    assert not _google_news_researchable_title("Bitcoin Is NOT Changed By Proof Of Node")


def test_google_news_candidate_hint_extracts_project_identity_from_headline():
    assert _google_news_candidate_hint("Pixels is killing old GameFi - Binance") == "Pixels"
    assert _google_news_candidate_hint("Battle Town (BTOWN) ICO Token Sale Review - CryptoRank") == "Battle Town (BTOWN)"
    assert _google_news_candidate_hint("Crypto.com integrates XYO as an initial DePIN network - CryptoNews") == "XYO"
    assert _google_news_candidate_hint("Solana DePIN startup Botanika raises $1.5M") == "Botanika"
    assert not _google_news_researchable_title("DePIN - Bit2Me")
    assert not _google_news_researchable_title("Decentralized Physical Infrastructure (DePIN)")
    assert not _google_news_researchable_title("Top #DePIN Projects by Annual Revenue")
    assert not _google_news_researchable_title("Web3 is dead? Only DeFi and DePIN remain")
    assert not _google_news_researchable_title("Best DePIN Cryptocurrencies to Watch in July 2026")
    assert _google_news_researchable_title("Mine-to-Earn Token PepeNode Leads the 2026 Charge")
    assert _google_news_researchable_title("AetheriumX Officially Launches Unified Web3 Platform")
