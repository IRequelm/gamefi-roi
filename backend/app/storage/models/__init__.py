"""Persistent storage models."""

from app.storage.models.monetization import (
    InboundLandingEventRecord,
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
    "InboundLandingEventRecord",
    "OutboundClickEventRecord",
    "ReferralProgramRecord",
    "RevenueAttributionRecord",
    "SponsoredPlacementRecord",
    "StrategyCalculationFailureRecord",
    "StrategySnapshotRecord",
    "StrategySnapshotScoreRecord",
]
