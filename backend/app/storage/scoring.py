"""Repository helpers for versioned risk/confidence snapshot scores."""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Engine, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.risk.results import (
    METHODOLOGY_VERSION,
    ConfidenceLabel,
    ConfidenceScore,
    RiskLabel,
    RiskScore,
    ScoreContribution,
    SnapshotScoreResult,
    UnavailableFactor,
)
from app.storage.models import StrategySnapshotScoreRecord


class ScoringPersistenceError(ValueError):
    """Raised when a scoring result cannot be safely persisted."""


class ScoringRepository:
    def __init__(self, bind: Engine | Connection) -> None:
        self.engine = bind

    def save_score(self, score: SnapshotScoreResult) -> SnapshotScoreResult:
        _validate_score(score)
        score_id = _score_id(score.snapshot_id, score.methodology_version)
        now = datetime.now(UTC)
        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(StrategySnapshotScoreRecord).where(
                    StrategySnapshotScoreRecord.snapshot_id == score.snapshot_id,
                    StrategySnapshotScoreRecord.methodology_version == score.methodology_version,
                )
            )
            if existing is not None:
                return _score_from_record(existing)

            record = StrategySnapshotScoreRecord(
                score_id=score_id,
                snapshot_id=score.snapshot_id,
                strategy_id=score.strategy_id,
                strategy_version=score.strategy_version,
                methodology_version=score.methodology_version,
                scored_at=score.scored_at,
                confidence_score=score.confidence.score,
                confidence_label=score.confidence.label.value,
                confidence_contributions_json=_contributions(score.confidence.contributions),
                risk_score=score.risk.score,
                risk_label=score.risk.label.value,
                risk_contributions_json=_contributions(score.risk.contributions),
                unavailable_factors_json=_unavailable(score),
                created_at=now,
            )
            session.add(record)
            session.commit()
            return _score_from_record(record)

    def get_score(
        self,
        snapshot_id: str,
        *,
        methodology_version: str = METHODOLOGY_VERSION,
    ) -> SnapshotScoreResult | None:
        with Session(self.engine) as session:
            record = session.scalar(
                select(StrategySnapshotScoreRecord).where(
                    StrategySnapshotScoreRecord.snapshot_id == snapshot_id,
                    StrategySnapshotScoreRecord.methodology_version == methodology_version,
                )
            )
            return None if record is None else _score_from_record(record)

    def get_scores_for_snapshots(
        self,
        snapshot_ids: tuple[str, ...],
        *,
        methodology_version: str = METHODOLOGY_VERSION,
    ) -> dict[str, SnapshotScoreResult]:
        if not snapshot_ids:
            return {}
        with Session(self.engine) as session:
            records = session.scalars(
                select(StrategySnapshotScoreRecord).where(
                    StrategySnapshotScoreRecord.snapshot_id.in_(snapshot_ids),
                    StrategySnapshotScoreRecord.methodology_version == methodology_version,
                )
            ).all()
        return {record.snapshot_id: _score_from_record(record) for record in records}


def _validate_score(score: SnapshotScoreResult) -> None:
    if not score.snapshot_id:
        raise ScoringPersistenceError("snapshot_id is required")
    if not score.methodology_version:
        raise ScoringPersistenceError("methodology_version is required")
    for field_name, value in (
        ("confidence.score", score.confidence.score),
        ("risk.score", score.risk.score),
    ):
        if value < 0 or value > 100:
            raise ScoringPersistenceError(f"{field_name} must be between 0 and 100")


def _score_from_record(record: StrategySnapshotScoreRecord) -> SnapshotScoreResult:
    confidence_contributions = tuple(
        _contribution_from_payload(payload) for payload in record.confidence_contributions_json
    )
    risk_contributions = tuple(_contribution_from_payload(payload) for payload in record.risk_contributions_json)
    confidence_unavailable = tuple(
        UnavailableFactor(factor=payload["factor"], reason=payload["reason"])
        for payload in record.unavailable_factors_json
        if payload.get("score_type") == "confidence"
    )
    risk_unavailable = tuple(
        UnavailableFactor(factor=payload["factor"], reason=payload["reason"])
        for payload in record.unavailable_factors_json
        if payload.get("score_type") == "risk"
    )
    return SnapshotScoreResult(
        snapshot_id=record.snapshot_id,
        strategy_id=record.strategy_id,
        strategy_version=record.strategy_version,
        methodology_version=record.methodology_version,
        scored_at=_as_utc(record.scored_at),
        confidence=ConfidenceScore(
            score=record.confidence_score,
            label=ConfidenceLabel(record.confidence_label),
            points_lost=sum(contribution.points for contribution in confidence_contributions),
            contributions=confidence_contributions,
            unavailable_factors=confidence_unavailable,
        ),
        risk=RiskScore(
            score=record.risk_score,
            label=RiskLabel(record.risk_label),
            points_added=sum(contribution.points for contribution in risk_contributions),
            contributions=risk_contributions,
            unavailable_factors=risk_unavailable,
        ),
    )


def _contribution_from_payload(payload: dict) -> ScoreContribution:
    return ScoreContribution(
        factor=payload["factor"],
        points=int(payload["points"]),
        reason=payload["reason"],
        evidence=MappingProxyType(dict(payload.get("evidence", {}))),
    )


def _contributions(contributions: tuple[ScoreContribution, ...]) -> list[dict]:
    return [
        {
            "factor": contribution.factor,
            "points": contribution.points,
            "reason": contribution.reason,
            "evidence": dict(contribution.evidence),
        }
        for contribution in contributions
    ]


def _unavailable(score: SnapshotScoreResult) -> list[dict]:
    return [
        {"score_type": "confidence", "factor": factor.factor, "reason": factor.reason}
        for factor in score.confidence.unavailable_factors
    ] + [
        {"score_type": "risk", "factor": factor.factor, "reason": factor.reason}
        for factor in score.risk.unavailable_factors
    ]


def _score_id(snapshot_id: str, methodology_version: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gamefi-roi-score|{snapshot_id}|{methodology_version}"))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
