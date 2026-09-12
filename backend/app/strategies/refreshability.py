"""Canonical production refreshability policy for modeled strategies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Refreshability(StrEnum):
    AUTO_REFRESHABLE = "AUTO_REFRESHABLE"
    PARTIAL_REFRESH_ONLY = "PARTIAL_REFRESH_ONLY"
    NOT_REFRESHABLE = "NOT_REFRESHABLE"


@dataclass(frozen=True)
class RefreshabilityDecision:
    refreshability: Refreshability
    reason: str


_AUTO_STRATEGY_IDS = frozenset(
    {
        "dfk-crystalvale-jeweler-cjewel-max-lock",
        "dfk-crystalvale-jeweler-cjewel-100-max-lock",
        "dfk-crystalvale-jeweler-cjewel-5000-max-lock",
        "farmers-world-axe-wood-production",
        "farmers-world-axe-wood-production-3x",
        "farmers-world-axe-wood-production-10x",
        "splinterlands-modern-ranked-sps-ev",
        "splinterlands-modern-ranked-casual-sps-ev",
        "splinterlands-modern-ranked-active-sps-ev",
        "splinterlands-modern-ranked-grinder-sps-ev",
    }
)
_PARTIAL_STRATEGY_IDS = frozenset(
    {
        "geodnet-empty-hex-triple-band-base-station",
        "weatherxm-d1-wifi-station",
        "dimo-software-only-compatible-car",
        "mysterium-b2b-existing-device",
    }
)
_NOT_REFRESHABLE_STRATEGY_IDS = frozenset(
    {
        "storj-existing-hardware-storage-node",
    }
)


def classify_refreshability(strategy_id: str) -> RefreshabilityDecision:
    if strategy_id in _AUTO_STRATEGY_IDS:
        return RefreshabilityDecision(
            refreshability=Refreshability.AUTO_REFRESHABLE,
            reason=(
                "Required publication-fresh inputs have approved production provider loaders; "
                "configured strategy assumptions remain explicit model inputs."
            ),
        )
    if strategy_id in _PARTIAL_STRATEGY_IDS:
        return RefreshabilityDecision(
            refreshability=Refreshability.PARTIAL_REFRESH_ONLY,
            reason=(
                "A market sub-input can refresh, but required capital, reward, or operating economics "
                "remain CONFIG/static."
            ),
        )
    if strategy_id in _NOT_REFRESHABLE_STRATEGY_IDS:
        return RefreshabilityDecision(
            refreshability=Refreshability.NOT_REFRESHABLE,
            reason="No approved live source loader exists for the required Storj economics.",
        )
    return RefreshabilityDecision(
        refreshability=Refreshability.NOT_REFRESHABLE,
        reason="No approved production refreshability classification is registered for this strategy.",
    )


def registered_refreshability_counts() -> dict[Refreshability, int]:
    return {
        Refreshability.AUTO_REFRESHABLE: len(_AUTO_STRATEGY_IDS),
        Refreshability.PARTIAL_REFRESH_ONLY: len(_PARTIAL_STRATEGY_IDS),
        Refreshability.NOT_REFRESHABLE: len(_NOT_REFRESHABLE_STRATEGY_IDS),
    }
