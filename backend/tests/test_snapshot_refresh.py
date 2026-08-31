from __future__ import annotations

from pathlib import Path

from app.config.settings import Settings
from app.jobs import snapshot_refresh
from app.jobs.snapshot_refresh import Refreshability, run_snapshot_refresh
from app.adapters.scenario_yield_probe import CONFIG_EVIDENCE_ESTABLISHED_AT, load_fixture_observations
from app.strategies.scenario_yield import DIMO_SOFTWARE_ONLY_V1


def test_dry_run_classifies_existing_production_tasks_without_provider_calls(monkeypatch) -> None:
    settings = _test_settings()
    tasks = tuple(snapshot_refresh.build_production_tasks(settings))
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: (_ for _ in ()).throw(AssertionError()))

    result = run_snapshot_refresh(settings=settings, dry_run=True)

    assert result.mode == "dry-run"
    assert result.refreshed_count == 0
    assert result.failed_count == 0
    assert result.skipped_count == 5
    assert result.partial_skipped == 4
    assert result.not_refreshable_skipped == 1
    assert len(result.refreshability) == len(tasks)
    assert sum(entry.refreshability == Refreshability.AUTO_REFRESHABLE for entry in result.refreshability) == 10
    assert sum(entry.refreshability == Refreshability.PARTIAL_REFRESH_ONLY for entry in result.refreshability) == 4
    assert sum(entry.refreshability == Refreshability.NOT_REFRESHABLE for entry in result.refreshability) == 1


def test_config_observations_keep_stable_source_identity_across_recalculation_times() -> None:
    first = load_fixture_observations(
        CONFIG_EVIDENCE_ESTABLISHED_AT,
        strategy=DIMO_SOFTWARE_ONLY_V1,
    )
    later = load_fixture_observations(
        CONFIG_EVIDENCE_ESTABLISHED_AT.replace(day=31),
        strategy=DIMO_SOFTWARE_ONLY_V1,
    )

    first_config = {observation.metric: observation for observation in first if observation.metadata.get("classification") == "CONFIG"}
    later_config = {observation.metric: observation for observation in later if observation.metadata.get("classification") == "CONFIG"}
    assert first_config.keys() == later_config.keys()
    for metric in first_config:
        assert later_config[metric].observation_id == first_config[metric].observation_id
        assert later_config[metric].observed_at == CONFIG_EVIDENCE_ESTABLISHED_AT
        assert later_config[metric].fresh_until == first_config[metric].fresh_until


def test_partial_and_not_refreshable_strategies_are_never_eligible_for_refresh(monkeypatch) -> None:
    settings = _test_settings()
    tasks = tuple(snapshot_refresh.build_production_tasks(settings))
    plan = snapshot_refresh.build_refresh_plan(tasks)
    by_id = {entry.strategy_id: entry for entry in plan}
    assert by_id["geodnet-empty-hex-triple-band-base-station"].refreshability is Refreshability.PARTIAL_REFRESH_ONLY
    assert by_id["storj-existing-hardware-storage-node"].refreshability is Refreshability.NOT_REFRESHABLE


def test_refresh_does_not_regenerate_distribution_after_strategy_failure(monkeypatch, tmp_path: Path) -> None:
    class FailedSummary:
        status = "ok"
        snapshot_ids = ("snapshot-1",)
        failure_ids = ("failure-1",)

    monkeypatch.setattr(snapshot_refresh, "_database_engine", lambda settings: _DisposableEngine())
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: FailedSummary())
    monkeypatch.setattr(snapshot_refresh, "_fetch_json", lambda url: (_ for _ in ()).throw(AssertionError()))

    result = run_snapshot_refresh(settings=_test_settings(), regenerate_distribution=True, distribution_output=tmp_path / "batch.json")

    assert result.refreshed_count == 1
    assert result.failed_count == 1
    assert result.distribution_regenerated is False
    assert not (tmp_path / "batch.json").exists()


def test_refresh_regenerates_distribution_only_after_zero_failure_refresh(monkeypatch, tmp_path: Path) -> None:
    class SuccessfulSummary:
        status = "ok"
        snapshot_ids = ("snapshot-1",)
        failure_ids = ()

    monkeypatch.setattr(snapshot_refresh, "_database_engine", lambda settings: _DisposableEngine())
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: SuccessfulSummary())
    monkeypatch.setattr(snapshot_refresh, "_fetch_json", lambda url: {"items": [], "page": {"total": 0}})
    monkeypatch.setattr(snapshot_refresh, "build_learning_batch", lambda *args, **kwargs: [])

    result = run_snapshot_refresh(settings=_test_settings(), regenerate_distribution=True, distribution_output=tmp_path / "batch.json")

    assert result.distribution_regenerated is True
    assert (tmp_path / "batch.json").exists()


class _DisposableEngine:
    def dispose(self) -> None:
        pass


def _test_settings() -> Settings:
    return Settings(database_url="sqlite+pysqlite:///:memory:", environment="test", allow_sqlite_for_tests=True)
