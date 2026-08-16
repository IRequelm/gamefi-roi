"""Risk and confidence scoring result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

METHODOLOGY_VERSION = "risk-confidence-v1"


class ConfidenceLabel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class RiskLabel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY HIGH"


@dataclass(frozen=True)
class ScoreContribution:
    factor: str
    points: int
    reason: str
    evidence: MappingProxyType[str, Any]

    def __post_init__(self) -> None:
        if not self.factor:
            raise ValueError("ScoreContribution.factor is required")
        if self.points < 0:
            raise ValueError("ScoreContribution.points must be non-negative")
        if not self.reason:
            raise ValueError("ScoreContribution.reason is required")
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))


@dataclass(frozen=True)
class UnavailableFactor:
    factor: str
    reason: str

    def __post_init__(self) -> None:
        if not self.factor:
            raise ValueError("UnavailableFactor.factor is required")
        if not self.reason:
            raise ValueError("UnavailableFactor.reason is required")


@dataclass(frozen=True)
class ConfidenceScore:
    score: int
    label: ConfidenceLabel
    points_lost: int
    contributions: tuple[ScoreContribution, ...]
    unavailable_factors: tuple[UnavailableFactor, ...]


@dataclass(frozen=True)
class RiskScore:
    score: int
    label: RiskLabel
    points_added: int
    contributions: tuple[ScoreContribution, ...]
    unavailable_factors: tuple[UnavailableFactor, ...]


@dataclass(frozen=True)
class SnapshotScoreResult:
    snapshot_id: str
    strategy_id: str
    strategy_version: str
    methodology_version: str
    scored_at: datetime
    confidence: ConfidenceScore
    risk: RiskScore
