"""Persistent risk/confidence scoring models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.metadata import Base


class StrategySnapshotScoreRecord(Base):
    __tablename__ = "strategy_snapshot_scores"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "methodology_version",
            name="uq_strategy_snapshot_scores_snapshot_id",
        ),
    )

    score_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("strategy_snapshots.snapshot_id"),
        nullable=False,
        index=True,
    )
    strategy_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_contributions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "confidence_contributions",
        JSON,
        nullable=False,
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_label: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_contributions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "risk_contributions",
        JSON,
        nullable=False,
    )
    unavailable_factors_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "unavailable_factors",
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
