from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.distribution.content_pack import (
    CONTENT_PACK_VERSION,
    ContentClaim,
    ContentPackLite,
    ContentPackValidationError,
    ContentReadiness,
    build_utm_url,
    expected_source_hash,
    resolve_claim_source_value,
    serialize_batch,
    source_snapshot_hash,
    validate_batch,
    validate_pack,
)
from app.distribution.learning_batch import LEARNING_BATCH_CREATED_AT, build_learning_batch


def test_source_snapshot_hash_is_deterministic() -> None:
    left = {"b": [2, 1], "a": {"value": "0.4885000000"}}
    right = {"a": {"value": "0.4885000000"}, "b": [2, 1]}

    assert source_snapshot_hash(left) == source_snapshot_hash(right)


def test_learning_batch_links_each_strategy_pack_to_snapshot_source() -> None:
    packs = build_learning_batch(_rankings_payload(), _opportunities_payload())
    strategy_packs = [pack for pack in packs if pack.source.strategy_id]

    assert len(packs) == 10
    assert strategy_packs
    assert all(pack.source.snapshot_id for pack in strategy_packs)
    assert all(pack.source.snapshot_timestamp for pack in strategy_packs)
    assert all(pack.source.source_snapshot_hash == expected_source_hash(pack) for pack in packs)


def test_unsupported_numeric_claim_rejects_pack() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]
    edited = pack.model_copy(
        update={
            "editorial": pack.editorial.model_copy(
                update={
                    "x_post": f"{pack.editorial.x_post}\nUnsupported extra claim: $999/day.",
                    "readiness": ContentReadiness.RED,
                }
            )
        }
    )
    edited = edited.model_copy(update={"source": edited.source.model_copy(update={"source_snapshot_hash": expected_source_hash(edited)})})

    result = validate_pack(edited)

    assert result.readiness == ContentReadiness.RED
    assert "$999/day" in result.unsupported_numeric_claims
    assert "editorial text contains unsupported numeric claim(s)" in result.errors


def test_claim_source_path_resolves_and_value_matches() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]
    claim = pack.claims[0]

    assert resolve_claim_source_value(pack, claim.source_path) == claim.source_value
    assert not validate_pack(pack).errors


def test_missing_claim_source_path_fails_closed() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]
    claim = pack.claims[0].model_copy(update={"source_path": "snapshot.missing.amount"})
    edited = _replace_claim(pack, claim)

    result = validate_pack(edited)

    assert result.readiness == ContentReadiness.RED
    assert any("source_path does not resolve" in error for error in result.errors)


def test_wrong_claim_source_value_fails_closed() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]
    claim = pack.claims[0].model_copy(update={"source_value": "999"})
    edited = _replace_claim(pack, claim)

    result = validate_pack(edited)

    assert result.readiness == ContentReadiness.RED
    assert any("source_value does not match" in error for error in result.errors)


def test_fabricated_registered_numeric_claim_fails_closed() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]
    fabricated = ContentClaim(
        claim_id="fabricated",
        text="Fabricated earnings are $999/day.",
        source_path="snapshot.earnings.net_earnings_day.amount",
        source_value=resolve_claim_source_value(pack, "snapshot.earnings.net_earnings_day.amount"),
        display_value="$999/day",
    )
    edited = pack.model_copy(
        update={
            "claims": [*pack.claims, fabricated],
            "editorial": pack.editorial.model_copy(
                update={
                    "x_post": f"{pack.editorial.x_post}\nFabricated earnings: $999/day.",
                    "readiness": ContentReadiness.RED,
                }
            ),
        }
    )
    edited = edited.model_copy(
        update={"source": edited.source.model_copy(update={"source_snapshot_hash": expected_source_hash(edited)})}
    )

    result = validate_pack(edited)

    assert result.readiness == ContentReadiness.RED
    assert any("display_value does not represent" in error for error in result.errors)


