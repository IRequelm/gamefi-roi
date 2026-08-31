from __future__ import annotations

from pathlib import Path

from app.config.settings import Settings
from app.jobs import snapshot_refresh
from app.jobs.snapshot_refresh import Refreshability, run_snapshot_refresh


def test_dry_run_classifies_existing_production_tasks_without_provider_calls(monkeypatch) -> None:
    settings = _test_settings()
    tasks = tuple(snapshot_refresh.build_production_tasks(settings))
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: (_ for _ in ()).throw(AssertionError()))

    result = run_snapshot_refresh(settings=settings, dry_run=True)

    assert result.mode == "dry-run"
    assert result.refreshed_count == 0
    assert result.failed_count == 0
    assert result.skipped_count == 0
    assert len(result.refreshability) == len(tasks)
    assert all(entry.refreshability == Refreshability.AUTO_REFRESHABLE for entry in result.refreshability)


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
