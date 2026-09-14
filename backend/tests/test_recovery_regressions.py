from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from app.jobs import snapshot_refresh
from app.discovery.engine import evaluate_admission
from app.storage.discovery import DiscoveryRepository
from app.storage.metadata import Base
from app.api.v1.service import ApiDataService
from app.publishing.elevenlabs import NarrationAssetMetadata, reuse_existing_narration
from app.publishing.distribution_worker import WorkerState
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.video_render.factory import render_package, _script_for
from test_discovery_engine import _record
from test_video_render_factory import _package, _settings, _runner


@pytest.mark.parametrize("failures,skipped,expected", [(1,0,1),(0,5,0)])
def test_refresh_process_result_is_truthful(monkeypatch, failures, skipped, expected):
    monkeypatch.setattr("sys.argv", ["snapshot_refresh"])
    value = snapshot_refresh.RefreshCommandResult("refresh", (), 0, skipped, failures)
    monkeypatch.setattr(snapshot_refresh, "run_snapshot_refresh", lambda **kw: value)
    assert snapshot_refresh.main() == expected


@pytest.mark.parametrize("category", ["Stake", "STAKE", "staking", "node", "earn", ""])
def test_arbitrary_taxonomy_is_quarantined(category):
    record = _record("identity", "participation", "reward_mechanism")
    record.category = category
    assert evaluate_admission(record).outcome == "QUARANTINE"


@pytest.mark.parametrize("category", ["GAME", "DEPIN_NODE", "POINTS"])
def test_taxonomy_survives_storage_restart_and_api(tmp_path, category):
    engine = create_engine(f"sqlite:///{tmp_path / 'discovery.db'}")
    Base.metadata.create_all(engine)
    record = _record("identity", "participation", "reward_mechanism")
    record.category = category
    DiscoveryRepository(engine).upsert(record)
    engine.dispose()
    engine = create_engine(f"sqlite:///{tmp_path / 'discovery.db'}")
    page, _ = ApiDataService(engine).opportunities_page(limit=100, offset=0)
    assert next(x for x in page if x.name == record.canonical_name).opportunity_type == category
    engine.dispose()


def test_visual_retry_preserves_legacy_neural_audio_without_paid_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    package = _package()
    script = _script_for(package)
    directory = tmp_path / "render" / "narration"
    directory.mkdir(parents=True)
    audio = directory / (package.source_inventory_item_id + "-approved.mp3")
    audio.write_bytes(b"verified-fixture-audio")
    meta = NarrationAssetMetadata(content_id=package.source_inventory_item_id,
        script_fingerprint=sha256(script.encode()).hexdigest(), source_script=script, spoken_text=script,
        voice_id="EXAVITQu4vr4xnSDxMaL", model_id="eleven_multilingual_v2",
        generated_at=datetime.now(UTC).isoformat(), audio_path=str(audio), audio_checksum=sha256(audio.read_bytes()).hexdigest())
    audio.with_suffix(".json").write_text(meta.model_dump_json())
    def forbidden(*a, **kw):
        raise AssertionError("Paid provider must never be constructed")
    for _ in range(2):
        result = render_package(package, settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=forbidden, command_runner=_runner)
        assert result.status == "NOT_READY"  # product visuals deliberately missing
        assert sha256(audio.read_bytes()).hexdigest() == meta.audio_checksum
    assets = tmp_path / "assets" / package.opportunity_id
    assets.mkdir(parents=True)
    (assets / "official-product-ui.png").write_bytes(b"test-fixture" * 100)
    monkeypatch.setenv("GAMEFI_SHORT_ASSET_ROOT", str(tmp_path / "assets"))
    rebuilt = render_package(package, settings=_settings(tmp_path), root=tmp_path / "render", narration_provider_factory=forbidden, command_runner=_runner)
    assert rebuilt.status == "NOT_READY"
    assert "BLOCKED_TTS_NARRATION" in rebuilt.reason
    assert sha256(audio.read_bytes()).hexdigest() == meta.audio_checksum
    assert reuse_existing_narration(package.source_inventory_item_id, directory, script=script) is not None
    assert reuse_existing_narration(package.source_inventory_item_id, directory, script=script + " Changed claim.") is None


def test_missing_narration_does_not_generate_by_default(tmp_path):
    def forbidden(*a, **kw):
        raise AssertionError("Unexpected paid generation")
    result = render_package(_package(), settings=_settings(tmp_path), root=tmp_path, narration_provider_factory=forbidden)
    assert result.audio_mode == "music_only"
    assert "BLOCKED_VISUAL_QA" in result.reason


def test_worker_failure_is_bounded_across_restart(tmp_path):
    path = tmp_path / "state.json"
    now = datetime.now(UTC)
    for _ in range(3):
        state = WorkerState(path)
        state.record_failure("video", error_category="RenderError", now=now, cooldown_seconds=1)
    assert WorkerState(path).blocked("video", now=now + timedelta(days=10))


def test_configured_does_not_prove_youtube_capability(tmp_path):
    publisher = YouTubePublisher(config=YouTubePublisherConfig(tmp_path / "client.json", tmp_path / "missing.json", tmp_path / "state.json"))
    status = publisher.check_capabilities()
    assert status["configured"]
    assert not status["authenticated"]
    assert not status["channel_verified"]
    assert not status["upload_scope_verified"]