def test_valid_non_numeric_source_claim_passes() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]
    freshness_claim = ContentClaim(
        claim_id="freshness",
        text="Source status is fresh.",
        source_path="snapshot.freshness.overall_status",
        source_value="fresh",
        display_value="fresh",
    )
    edited = pack.model_copy(update={"claims": [*pack.claims, freshness_claim]})
    edited = edited.model_copy(
        update={"source": edited.source.model_copy(update={"source_snapshot_hash": expected_source_hash(edited)})}
    )

    assert resolve_claim_source_value(edited, freshness_claim.source_path) == "fresh"
    assert not validate_pack(edited).errors


def test_green_yellow_red_readiness_validation() -> None:
    fresh_low_risk = _pack_with(freshness="fresh", risk_label="LOW", confidence_label="HIGH")
    fresh_high_risk = _pack_with(freshness="fresh", risk_label="VERY HIGH", confidence_label="HIGH")
    stale_modeled = _pack_with(freshness="stale", risk_label="LOW", confidence_label="HIGH")
    roi_unavailable = next(pack for pack in build_learning_batch(_rankings_payload(), _opportunities_payload()) if pack.source.opportunity_id == "grass")

    assert validate_pack(fresh_low_risk).readiness == ContentReadiness.GREEN
    assert validate_pack(fresh_high_risk).readiness == ContentReadiness.YELLOW
    assert validate_pack(stale_modeled).readiness == ContentReadiness.RED
    assert validate_pack(roi_unavailable).readiness == ContentReadiness.YELLOW


def test_duplicate_content_id_prevention() -> None:
    pack = build_learning_batch(_rankings_payload(), _opportunities_payload())[0]

    with pytest.raises(ContentPackValidationError, match="Duplicate content_id"):
        validate_batch([pack, pack])


def test_utm_generation_uses_standard_distribution_parameters() -> None:
    url = build_utm_url(
        "https://gamcryp.com/strategies/example",
        source="x",
        medium="social",
        content_id="content-001",
    )

    assert url == (
        "https://gamcryp.com/strategies/example?"
        "utm_campaign=distribution-mvp&utm_content=content-001&utm_medium=social&utm_source=x"
    )


def test_serialization_is_deterministic_and_versioned() -> None:
    packs = build_learning_batch(_rankings_payload(), _opportunities_payload())

    first = json.dumps(
        serialize_batch(
            packs,
            batch_id="test-batch",
            generated_at=LEARNING_BATCH_CREATED_AT,
            source_dataset="test",
        ),
        sort_keys=True,
    )
    second = json.dumps(
        serialize_batch(
            list(reversed(packs)),
            batch_id="test-batch",
            generated_at=LEARNING_BATCH_CREATED_AT,
            source_dataset="test",
        ),
        sort_keys=True,
    )

    assert CONTENT_PACK_VERSION in first
    assert first == second


def test_committed_learning_batch_artifact_is_valid() -> None:
    payload = json.loads(Path("distribution/content_packs/learning_batch_001.json").read_text(encoding="utf-8"))
    packs = [ContentPackLite.model_validate(item) for item in payload["packs"]]

    validate_batch(packs)

    assert len(packs) == 10
    assert sum(payload["readiness_counts"].values()) == 10
    assert len([pack for pack in packs if pack.editorial.x_post]) == 10
    assert len([pack for pack in packs if pack.editorial.youtube_short_script]) == 3
    assert all(pack.distribution.x_utm_url.endswith(f"utm_source=x") for pack in packs)


def test_publishable_drafts_interpolate_attribution_urls() -> None:
    packs = build_learning_batch(_rankings_payload(), _opportunities_payload())
    methodology = next(pack for pack in packs if pack.source.opportunity_id == "gamcryp-methodology")
    grass = next(pack for pack in packs if pack.source.opportunity_id == "grass")

    for pack in (methodology, grass):
        assert pack.distribution.x_utm_url in pack.editorial.x_post
        assert "{url}" not in pack.editorial.x_post
        assert "utm_source=x" in pack.editorial.x_post
        assert "utm_medium=social" in pack.editorial.x_post
        assert "utm_campaign=distribution-mvp" in pack.editorial.x_post
        assert f"utm_content={pack.content_id}" in pack.editorial.x_post

    assert all(
        "{url}" not in pack.editorial.x_post
        for pack in packs
        if pack.editorial.readiness != ContentReadiness.RED
    )


