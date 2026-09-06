from __future__ import annotations

from app.strategies.catalog import get_opportunity, get_outbound_destination, list_opportunities


BATCH_THREE = (
    "akash-provider",
    "golem-provider",
    "helium-iot-hotspot",
    "theta-edge-node",
    "render-node-operator",
    "filecoin-storage-provider",
    "nosana-gpu-host",
    "livepeer-orchestrator",
)


def test_batch_three_is_source_backed_guide_only() -> None:
    for opportunity_id in BATCH_THREE:
        opportunity = get_opportunity(opportunity_id)
        assert opportunity is not None
        assert opportunity.admission_mode == "GUIDE_ONLY"
        assert opportunity.strategy_ids == ()
        assert opportunity.official_source_references
        assert all(reference.source_role == "OFFICIAL_PROJECT" for reference in opportunity.official_source_references)
        assert opportunity.guidance is not None
        assert opportunity.roi_unavailable is not None
        destination = get_outbound_destination(opportunity.outbound_destination_slugs[0])
        assert destination is not None
        assert destination.official_url.startswith("https://")
        assert destination.referral_url is None


def test_batch_three_increases_guide_only_catalog_without_changing_strategy_count() -> None:
    opportunities = list_opportunities()
    assert all(get_opportunity(opportunity_id) is not None for opportunity_id in BATCH_THREE)
    assert len(opportunities) == 51
    assert len([item for item in opportunities if item.admission_mode == "MODELED"]) == 8
    assert len([item for item in opportunities if item.admission_mode == "GUIDE_ONLY"]) == 43
