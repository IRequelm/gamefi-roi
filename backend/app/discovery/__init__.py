"""Autonomous discovery, admission, and content-intelligence primitives."""

from app.discovery.engine import (
    AdmissionDecision,
    DiscoveryRecord,
    EvidenceRecord,
    Signal,
    evaluate_admission,
    normalize_entity,
    score_discovery,
)

__all__ = [
    "AdmissionDecision",
    "DiscoveryRecord",
    "EvidenceRecord",
    "Signal",
    "evaluate_admission",
    "normalize_entity",
    "score_discovery",
]