def test_methodology_pack_is_not_coupled_to_strategy_snapshot() -> None:
    pack = next(
        pack
        for pack in build_learning_batch(_rankings_payload(), _opportunities_payload())
        if pack.source.opportunity_id == "gamcryp-methodology"
    )

    assert pack.source.strategy_id is None
    assert pack.source.snapshot_id is None
    assert pack.source.snapshot_timestamp is None
    assert pack.facts.freshness.display == "not applicable"


def test_distribution_code_does_not_import_financial_business_logic() -> None:
    distribution_files = Path("backend/app/distribution").glob("*.py")
    source = "\n".join(path.read_text(encoding="utf-8") for path in distribution_files)

    assert "app.engine" not in source
    assert "app.adapters" not in source
    assert "app.risk.scoring" not in source
    assert "calculate_strategy_roi" not in source


def _pack_with(*, freshness: str, risk_label: str, confidence_label: str):
    payload = _rankings_payload()
    item = payload["items"][0]
    item["latest_snapshot"]["freshness"]["overall_status"] = freshness
    item["latest_snapshot"]["risk"]["label"] = risk_label
    item["latest_snapshot"]["risk"]["score"] = 20 if risk_label == "LOW" else 90
    item["latest_snapshot"]["confidence"]["label"] = confidence_label
    item["latest_snapshot"]["confidence"]["score"] = 90 if confidence_label == "HIGH" else 40
    pack = build_learning_batch(payload, _opportunities_payload())[0]
    expected = ContentReadiness.GREEN
    if freshness == "stale":
        expected = ContentReadiness.RED
    elif risk_label in {"HIGH", "VERY HIGH"} or confidence_label in {"LOW", "MODERATE"}:
        expected = ContentReadiness.YELLOW
    return pack.model_copy(update={"editorial": pack.editorial.model_copy(update={"readiness": expected})})


def _replace_claim(pack: ContentPackLite, claim: ContentClaim) -> ContentPackLite:
    edited = pack.model_copy(update={"claims": [claim, *pack.claims[1:]]})
    return edited.model_copy(
        update={"source": edited.source.model_copy(update={"source_snapshot_hash": expected_source_hash(edited)})}
    )


