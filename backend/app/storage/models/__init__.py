"""Persistent storage models."""

from app.storage.models.monetization import (
    InboundLandingEventRecord,
    OutboundClickEventRecord,
    ReferralProgramRecord,
    ReferralTaskRecord,
    RevenueAttributionRecord,
    SponsoredPlacementRecord,
)
from app.storage.models.observation import ObservationRecord
from app.storage.models.scoring import StrategySnapshotScoreRecord
from app.storage.models.strategy_history import StrategyCalculationFailureRecord, StrategySnapshotRecord
from app.storage.models.discovery import DiscoveryRecordModel, DynamicCatalogEntryModel

__all__ = [
    "ObservationRecord",
    "InboundLandingEventRecord",
    "OutboundClickEventRecord",
    "ReferralProgramRecord",
    "ReferralTaskRecord",
    "RevenueAttributionRecord",
    "SponsoredPlacementRecord",
    "StrategyCalculationFailureRecord",
    "StrategySnapshotRecord",
    "StrategySnapshotScoreRecord",
    "DiscoveryRecordModel",
    "DynamicCatalogEntryModel",
]
