from __future__ import annotations

from app.strategies.catalog import get_opportunity, get_outbound_destination, list_opportunities, list_strategies


FINAL_BATCH = (
    "aethir-checker-node",
    "io-net-worker",
    "aleph-im-compute-resource-node",
    "acurast-compute-provider",
    "nym-mixnode",
    "subspace-farmer",
    "bittensor-miner",
    "fluxnode",
)


def test_final_catalog_batch_is_source_backed_and_has_no_models() -> None:
    for opportunity_id in FINAL_BATCH:
        opportunity = get_opportunity(opportunity_id)
        assert opportunity is not None
        assert opportunity.strategy_ids == ()
        assert opportunity.official_source_references
        assert all(reference.source_role == "OFFICIAL_PROJECT" for reference in opportunity.official_source_references)
        assert opportunity.guidance is not None
        assert opportunity.roi_unavailable is not None
        destination = get_outbound_destination(opportunity.outbound_destination_slugs[0])
        assert destination is not None
        assert destination.official_url.startswith("https://")
        assert destination.referral_url is None


def test_final_catalog_batch_crosses_fifty_without_changing_modeled_strategy_count() -> None:
    opportunities = list_opportunities()

    assert len(opportunities) == 51
    assert sum(item.admission_mode == "MODELED" for item in opportunities) == 8
    assert sum(item.admission_mode == "GUIDE_ONLY" for item in opportunities) == 43
    assert len(list_strategies()) == 15
    assert get_opportunity("fluxnode").status == "watchlist"
