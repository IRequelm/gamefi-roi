import json
from datetime import UTC, datetime

from app.discovery.worker import DiscoveryWorker, DiscoveryWorkerConfig


def test_worker_once_persists_provider_state_without_publishing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.discovery.worker.GoogleTrendsProvider.probe", lambda self: type("R", (), {
        "provider": "google_trends", "status": "BLOCKED", "retrieved_at": datetime.now(UTC),
        "signals": (), "limitation": "test limitation",
    })())
    path = tmp_path / "discovery" / "state.json"
    payload = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=path)).run_once()
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert payload["publish_performed"] is False
    assert persisted["state_version"] == "discovery-worker-v1"
    assert persisted["providers"][0]["status"] == "BLOCKED"


def test_worker_rejects_dangerously_fast_loop(tmp_path):
    worker = DiscoveryWorker(config=DiscoveryWorkerConfig(state_file=tmp_path / "state.json", interval_seconds=299))
    try:
        worker.run_forever()
    except ValueError as exc:
        assert "at least 300" in str(exc)
    else:
        raise AssertionError("worker accepted an unsafe interval")
