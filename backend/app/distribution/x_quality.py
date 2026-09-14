"""X-specific usefulness and safety checks for GamCryp copy.

The general content-pack validator protects facts and financial language. X
needs one additional editorial gate: a post presented as a setup/how-to guide
must actually help a reader take the next safe step. This module deliberately
does not infer project mechanics; it only checks the structure of copy built
from catalog guidance and official references.
"""

from __future__ import annotations

import re

from app.distribution.content_pack import ContentPackLite

ACTIONABLE_ANGLE_RE = re.compile(r"(?i)\b(?:how[- ]to|setup|getting started|onboarding|registration)\b")
NUMBERED_STEP_RE = re.compile(r"(?m)^\s*(?:\d+[.)]|[•*-])\s+\S+")
ACTION_CUE_RE = re.compile(
    r"(?i)\b(?:start|open|install|register|connect|review|check|confirm|follow|need|requires?|before)\b"
)
REWARD_OR_EXIT_CUE_RE = re.compile(r"(?i)\b(?:earn|reward|claim|exit|payout|withdraw|redeem|roi)\b")


def is_actionable_angle(pack: ContentPackLite) -> bool:
    """Whether editorial metadata declares a how-to/setup style post."""

    return bool(ACTIONABLE_ANGLE_RE.search(pack.editorial.content_angle))


def actionable_x_copy_blockers(pack: ContentPackLite, final_copy: str) -> tuple[str, ...]:
    """Return fail-closed blockers for an actionable X post.

    The check is intentionally structural. It does not require a particular
    verb such as ``register`` because some opportunities use a node, device,
    or wallet flow instead of an account registration flow.
    """

    if not is_actionable_angle(pack):
        return ()

    blockers: list[str] = []
    if len(NUMBERED_STEP_RE.findall(final_copy)) < 2:
        blockers.append("how-to X copy must contain at least two actionable steps")
    if not ACTION_CUE_RE.search(final_copy):
        blockers.append("how-to X copy is missing a start/setup action cue")
    if not REWARD_OR_EXIT_CUE_RE.search(final_copy):
        blockers.append("how-to X copy is missing an earn, reward, claim, exit, or ROI status cue")
    if not pack.source.official_source_refs:
        blockers.append("how-to X copy requires at least one official source reference")
    return tuple(blockers)
