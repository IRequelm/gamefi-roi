from __future__ import annotations

from app.distribution.learning_batch import build_learning_batch
from app.distribution.x_quality import actionable_x_copy_blockers
from app.distribution.x_queue import x_weighted_character_count


def _guide_opportunity() -> dict[str, object]:
    return {
        "opportunity_id": "example-game",
        "opportunity_type": "GAME",
        "name": "Example Game",
        "status": "candidate",
        "platforms": ["web"],
        "chains": ["testnet"],
        "economy_types": ["quest-rewards"],
        "reward_asset_or_points_type": ["points"],
        "value_realization_status": "unknown",
        "data_feasibility_status": "PARTIAL",
        "feasibility_summary": "Current reward value is not reproducibly modeled.",
        "guidance": {
            "how_to_start": ["Open the official game guide and review the current start steps."],
            "what_you_need": ["A supported account and the listed platform requirements are needed."],
            "how_you_earn": ["Complete documented quests for points."],
            "how_to_exit_or_claim": ["Review the official claim instructions before acting."],
        },
        "primary_destination": {
            "source_reference": {"label": "Official game guide", "url": "https://example.com/game"}
        },
    }


def test_generated_guide_copy_is_actionable_and_x_safe() -> None:
    packs = build_learning_batch(
        {"items": []},
        {"items": [_guide_opportunity()]},
        include_x_guides=True,
    )
    pack = next(item for item in packs if item.source.opportunity_id == "example-game")

    assert pack.editorial.content_angle == "how-to start guide"
    assert pack.editorial.x_post.startswith("Example Game: how to start")
    assert "1) Start:" in pack.editorial.x_post
    assert "2) Need:" in pack.editorial.x_post
    assert "3) Earn/claim:" in pack.editorial.x_post
    assert x_weighted_character_count(pack.editorial.x_post) <= 280
    assert actionable_x_copy_blockers(pack, pack.editorial.x_post) == ()


def test_actionable_x_qa_blocks_a_how_to_post_without_real_steps() -> None:
    pack = next(
        item
        for item in build_learning_batch({"items": []}, {"items": [_guide_opportunity()]}, include_x_guides=True)
        if item.source.opportunity_id == "example-game"
    )
    blockers = actionable_x_copy_blockers(
        pack,
        "Example Game can earn points. Check GamCryp for details.",
    )

    assert "how-to X copy must contain at least two actionable steps" in blockers


def test_x_guide_selector_rejects_noncanonical_generated_types() -> None:
    invalid = _guide_opportunity() | {"opportunity_id": "invalid-stake", "opportunity_type": "Stake"}
    packs = build_learning_batch(
        {"items": []},
        {"items": [invalid]},
        include_x_guides=True,
    )

    assert not any(item.source.opportunity_id == "invalid-stake" for item in packs)
