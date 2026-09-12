"""Canonical opportunity taxonomy shared by admission and catalog boundaries."""
from enum import StrEnum


class OpportunityType(StrEnum):
    GAME = "GAME"
    DEPIN_NODE = "DEPIN_NODE"
    POINTS = "POINTS"


def canonical_type(value: str) -> str:
    return OpportunityType(value).value
