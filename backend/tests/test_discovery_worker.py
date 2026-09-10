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
