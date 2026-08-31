"""Generate the first Distribution MVP learning batch from GamCryp API facts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.distribution.content_pack import (
    ContentClaim,
    ContentFactSet,
    ContentPackLite,
    ContentReadiness,
    ContentSource,
    DistributionLinks,
    EditorialContent,
    MetricFact,
    ScoreFact,
    SourceReference,
    build_utm_url,
    derive_readiness,
    set_expected_source_hash,
)
from app.strategies.refreshability import classify_refreshability

LEARNING_BATCH_ID = "distribution-learning-batch-001"
LEARNING_BATCH_CREATED_AT = "2026-08-31T18:00:00Z"


def build_learning_batch(
    rankings_payload: dict[str, Any],
    opportunities_payload: dict[str, Any],
    *,
    base_url: str = "https://gamcryp.com",
    created_at: str = LEARNING_BATCH_CREATED_AT,
) -> list[ContentPackLite]:
    """Build 10 draft packs from current GamCryp ranking/catalog data."""

    ranking_items = {item["strategy"]["strategy_id"]: item for item in rankings_payload["items"]}
    opportunities = {item["opportunity_id"]: item for item in opportunities_payload["items"]}
    packs = [
        _geodnet_leader_pack(ranking_items["geodnet-empty-hex-triple-band-base-station"], base_url, created_at),
        _dfk_lock_pack(ranking_items["dfk-crystalvale-jeweler-cjewel-5000-max-lock"], base_url, created_at),
        _farmers_world_tiny_pack(ranking_items["farmers-world-axe-wood-production"], base_url, created_at),
        _weatherxm_location_pack(ranking_items["weatherxm-d1-wifi-station"], base_url, created_at),
        _splinterlands_ev_pack(ranking_items["splinterlands-modern-ranked-sps-ev"], base_url, created_at),
        _storj_existing_hardware_pack(ranking_items["storj-existing-hardware-storage-node"], base_url, created_at),
        _dimo_subscription_pack(ranking_items["dimo-software-only-compatible-car"], base_url, created_at),
        _mysterium_demand_pack(ranking_items["mysterium-b2b-existing-device"], base_url, created_at),
        _grass_unavailable_pack(opportunities["grass"], base_url, created_at),
        _methodology_pack(base_url, created_at),
    ]
    return [_finalize_readiness(pack) for pack in packs]


def _geodnet_leader_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-geodnet-rank-risk-20260831",
        content_angle="current rank leader with major risk",
        hook="GEODNET leads GamCryp's current modeled rankings, but the catch matters.",
        core_message=(
            "GamCryp models GEODNET's empty-hex base-station scenario at high return potential "
            "with very high risk from location and signal-quality dependence."
        ),
        x_post=(
            "GEODNET leads GamCryp's current modeled rankings, but it is not a recommendation.\n\n"
            "Modeled capital: $695. Net/day: $2.59/day. 30D ROI: 11.16%.\n\n"
            "Risk: VERY HIGH. Confidence: MODERATE. The catch: location, hex occupancy, and station quality "
            "can change the outcome materially.\n\n"
            "{url}"
        ),
        youtube_title="GEODNET ROI looks strong. Here is the catch.",
        youtube_short_script=(
            "GEODNET is one of the clearest examples of why ROI alone is not enough. "
            "The user runs a geospatial base station. GamCryp's current scenario uses $695 of modeled capital, "
            "$2.59/day of net earnings, and 11.16% 30D ROI. But this is an empty-hex, quality-dependent model. "
            "If your location, signal, or competition is worse, the result can change sharply. "
            "Use GamCryp to inspect the numbers, confidence, and risk before treating the model as useful."
        ),
        youtube_description=(
            "A GamCryp data-backed Short explaining GEODNET's modeled base-station economics and why "
            "high ROI can still carry very high risk."
        ),
        visual_plan=[
            "Open with GEODNET name and a clean rank card.",
            "Show capital, net/day, and 30D ROI as three compact data beats.",
            "Cut to a map/hex-style visual labelled location quality.",
            "End on the GamCryp strategy page with risk and confidence visible.",
        ],
        thumbnail_text="GEODNET ROI: catch first",
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $695.", "snapshot.capital.total_capital.amount", _capital_value(item), "$695"),
            _claim("net_day", "Modeled net earnings are $2.59/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "$2.59/day"),
            _claim("roi_30d", "Modeled 30D ROI is 11.16%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "11.16%"),
        ],
    )


def _dfk_lock_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-dfk-lock-risk-20260831",
        content_angle="high-confidence model with lock risk",
        hook="DeFi Kingdoms shows why confidence and risk are different.",
        core_message=(
            "GamCryp can have high confidence in the DFK Jeweler calculation while still marking "
            "the strategy very high risk because capital is locked and exit penalties matter."
        ),
        x_post=(
            "DeFi Kingdoms shows why confidence and risk are not the same.\n\n"
            "GamCryp models the 5000 JEWEL max-lock strategy at $40.64 capital, $0.0136/day net, "
            "and 1.00% 30D ROI.\n\n"
            "Confidence: HIGH. Risk: VERY HIGH because the lock and emergency-exit terms dominate the catch.\n\n"
            "{url}"
        ),
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $40.64.", "snapshot.capital.total_capital.amount", _capital_value(item), "$40.64"),
            _claim("net_day", "Modeled net earnings are $0.0136/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "$0.0136/day"),
            _claim("roi_30d", "Modeled 30D ROI is 1.00%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "1.00%"),
        ],
    )


def _farmers_world_tiny_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-farmers-world-tiny-economics-20260831",
        content_angle="low-cost but weak economics",
        hook="Farmers World is cheap to model, but cheap is not the same as attractive.",
        core_message=(
            "GamCryp uses Farmers World to show that tiny capital and tiny earnings can produce weak "
            "or negative economics once market realization is considered."
        ),
        x_post=(
            "Farmers World is a useful reminder: cheap entry is not the same as good economics.\n\n"
            "GamCryp's axe strategy shows capital under $0.01, net/day under $0.0001/day, and 30D ROI of -0.92%.\n\n"
            "This is why GamCryp separates modeled return from risk, liquidity, and confidence.\n\n"
            "{url}"
        ),
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is under $0.01.", "snapshot.capital.total_capital.amount", _capital_value(item), "<$0.01"),
            _claim("net_day", "Modeled net earnings are under $0.0001/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "<$0.0001/day"),
            _claim("roi_30d", "Modeled 30D ROI is -0.92%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "-0.92%"),
        ],
    )


def _weatherxm_location_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-weatherxm-cell-quality-20260831",
        content_angle="hardware node with location caveat",
        hook="WeatherXM is not one universal ROI number.",
        core_message=(
            "GamCryp models a WeatherXM D1 WiFi Station scenario, but the station's cell, quality, "
            "and live reward feed are the central caveats."
        ),
        x_post=(
            "WeatherXM is not one universal ROI number.\n\n"
            "GamCryp's D1 WiFi Station model uses $139 capital, net/day of -$0.0003/day, "
            "and 30D ROI of -0.01%.\n\n"
            "The catch: station quality, cell-level rewards, and live reward access can change the result.\n\n"
            "{url}"
        ),
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $139.", "snapshot.capital.total_capital.amount", _capital_value(item), "$139"),
            _claim("net_day", "Modeled net earnings are -$0.0003/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "-$0.0003/day"),
            _claim("roi_30d", "Modeled 30D ROI is -0.01%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "-0.01%"),
        ],
    )


def _splinterlands_ev_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-splinterlands-expected-value-20260831",
        content_angle="expected value is not guaranteed earnings",
        hook="Splinterlands is modeled as expected value, not guaranteed income.",
        core_message=(
            "GamCryp treats Splinterlands ranked SPS rewards as a performance-dependent expected-value model, "
            "so win assumptions and reward uncertainty stay visible."
        ),
        x_post=(
            "Splinterlands is modeled as expected value, not guaranteed income.\n\n"
            "GamCryp's Modern Ranked SPS strategy uses $10 capital, -$0.0007/day net, "
            "and -0.20% 30D ROI.\n\n"
            "The catch: win rate and SPS per win are assumptions, so confidence stays LOW and uncertainty is explicit.\n\n"
            "{url}"
        ),
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $10.", "snapshot.capital.total_capital.amount", _capital_value(item), "$10"),
            _claim("net_day", "Modeled net earnings are -$0.0007/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "-$0.0007/day"),
            _claim("roi_30d", "Modeled 30D ROI is -0.20%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "-0.20%"),
        ],
    )


def _storj_existing_hardware_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-storj-existing-hardware-catch-20260831",
        content_angle="existing hardware and demand-driven earnings",
        hook="Storj node economics depend on demand and held-back payouts.",
        core_message=(
            "GamCryp's Storj strategy intentionally models an existing-hardware scenario and keeps the demand "
            "and held-back payout caveats visible."
        ),
        x_post=(
            "Storj node economics depend on demand and held-back payouts.\n\n"
            "GamCryp's existing-hardware scenario uses $1 capital, -$0.0119/day net, "
            "and -35.75% 30D ROI.\n\n"
            "The catch: storage fill, egress, and held-back amounts matter more than a simple headline ROI.\n\n"
            "{url}"
        ),
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $1.", "snapshot.capital.total_capital.amount", _capital_value(item), "$1"),
            _claim("net_day", "Modeled net earnings are -$0.0119/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "-$0.0119/day"),
            _claim("roi_30d", "Modeled 30D ROI is -35.75%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "-35.75%"),
        ],
    )


def _dimo_subscription_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-dimo-subscription-catch-20260831",
        content_angle="software-only cost versus reward",
        hook="DIMO looks lightweight, but the subscription cost dominates this scenario.",
        core_message=(
            "GamCryp's DIMO software-only compatible-car model exposes the cost side first instead of "
            "turning vehicle data rewards into a blanket recommendation."
        ),
        x_post=(
            "DIMO looks lightweight, but the cost side matters.\n\n"
            "GamCryp's software-only compatible-car model uses $8.99 capital, -$0.30/day net, "
            "and -99.91% 30D ROI.\n\n"
            "The catch: rewards depend on network points and vehicle-specific eligibility.\n\n"
            "{url}"
        ),
        youtube_title="DIMO: vehicle data rewards need the cost side",
        youtube_short_script=(
            "DIMO is a DePIN vehicle-data project. The user connects a compatible car and may receive DIMO rewards. "
            "GamCryp's software-only scenario uses $8.99 of capital, -$0.30/day net, and -99.91% 30D ROI. "
            "That is not a verdict on the project. It is the current modeled scenario. The major catch is that rewards "
            "depend on vehicle eligibility, network points, and recurring costs."
        ),
        youtube_description=(
            "A GamCryp Short showing why DIMO's vehicle-data rewards need cost, eligibility, risk, and confidence shown together."
        ),
        visual_plan=[
            "Open on DIMO name and a connected-car concept.",
            "Show the cost line before the reward line.",
            "Highlight the modeled negative 30D ROI without recommendation language.",
            "End with GamCryp risk and confidence context.",
        ],
        thumbnail_text="DIMO cost vs reward",
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $8.99.", "snapshot.capital.total_capital.amount", _capital_value(item), "$8.99"),
            _claim("net_day", "Modeled net earnings are -$0.30/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "-$0.30/day"),
            _claim("roi_30d", "Modeled 30D ROI is -99.91%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "-99.91%"),
        ],
    )


def _mysterium_demand_pack(item: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    pack = _strategy_pack(
        item,
        base_url,
        created_at,
        content_id="x-mysterium-demand-risk-20260831",
        content_angle="demand-dependent node economics",
        hook="Mysterium node income is demand-dependent, not a fixed yield.",
        core_message=(
            "GamCryp's Mysterium model uses a B2B-only existing-device assumption and keeps location, demand, "
            "and policy sensitivity in the foreground."
        ),
        x_post=(
            "Mysterium node income is demand-dependent, not a fixed yield.\n\n"
            "GamCryp's B2B existing-device model uses $2 capital, -$0.0068/day net, "
            "and -10.14% 30D ROI.\n\n"
            "The catch: region, IP quality, uptime, and traffic policy can materially change outcomes.\n\n"
            "{url}"
        ),
    )
    return _with_claims(
        pack,
        [
            _claim("capital", "Modeled capital is $2.", "snapshot.capital.total_capital.amount", _capital_value(item), "$2"),
            _claim("net_day", "Modeled net earnings are -$0.0068/day.", "snapshot.earnings.net_earnings_day.amount", _net_day_value(item), "-$0.0068/day"),
            _claim("roi_30d", "Modeled 30D ROI is -10.14%.", "snapshot.roi.roi_total_30d.value", _roi_30d_value(item), "-10.14%"),
        ],
    )


def _grass_unavailable_pack(opportunity: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    canonical_url = f"{base_url}/opportunities/{opportunity['opportunity_id']}"
    content_id = "x-grass-roi-unavailable-20260831"
    x_utm_url = build_utm_url(canonical_url, source="x", medium="social", content_id=content_id)
    pack = ContentPackLite(
        content_id=content_id,
        source=ContentSource(
            opportunity_id=opportunity["opportunity_id"],
            source_snapshot_hash="",
            official_source_refs=_source_refs(opportunity),
        ),
        facts=ContentFactSet(
            project_name=opportunity["name"],
            opportunity_type=opportunity["opportunity_type"],
            modeled_return=MetricFact(
                value=None,
                unit=None,
                display="ROI unavailable",
                source_path="opportunity.value_realization_status",
                status="unavailable",
                reason="Points do not currently have a reproducible executable value route in GamCryp.",
            ),
            freshness=MetricFact(
                value=opportunity.get("data_feasibility_status"),
                unit=None,
                display=opportunity.get("data_feasibility_status", "unknown"),
                source_path="opportunity.data_feasibility_status",
                status="available",
            ),
            reward_source="Bandwidth contribution and points program.",
            major_catch="Grass points are not modeled as financial ROI unless a lawful, reproducible value route exists.",
        ),
        editorial=EditorialContent(
            content_angle="ROI unavailable because points are not executable value",
            readiness=ContentReadiness.YELLOW,
            hook="Grass is useful for GamCryp precisely because ROI is unavailable.",
            core_message=(
                "GamCryp can explain Grass without pretending points are dollars. The current catalog marks "
                "Grass as a points-based DePIN opportunity with financial ROI unavailable."
            ),
            x_post=(
                "Grass is useful for GamCryp because the honest answer is: ROI unavailable.\n\n"
                "The project has points-based rewards, but GamCryp does not convert points into financial ROI "
                "unless there is a reproducible exit route.\n\n"
                "That is the point of the model: no fake zero, no made-up yield.\n\n"
                "{url}"
            ).format(url=x_utm_url),
            youtube_title="Grass: why GamCryp says ROI unavailable",
            youtube_short_script=(
                "Grass is a good example of a Web3 earning opportunity where GamCryp should not invent ROI. "
                "The user contributes bandwidth and may earn points. But points are not the same as a realizable "
                "market return. GamCryp marks ROI unavailable until a lawful, reproducible value route exists. "
                "That protects users from fake precision."
            ),
            youtube_description=(
                "A GamCryp Short explaining why points-based opportunities like Grass may be useful to track while ROI remains unavailable."
            ),
            visual_plan=[
                "Open with Grass name and ROI unavailable.",
                "Show points are not dollars.",
                "Show GamCryp rule: no executable value route means no financial ROI.",
                "End on the Grass opportunity page.",
            ],
            thumbnail_text="Grass ROI unavailable",
            disclosure="Draft educational content. Not investment advice. No guaranteed rewards or returns.",
        ),
        distribution=DistributionLinks(
            canonical_site_url=canonical_url,
            content_id=content_id,
            x_utm_url=x_utm_url,
            youtube_utm_url=build_utm_url(canonical_url, source="youtube", medium="short", content_id=content_id),
        ),
        created_at=created_at,
    )
    return set_expected_source_hash(pack)


def _methodology_pack(base_url: str, created_at: str) -> ContentPackLite:
    canonical_url = f"{base_url}/methodology"
    content_id = "x-gamcryp-methodology-not-recommendation-20260831"
    x_utm_url = build_utm_url(canonical_url, source="x", medium="social", content_id=content_id)
    pack = ContentPackLite(
        content_id=content_id,
        source=ContentSource(
            opportunity_id="gamcryp-methodology",
            source_snapshot_hash="",
            official_source_refs=[SourceReference(label="GamCryp methodology", url=canonical_url)],
        ),
        facts=ContentFactSet(
            project_name="GamCryp",
            opportunity_type="METHODOLOGY",
            freshness=MetricFact(
                value="not_applicable",
                unit=None,
                display="not applicable",
                source_path="facts.freshness.value",
                status="available",
            ),
            reward_source="GamCryp compares modeled strategy-specific opportunity economics.",
            major_catch="Rank is a comparison signal, not a recommendation or guaranteed return.",
        ),
        editorial=EditorialContent(
            content_angle="methodology explanation",
            readiness=ContentReadiness.GREEN,
            hook="GamCryp ranks strategies, not hype.",
            core_message=(
                "GamCryp content should explain capital, realizable earnings, confidence, risk, and freshness "
                "from the same source chain users see on the site."
            ),
            x_post=(
                "GamCryp ranks strategies, not hype.\n\n"
                "A high modeled ROI can still carry high risk. A low-cost opportunity can still have weak economics. "
                "And if rewards are not reproducible, ROI stays unavailable.\n\n"
                "The goal is decision clarity, not a recommendation.\n\n"
                "{url}"
            ).format(url=x_utm_url),
            disclosure="Draft educational content. Not investment advice. No guaranteed rewards or returns.",
        ),
        distribution=DistributionLinks(
            canonical_site_url=canonical_url,
            content_id=content_id,
            x_utm_url=x_utm_url,
            youtube_utm_url=build_utm_url(canonical_url, source="youtube", medium="short", content_id=content_id),
        ),
        created_at=created_at,
    )
    return set_expected_source_hash(pack)


def _strategy_pack(
    item: dict[str, Any],
    base_url: str,
    created_at: str,
    *,
    content_id: str,
    content_angle: str,
    hook: str,
    core_message: str,
    x_post: str,
    youtube_title: str | None = None,
    youtube_short_script: str | None = None,
    youtube_description: str | None = None,
    visual_plan: list[str] | None = None,
    thumbnail_text: str | None = None,
) -> ContentPackLite:
    strategy = item["strategy"]
    snapshot = item["latest_snapshot"]
    canonical_url = f"{base_url}/strategies/{strategy['strategy_id']}"
    risk = snapshot["risk"]
    confidence = snapshot["confidence"]
    primary_destination = strategy.get("primary_destination") or {}
    official_source = primary_destination.get("source_reference")
    pack = ContentPackLite(
        content_id=content_id,
        source=ContentSource(
            opportunity_id=strategy["opportunity_id"],
            strategy_id=strategy["strategy_id"],
            snapshot_id=snapshot["snapshot_id"],
            snapshot_timestamp=snapshot["calculated_at"],
            source_snapshot_hash="",
            strategy_version=strategy["strategy_version"],
            adapter_contract_version=snapshot["versions"]["adapter_contract_version"],
            model_version=snapshot["versions"]["model_version"],
            scoring_methodology_version=snapshot["versions"].get("scoring_methodology_version"),
            refreshability=classify_refreshability(strategy["strategy_id"]).refreshability,
            official_source_refs=[SourceReference(**official_source)] if official_source else [],
        ),
        facts=ContentFactSet(
            project_name=snapshot["game_name"],
            opportunity_type=strategy["opportunity_type"],
            capital=_money_fact(
                snapshot["capital"]["total_capital"]["amount"],
                snapshot["capital"]["total_capital"]["currency"],
                "snapshot.capital.total_capital.amount",
            ),
            modeled_return=_ratio_fact(
                snapshot["roi"]["roi_total_30d"]["value"],
                "snapshot.roi.roi_total_30d.value",
                label="30D ROI",
            ),
            net_earnings=_money_day_fact(
                snapshot["earnings"]["net_earnings_day"]["amount"],
                snapshot["earnings"]["net_earnings_day"]["currency"],
                "snapshot.earnings.net_earnings_day.amount",
            ),
            break_even=_break_even_fact(snapshot["roi"]["break_even"]),
            risk=ScoreFact(
                score=risk.get("score"),
                label=risk.get("label"),
                display=_score_display(risk),
                source_path="snapshot.risk",
            ),
            confidence=ScoreFact(
                score=confidence.get("score"),
                label=confidence.get("label"),
                display=_score_display(confidence),
                source_path="snapshot.confidence",
            ),
            freshness=MetricFact(
                value=snapshot["freshness"]["overall_status"],
                unit=None,
                display=snapshot["freshness"]["overall_status"],
                source_path="snapshot.freshness.overall_status",
                status="available",
            ),
            reward_source=_reward_source(strategy, snapshot),
            major_catch=_major_catch(snapshot),
        ),
        editorial=EditorialContent(
            content_angle=content_angle,
            readiness=ContentReadiness.GREEN,
            hook=hook,
            core_message=core_message,
            x_post=x_post.format(
                url=build_utm_url(canonical_url, source="x", medium="social", content_id=content_id)
            ),
            youtube_title=youtube_title,
            youtube_short_script=youtube_short_script,
            youtube_description=youtube_description,
            visual_plan=visual_plan or [],
            thumbnail_text=thumbnail_text,
            disclosure="Draft educational content. Not investment advice. No guaranteed rewards or returns.",
        ),
        distribution=DistributionLinks(
            canonical_site_url=canonical_url,
            content_id=content_id,
            x_utm_url=build_utm_url(canonical_url, source="x", medium="social", content_id=content_id),
            youtube_utm_url=build_utm_url(canonical_url, source="youtube", medium="short", content_id=content_id),
        ),
        created_at=created_at,
    )
    return set_expected_source_hash(pack)


def _with_claims(pack: ContentPackLite, claims: list[ContentClaim]) -> ContentPackLite:
    updated = pack.model_copy(update={"claims": claims})
    return set_expected_source_hash(updated)


def _finalize_readiness(pack: ContentPackLite) -> ContentPackLite:
    readiness = derive_readiness(pack)
    updated = pack.model_copy(update={"editorial": pack.editorial.model_copy(update={"readiness": readiness})})
    return set_expected_source_hash(updated)


def _claim(claim_id: str, text: str, source_path: str, source_value: str, display_value: str) -> ContentClaim:
    return ContentClaim(
        claim_id=claim_id,
        text=text,
        source_path=source_path,
        source_value=source_value,
        display_value=display_value,
    )


def _capital_value(item: dict[str, Any]) -> str:
    return item["latest_snapshot"]["capital"]["total_capital"]["amount"]


def _net_day_value(item: dict[str, Any]) -> str:
    return item["latest_snapshot"]["earnings"]["net_earnings_day"]["amount"]


def _roi_30d_value(item: dict[str, Any]) -> str:
    return item["latest_snapshot"]["roi"]["roi_total_30d"]["value"]


def _money_fact(amount: str, currency: str, source_path: str) -> MetricFact:
    return MetricFact(value=amount, unit=currency, display=_format_money(amount, currency), source_path=source_path)


def _money_day_fact(amount: str, currency: str, source_path: str) -> MetricFact:
    return MetricFact(value=amount, unit=f"{currency}/day", display=f"{_format_money(amount, currency)}/day", source_path=source_path)


def _ratio_fact(value: str | None, source_path: str, *, label: str) -> MetricFact:
    if value is None:
        return MetricFact(value=None, unit="ratio", display=f"{label} unavailable", source_path=source_path, status="unavailable")
    return MetricFact(value=value, unit="ratio", display=_format_ratio(value), source_path=source_path)


def _break_even_fact(break_even: dict[str, Any]) -> MetricFact:
    days = break_even.get("days")
    if not days:
        return MetricFact(
            value=None,
            unit="days",
            display="Break-even unavailable",
            source_path="snapshot.roi.break_even.days",
            status="unavailable",
            reason=break_even.get("reason"),
        )
    return MetricFact(value=days, unit="days", display=_format_days(days), source_path="snapshot.roi.break_even.days")


def _score_display(score: dict[str, Any]) -> str:
    label = score.get("label") or "unavailable"
    value = score.get("score")
    return f"{label} {value}/100" if value is not None else label


def _reward_source(strategy: dict[str, Any], snapshot: dict[str, Any]) -> str:
    opportunity_type = strategy.get("opportunity_type", "opportunity")
    economy_type = strategy.get("economy_type") or snapshot.get("economy_type")
    return f"{opportunity_type} strategy using {economy_type} rewards."


def _major_catch(snapshot: dict[str, Any]) -> str:
    warnings = snapshot.get("warnings") or []
    if warnings:
        return warnings[0]["message"]
    risk = snapshot.get("risk") or {}
    label = risk.get("label")
    if label in {"HIGH", "VERY HIGH"}:
        return f"Risk is {label}; review the strategy assumptions before acting."
    return "Review the strategy assumptions, freshness, and exit route before acting."


def _source_refs(opportunity: dict[str, Any]) -> list[SourceReference]:
    primary = opportunity.get("primary_destination") or {}
    source = primary.get("source_reference")
    return [SourceReference(**source)] if source else []


def _format_money(amount: str, currency: str) -> str:
    value = _decimal(amount)
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    prefix = "$" if currency == "USD" else f"{currency} "
    if absolute == 0:
        return f"{prefix}0"
    if absolute < Decimal("0.0001"):
        return f"{sign}<{prefix}0.0001"
    if absolute < Decimal("1"):
        formatted = absolute.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return f"{sign}{prefix}{_trim_decimal(formatted)}"
    if absolute < Decimal("1000"):
        formatted = absolute.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{sign}{prefix}{_trim_decimal(formatted)}"
    formatted = absolute.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{sign}{prefix}{formatted:,}"


def _format_ratio(value: str) -> str:
    percent = _decimal(value) * Decimal("100")
    absolute = abs(percent)
    sign = "-" if percent < 0 else ""
    if absolute != 0 and absolute < Decimal("0.01"):
        return f"{sign}<0.01%"
    formatted = absolute.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{sign}{_trim_decimal(formatted)}%"


def _format_days(days: str) -> str:
    value = _decimal(days).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{value:,} days"


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal string: {value}") from exc


def _trim_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered
