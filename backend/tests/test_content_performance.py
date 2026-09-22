from __future__ import annotations

from datetime import timedelta

import pytest

from app.monetization.models import ContentPerformancePlatform
from app.storage.monetization import MonetizationPersistenceError, MonetizationRepository
from test_api_v1 import NOW
from test_history_storage import _migrated_engine


def test_content_performance_is_source_backed_and_idempotent(monkeypatch, tmp_path) -> None:
    repository = MonetizationRepository(_migrated_engine(monkeypatch, tmp_path, "content-performance.db"))
    first = repository.save_content_performance(
        platform=ContentPerformancePlatform.X,
        content_id="x-example-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=1),
        impressions=100,
        engagements=12,
        link_clicks=4,
        evidence_reference="x-dashboard-export-2026-09-21.csv",
    )
    second = repository.save_content_performance(
        platform="X",
        content_id="x-example-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=1),
        impressions=125,
        engagements=15,
        link_clicks=5,
        evidence_url="https://analytics.x.com/example",
    )

    assert first.performance_id == second.performance_id
    records = repository.content_performance(platform="X", content_id="x-example-1")
    assert len(records) == 1
    assert records[0].impressions == 125
    assert records[0].link_clicks == 5
    assert records[0].platform is ContentPerformancePlatform.X


@pytest.mark.parametrize(
    "overrides",
    [
        {"impressions": -1, "evidence_reference": "dashboard.csv"},
        {"impressions": 1},
        {"impressions": 1, "average_retention_percent": "101", "evidence_reference": "dashboard.csv"},
        {"impressions": 1, "evidence_reference": "dashboard.csv", "period_end": NOW - timedelta(days=1)},
    ],
)
def test_content_performance_rejects_untrustworthy_records(monkeypatch, tmp_path, overrides) -> None:
    repository = MonetizationRepository(_migrated_engine(monkeypatch, tmp_path, "content-performance-invalid.db"))
    values = {
        "platform": "YOUTUBE",
        "content_id": "yt-example-1",
        "period_start": NOW,
        "period_end": NOW + timedelta(days=1),
        "views": 10,
    }
    values.update(overrides)
    with pytest.raises(MonetizationPersistenceError):
        repository.save_content_performance(**values)
