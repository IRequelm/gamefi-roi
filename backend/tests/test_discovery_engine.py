from datetime import UTC, datetime
import json

from sqlalchemy import create_engine

from app.discovery.content_intelligence import build_editorial_brief
from app.discovery.engine import DiscoveryRecord, EvidenceRecord, Signal, evaluate_admission, normalize_entity, score_discovery
from app.discovery.providers import GoogleTrendsProvider
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
    repository = DiscoveryRepository(engine)
    _, outcome = repository.upsert(record)
    assert outcome == "AUTO_ADD_GUIDE"
    assert [item.name for item in repository.dynamic_opportunities()] == ["Grass.io"]
    page, total = ApiDataService(engine).opportunities_page(limit=100, offset=0)
    assert total == len(page)
    assert any(item.name == "Grass.io" and item.admission_mode == "GUIDE_ONLY" for item in page)
    assert build_editorial_brief(record).prohibited_claims


def test_trends_provider_is_explicit_when_query_values_are_not_safe_to_infer(monkeypatch):
    monkeypatch.setattr("app.discovery.providers.urlopen", lambda *args, **kwargs: type("R", (), {"status": 200, "read": lambda self: b"not-json", "__enter__": lambda self: self, "__exit__": lambda *args: None})())
    result = GoogleTrendsProvider().probe()
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
    result = GoogleTrendsProvider().query(("GameFi", "DePIN"))
    assert result.status == "LIVE"
    assert result.signals[0]["status"] == "LIVE_RELATIVE_INDEX"
    assert "not absolute search volume" in result.signals[0]["explanation"]