def _rankings_payload() -> dict[str, object]:
    strategies = [
        ("geodnet-empty-hex-triple-band-base-station", "geodnet", "GEODNET", "DEPIN_NODE", "geospatial-node", "695", "2.5863626413797332680", "0.1116415528653122273956834532", "269.096", "VERY HIGH", 100, "MODERATE", 52),
        ("dfk-crystalvale-jeweler-cjewel-5000-max-lock", "defi-kingdoms", "DeFi Kingdoms", "GAME", "locked-yield-reward", "40.64045550630489442100105938", "0.01361299918132749601471545559", "0.01004885330029009938953579240", "2985.0", "VERY HIGH", 93, "HIGH", 82),
        ("farmers-world-axe-wood-production", "farmers-world", "Farmers World", "GAME", "resource-production", "0.0018906664685463456", "-5.782212375793702466790210095E-7", "-0.009174879554889557773141170400", None, "MODERATE", 55, "MODERATE", 77),
        ("weatherxm-d1-wifi-station", "weatherxm", "WeatherXM", "DEPIN_NODE", "weather-station", "139", "-0.00026514037839080274", "-0.00005722454209873440431654676259", None, "VERY HIGH", 100, "MODERATE", 59),
        ("splinterlands-modern-ranked-sps-ev", "splinterlands", "Splinterlands", "GAME", "probabilistic-performance", "10", "-0.0006575461707646110610000", "-0.0019726385122938331830000", None, "VERY HIGH", 100, "LOW", 39),
        ("storj-existing-hardware-storage-node", "storj-storage-node", "Storj Storage Node", "DEPIN_NODE", "storage-node", "1.00", "-0.01191666666666666666666666667", "-0.3575000000000000000000000001", None, "VERY HIGH", 100, "LOW", 47),
        ("dimo-software-only-compatible-car", "dimo", "DIMO", "DEPIN_NODE", "vehicle-data", "8.99", "-0.2993874002349686587029523810", "-0.9990680764236996397206419833", None, "VERY HIGH", 100, "MODERATE", 52),
        ("mysterium-b2b-existing-device", "mysterium-network-node", "Mysterium Network Node", "DEPIN_NODE", "bandwidth-node", "2.00", "-0.006758015240225208", "-0.10137022860337812", None, "VERY HIGH", 100, "LOW", 45),
    ]
    return {
        "items": [
            {
                "rank": index,
                "strategy": {
                    "strategy_id": strategy_id,
                    "strategy_version": "v1",
                    "opportunity_id": opportunity_id,
                    "opportunity_type": opportunity_type,
                    "game_id": opportunity_id,
                    "game_name": name,
                    "name": f"{name} Strategy",
                    "chain": "test-chain",
                    "economy_type": economy_type,
                    "description": "Test strategy",
                    "primary_destination": {
                        "source_reference": {
                            "label": "Official site",
                            "url": f"https://example.com/{opportunity_id}",
                        }
                    },
                },
                "latest_snapshot": {
                    "snapshot_id": f"snapshot-{strategy_id}",
                    "strategy_id": strategy_id,
                    "strategy_version": "v1",
                    "opportunity_id": opportunity_id,
                    "opportunity_type": opportunity_type,
                    "game_id": opportunity_id,
                    "game_name": name,
                    "chain": "test-chain",
                    "economy_type": economy_type,
                    "calculated_at": "2026-08-31T12:00:00Z",
                    "capital": {
                        "total_capital": {"amount": capital, "currency": "USD"},
                    },
                    "earnings": {
                        "net_earnings_day": {"amount": net_day, "currency": "USD"},
                    },
                    "roi": {
                        "roi_total_30d": {"value": roi_30d, "status": "available"},
                        "break_even": {
                            "basis": "net_earnings_day",
                            "recovery_target": {"amount": capital, "currency": "USD"},
                            "days": break_even_days,
                            "status": "available" if break_even_days else "unavailable",
                        },
                    },
                    "confidence": {"available": True, "score": confidence_score, "label": confidence_label},
                    "risk": {"available": True, "score": risk_score, "label": risk_label},
                    "warnings": [
                        {
                            "code": "test-warning",
                            "message": "Important strategy caveat.",
                            "severity": "warning",
                        }
                    ],
                    "freshness": {
                        "overall_status": "fresh",
                        "calculated_at": "2026-08-31T12:00:00Z",
                        "status_counts": {"fresh": 1, "stale": 0, "missing": 0, "invalid": 0},
                        "input_count": 1,
                    },
                    "versions": {
                        "adapter_contract_version": "adapter-contract-v1",
                        "model_version": "roi-core-v1",
                        "scoring_methodology_version": "risk-confidence-v1",
                    },
                },
            }
            for index, (
                strategy_id,
                opportunity_id,
                name,
                opportunity_type,
                economy_type,
                capital,
                net_day,
                roi_30d,
                break_even_days,
                risk_label,
                risk_score,
                confidence_label,
                confidence_score,
            ) in enumerate(strategies, start=1)
        ],
        "page": {"limit": 100, "offset": 0, "total": len(strategies)},
    }


def _opportunities_payload() -> dict[str, object]:
    return {
        "items": [
            {
                "opportunity_id": "grass",
                "opportunity_type": "DEPIN_NODE",
                "name": "Grass",
                "status": "candidate",
                "platforms": ["browser-extension", "desktop"],
                "chains": ["solana"],
                "economy_types": ["bandwidth-contribution", "points-program"],
                "reward_asset_or_points_type": ["Grass Points", "GRASS"],
                "value_realization_status": "non_transferable_points",
                "data_feasibility_status": "PARTIAL",
                "strategy_count": 0,
                "primary_destination": {
                    "source_reference": {
                        "label": "Official site",
                        "url": "https://www.grass.io/",
                    }
                },
            }
        ],
        "page": {"limit": 100, "offset": 0, "total": 1},
    }
