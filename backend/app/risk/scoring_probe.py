"""Local deterministic probe for G9 risk/confidence scoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.jobs.history_probe import build_history_probe_tasks
from app.jobs.recalculation import ScheduledRecalculator, hourly_window
from app.risk.scoring import SnapshotScorer
from app.storage.database import create_database_engine
from app.storage.history import HistoryRepository
from app.storage.scoring import ScoringRepository


def main() -> int:
    engine = create_database_engine()
    try:
        history_repository = HistoryRepository(engine)
        scoring_repository = ScoringRepository(engine)
        calculated_at = datetime.now(UTC)
        run = ScheduledRecalculator(history_repository).run_once(
            build_history_probe_tasks(),
            intended_window=hourly_window(calculated_at),
            calculated_at=calculated_at,
        )
        if run.failures:
            for failure in run.failures:
                print(f"[FAILURE] {failure.strategy_id}@{failure.strategy_version} {failure.error_type}: {failure.error_message}")
            return 1

        scorer = SnapshotScorer()
        scores = []
        for snapshot in run.snapshots:
            history = history_repository.ordered_time_series(
                snapshot.strategy_id,
                start=snapshot.calculated_at - timedelta(days=30),
                end=snapshot.calculated_at,
                strategy_version=snapshot.strategy_version,
                model_version=snapshot.model_version,
            )
            scores.append(scoring_repository.save_score(scorer.score(snapshot, history=history, scored_at=calculated_at)))
    finally:
        engine.dispose()

    print(f"scoring methodology={SnapshotScorer.methodology_version} scored={len(scores)}")
    for score in sorted(scores, key=lambda item: item.strategy_id):
        confidence_top = _top_factors(score.confidence.contributions)
        risk_top = _top_factors(score.risk.contributions)
        unavailable = sorted({factor.factor for factor in score.risk.unavailable_factors})
        print(
            f"[SCORE] {score.strategy_id}@{score.strategy_version} "
            f"confidence={score.confidence.score} {score.confidence.label.value} "
            f"risk={score.risk.score} {score.risk.label.value} "
            f"confidence_top={confidence_top} risk_top={risk_top} "
            f"unavailable={','.join(unavailable) if unavailable else 'none'}"
        )
    return 0


def _top_factors(contributions) -> str:
    ordered = sorted(contributions, key=lambda contribution: contribution.points, reverse=True)[:3]
    return ",".join(f"{contribution.factor}:{contribution.points}" for contribution in ordered) or "none"


if __name__ == "__main__":
    raise SystemExit(main())
