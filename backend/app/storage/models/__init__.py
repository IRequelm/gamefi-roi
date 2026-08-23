"""Persistent storage models."""

from app.storage.models.monetization import (
    OutboundClickEventRecord,
    ReferralProgramRecord,
    RevenueAttributionRecord,
    SponsoredPlacementRecord,
)
from app.storage.models.observation import ObservationRecord
from app.storage.models.scoring import StrategySnapshotScoreRecord
from app.storage.models.strategy_history import StrategyCalculationFailureRecord, StrategySnapshotRecord

__all__ = [
    "ObservationRecord",
    "OutboundClickEventRecord",
    "ReferralProgramRecord",
    "RevenueAttributionRecord",
    "SponsoredPlacementRecord",
    "StrategyCalculationFailureRecord",
    "StrategySnapshotRecord",
    "StrategySnapshotScoreRecord",
]
