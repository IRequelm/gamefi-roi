"""Operator-facing wrapper for the existing snapshot recalculation pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from app.config.settings import Settings, get_settings
from app.distribution.learning_batch import LEARNING_BATCH_CREATED_AT, LEARNING_BATCH_ID, build_learning_batch
from app.distribution.content_pack import write_batch
from app.jobs.production_recalculation import (
    ProductionRecalculationSummary,
    build_production_tasks,
    run_recalculation_tasks,
)
from app.jobs.recalculation import StrategyCalculationTask
from app.strategies.refreshability import Refreshability, classify_refreshability


@dataclass(frozen=True)
class RefreshPlanEntry:
    strategy_id: str
    strategy_version: str
    refreshability: Refreshability
    reason: str


@dataclass(frozen=True)
class RefreshCommandResult:
    mode: str
    refreshability: tuple[RefreshPlanEntry, ...]
    refreshed_count: int
    skipped_count: int
    failed_count: int
    auto_refreshed: int = 0
    partial_skipped: int = 0
    not_refreshable_skipped: int = 0
    failed: int = 0
    snapshot_summary: ProductionRecalculationSummary | None = None
    distribution_regenerated: bool = False
    status: str = "planned"
    eligible_count: int = 0
    reused_count: int = 0


def build_refresh_plan(
    tasks: tuple[StrategyCalculationTask, ...],
    *,
    dfk_jeweler_refresh_enabled: bool = True,
) -> tuple[RefreshPlanEntry, ...]:
    """Classify current production tasks without calling providers.

    This is intentionally an explicit strategy registry. Adapter module identity
    alone cannot prove that every required economic input has a live refresh path.
    """

    plan = []
    for task in tasks:
        decision = classify_refreshability(
            task.strategy_id,
            dfk_jeweler_refresh_enabled=dfk_jeweler_refresh_enabled,
        )
        plan.append(
            RefreshPlanEntry(
                strategy_id=task.strategy_id,
                strategy_version=task.strategy_version,
                refreshability=decision.refreshability,
                reason=decision.reason,
            )
        )
    return tuple(plan)


def run_snapshot_refresh(
    *,
    settings: Settings | None = None,
    calculated_at=None,
    dry_run: bool = False,
    regenerate_distribution: bool = False,
    distribution_output: Path = Path("distribution/content_packs/learning_batch_001.json"),
    rankings_url: str = "https://gamcryp.com/api/v1/rankings?limit=100",
    opportunities_url: str = "https://gamcryp.com/api/v1/opportunities?limit=100",
    base_url: str = "https://gamcryp.com",
) -> RefreshCommandResult:
    active_settings = settings or get_settings()
    tasks = build_production_tasks(active_settings)
    plan = build_refresh_plan(tasks, dfk_jeweler_refresh_enabled=active_settings.dfk_jeweler_refresh_enabled)
    eligible_tasks = tuple(
        task
        for task, entry in zip(tasks, plan, strict=True)
        if entry.refreshability == Refreshability.AUTO_REFRESHABLE
    )
    partial_skipped = sum(entry.refreshability == Refreshability.PARTIAL_REFRESH_ONLY for entry in plan)
    not_refreshable_skipped = sum(entry.refreshability == Refreshability.NOT_REFRESHABLE for entry in plan)
    skipped_count = partial_skipped + not_refreshable_skipped
    if dry_run:
        return RefreshCommandResult(
            mode="dry-run",
            refreshability=plan,
            refreshed_count=0,
            skipped_count=skipped_count,
            failed_count=0,
            auto_refreshed=0,
            partial_skipped=partial_skipped,
            not_refreshable_skipped=not_refreshable_skipped,
            failed=0,
            status="dry_run",
            eligible_count=len(eligible_tasks),
        )

    engine = _database_engine(active_settings)
    try:
        summary = run_recalculation_tasks(
            engine=engine,
            tasks=eligible_tasks,
            calculated_at=calculated_at,
            cadence_minutes=active_settings.scheduler_cadence_minutes,
        )
    finally:
        engine.dispose()
    distribution_regenerated = False
    if regenerate_distribution and summary.status == "ok" and not summary.failure_ids:
        rankings_payload = _fetch_json(rankings_url)
        opportunities_payload = _fetch_json(opportunities_url)
        packs = build_learning_batch(rankings_payload, opportunities_payload, base_url=base_url)
        write_batch(
            distribution_output,
            packs,
            batch_id=LEARNING_BATCH_ID,
            generated_at=LEARNING_BATCH_CREATED_AT,
            source_dataset=f"{rankings_url} + {opportunities_url}",
        )
        distribution_regenerated = True
    new_snapshot_count = getattr(summary, "new_snapshot_count", len(summary.snapshot_ids))
    reused_snapshot_count = getattr(summary, "reused_snapshot_count", len(summary.snapshot_ids) - new_snapshot_count)
    return RefreshCommandResult(
        mode="refresh",
        refreshability=plan,
        refreshed_count=new_snapshot_count,
        skipped_count=skipped_count,
        failed_count=len(summary.failure_ids),
        auto_refreshed=new_snapshot_count,
        partial_skipped=partial_skipped,
        not_refreshable_skipped=not_refreshable_skipped,
        failed=len(summary.failure_ids),
        snapshot_summary=summary,
        distribution_regenerated=distribution_regenerated,
        status="failure" if summary.failure_ids else "skipped_lock_busy" if summary.status == "skipped_lock_busy" else "degraded" if skipped_count else "success",
        eligible_count=len(eligible_tasks),
        reused_count=reused_snapshot_count,
    )


def _database_engine(settings: Settings):
    from app.storage.database import create_database_engine

    return create_database_engine(settings)


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _json_default(value: Any):
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh eligible GamCryp strategy snapshots safely.")
    parser.add_argument("--dry-run", action="store_true", help="Report eligible strategies without provider/database calls.")
    parser.add_argument(
        "--regenerate-distribution",
        action="store_true",
        help="Regenerate the file-based distribution batch only after a zero-failure refresh.",
    )
    parser.add_argument("--distribution-output", type=Path, default=Path("distribution/content_packs/learning_batch_001.json"))
    args = parser.parse_args()
    result = run_snapshot_refresh(
        dry_run=args.dry_run,
        regenerate_distribution=args.regenerate_distribution,
        distribution_output=args.distribution_output,
    )
    print(json.dumps(asdict(result), default=_json_default, indent=2, sort_keys=True))
    lock_busy = result.snapshot_summary is not None and result.snapshot_summary.status == "skipped_lock_busy"
    if result.failed_count:
        return 1
    return 0 if result.mode == "dry-run" or result.refreshed_count or result.skipped_count or result.reused_count or lock_busy else 1


if __name__ == "__main__":
    raise SystemExit(main())
