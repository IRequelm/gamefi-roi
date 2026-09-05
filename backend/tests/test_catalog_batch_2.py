from __future__ import annotations

from app.strategies.catalog import get_opportunity, get_outbound_destination


def test_batch_two_candidates_are_guide_only_and_source_backed() -> None:
    for opportunity_id in ("hivemapper", "honeygain", "earnapp"):
        opportunity = get_opportunity(opportunity_id)
        assert opportunity is not None
        assert opportunity.admission_mode == "GUIDE_ONLY"
        assert not opportunity.strategy_ids
        assert opportunity.official_source_references
        assert all(reference.source_role == "OFFICIAL_PROJECT" for reference in opportunity.official_source_references)
        assert opportunity.guidance is not None
        assert opportunity.roi_unavailable is not None
        destination = get_outbound_destination(opportunity.outbound_destination_slugs[0])
        assert destination is not None
        assert destination.official_url.startswith("https://")


def test_batch_two_does_not_create_financial_snapshots_or_commercial_priority() -> None:
    for opportunity_id in ("hivemapper", "honeygain", "earnapp"):
        opportunity = get_opportunity(opportunity_id)
        assert opportunity is not None
        assert opportunity.strategy_ids == ()
        destination = get_outbound_destination(opportunity.outbound_destination_slugs[0])
        assert destination is not None
        assert destination.referral_url is None
        assert destination.is_affiliate is False
