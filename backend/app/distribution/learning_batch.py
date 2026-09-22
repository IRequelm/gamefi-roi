"""Generate the first Distribution MVP learning batch from GamCryp API facts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import re
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
from app.strategies.taxonomy import canonical_type

LEARNING_BATCH_ID = "distribution-learning-batch-001"
LEARNING_BATCH_CREATED_AT = "2026-08-31T18:00:00Z"


def build_learning_batch(
    rankings_payload: dict[str, Any],
    opportunities_payload: dict[str, Any],
    *,
    base_url: str = "https://gamcryp.com",
    created_at: str = LEARNING_BATCH_CREATED_AT,
    include_x_guides: bool = False,
) -> list[ContentPackLite]:
    """Build 10 draft packs from current GamCryp ranking/catalog data."""

    ranking_items = {item["strategy"]["strategy_id"]: item for item in rankings_payload["items"]}
    opportunities = {item["opportunity_id"]: item for item in opportunities_payload["items"]}
    # The first learning batch predates the current catalog and named a fixed
    # set of strategy IDs. A stale ranking response (or a deliberate
    # fail-closed empty ranking page) must reduce the batch, not crash the
    # unattended worker. Every retained pack is still generated from the exact
    # current API item; absent strategies are simply omitted.
    strategy_builders = (
        ("geodnet-empty-hex-triple-band-base-station", _geodnet_leader_pack),
        ("dfk-crystalvale-jeweler-cjewel-5000-max-lock", _dfk_lock_pack),
        ("farmers-world-axe-wood-production", _farmers_world_tiny_pack),
        ("weatherxm-d1-wifi-station", _weatherxm_location_pack),
        ("splinterlands-modern-ranked-sps-ev", _splinterlands_ev_pack),
        ("storj-existing-hardware-storage-node", _storj_existing_hardware_pack),
        ("dimo-software-only-compatible-car", _dimo_subscription_pack),
        ("mysterium-b2b-existing-device", _mysterium_demand_pack),
    )
    packs = [builder(ranking_items[strategy_id], base_url, created_at) for strategy_id, builder in strategy_builders if strategy_id in ranking_items]
    if "grass" in opportunities:
        packs.append(_grass_unavailable_pack(opportunities["grass"], base_url, created_at))
    if include_x_guides:
        packs.extend(
            _guide_only_pack(opportunity, base_url, created_at)
            for opportunity in _select_guide_opportunities(opportunities.values())
        )
    packs.append(_methodology_pack(base_url, created_at))
    return [_finalize_readiness(pack) for pack in packs]


def _select_guide_opportunities(opportunities: Any) -> tuple[dict[str, Any], ...]:
    """Select a small, deterministic cross-category guide buffer.

    The content batch is intentionally bounded. Prefer a game guide when the
    catalog has one, then DePIN and points guides, while keeping at most one
    opportunity per canonical type. A missing guidance block means we do not
    invent registration or gameplay instructions.
    """

    candidates = [
        item
        for item in opportunities
        if isinstance(item, dict)
        and _is_canonical_opportunity(item)
        and isinstance(item.get("guidance"), dict)
        and item["guidance"].get("how_to_start")
        and item["guidance"].get("what_you_need")
        and _opportunity_source_refs(item)
    ]
    priority = {"GAME": 0, "DEPIN_NODE": 1, "POINTS": 2}
    candidates.sort(key=lambda item: (priority.get(str(item.get("opportunity_type", "")), 3), str(item.get("opportunity_id", ""))))
    selected: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for item in candidates:
        opportunity_type = str(item.get("opportunity_type", ""))
        if opportunity_type in seen_types:
            continue
        selected.append(item)
        seen_types.add(opportunity_type)
        if len(selected) == 3:
            break
    return tuple(selected)


def _is_canonical_opportunity(opportunity: dict[str, Any]) -> bool:
    try:
        canonical_type(str(opportunity.get("opportunity_type", "")))
    except ValueError:
        return False
    return True


def _opportunity_source_refs(opportunity: dict[str, Any]) -> list[SourceReference]:
    refs: list[SourceReference] = []
    raw_refs = opportunity.get("official_source_references") or opportunity.get("source_references") or ()
    if isinstance(raw_refs, list):
        for raw in raw_refs:
            if isinstance(raw, dict) and raw.get("label") and raw.get("url"):
                refs.append(SourceReference(label=str(raw["label"]), url=str(raw["url"])))
            elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                refs.append(SourceReference(label=str(raw[0]), url=str(raw[1])))
    primary = opportunity.get("primary_destination") or {}
    source = primary.get("source_reference") if isinstance(primary, dict) else None
    if isinstance(source, dict) and source.get("label") and source.get("url"):
        refs.append(SourceReference(label=str(source["label"]), url=str(source["url"])))
    unique: dict[str, SourceReference] = {ref.url: ref for ref in refs}
    return list(unique.values())


def _guide_only_pack(opportunity: dict[str, Any], base_url: str, created_at: str) -> ContentPackLite:
    """Build a non-financial, catalog-backed X guide pack."""

    opportunity_id = str(opportunity["opportunity_id"])
    name = str(opportunity["name"])
    guidance = opportunity["guidance"]
    refs = _opportunity_source_refs(opportunity)
    canonical_url = f"{base_url}/opportunities/{opportunity_id}"
    evidence_key = json.dumps(
        {
            "opportunity_id": opportunity_id,
            "guidance": guidance,
            "refs": [ref.model_dump(mode="json") for ref in refs],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    version = hashlib.sha256(evidence_key.encode("utf-8")).hexdigest()[:10]
    content_id = f"x-{opportunity_id}-how-to-start-{version}"
    x_utm_url = build_utm_url(canonical_url, source="x", medium="social", content_id=content_id)
    start = _compact_guide_text(
        str(guidance["how_to_start"][0]),
        limit=60,
        fallback=f"Review {name}'s official setup guide.",
    )
    need = _compact_guide_text(
        str(guidance["what_you_need"][0]),
        limit=60,
        fallback=f"Prepare the requirements listed by {name}.",
    )
    earning = _compact_guide_text(
        str((guidance.get("how_you_earn") or ("Review the documented reward mechanism.",))[0]),
        limit=60,
        fallback="Follow the documented reward or claim route.",
    )
    # The full guidance remains in factual_talking_points. X copy uses a
    # compact, numbered checklist so it is useful and fits X's hard limit.
    x_post = (
        f"{name}: how to start\n\n"
        f"1) Start: {start}\n"
        f"2) Need: {need}\n\n"
        f"3) Earn/claim: {earning} No fixed ROI is promised.\n"
        f"\n{x_utm_url}"
    )
    return set_expected_source_hash(
        ContentPackLite(
            content_id=content_id,
            source=ContentSource(
                opportunity_id=opportunity_id,
                source_snapshot_hash="",
                official_source_refs=refs,
            ),
            facts=ContentFactSet(
                project_name=name,
                opportunity_type=str(opportunity["opportunity_type"]),
                freshness=MetricFact(
                    value=str(opportunity.get("data_feasibility_status") or "unknown"),
                    unit=None,
                    display=str(opportunity.get("data_feasibility_status") or "unknown"),
                    source_path="opportunity.data_feasibility_status",
                    status="available",
                ),
                reward_source=(
                    f"{', '.join(str(value) for value in (opportunity.get('economy_types') or ())) or 'Documented project rewards'}; "
                    f"assets/points: {', '.join(str(value) for value in (opportunity.get('reward_asset_or_points_type') or ())) or 'not specified'}."
                ),
                major_catch=str(opportunity.get("feasibility_summary") or "Verify current requirements and the claim route before acting."),
            ),
            editorial=EditorialContent(
                content_angle="how-to start guide",
                readiness=ContentReadiness.YELLOW,
                hook=f"Want to start {name}? Check these two things first.",
                core_message=(
                    f"This is a catalog-backed starting guide for {name}. It uses the current structured guidance "
                    "and keeps ROI unavailable when a reproducible financial model is not present."
                ),
                x_post=x_post,
                disclosure="Educational guide. Verify current official terms. Not investment advice; no guaranteed rewards or returns.",
            ),
            distribution=DistributionLinks(
                canonical_site_url=canonical_url,
                content_id=content_id,
                x_utm_url=x_utm_url,
                youtube_utm_url=build_utm_url(canonical_url, source="youtube", medium="short", content_id=content_id),
            ),
            created_at=created_at,
        )
    )


def _compact_guide_text(text: str, *, limit: int, fallback: str) -> str:
    """Keep sourced guidance grammatical inside X's hard limit.

    An incomplete ellipsis is worse than a short, truthful fallback: it can
    make a reader believe a truncated requirement or reward claim is complete.
    """

    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    for sentence in re.split(r"(?<=[.!?;])\s+", normalized):
        candidate = sentence.strip()
        if candidate and len(candidate) <= limit:
            return candidate
    return " ".join(fallback.split())[:limit].rstrip(" ,;:")


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
            "Modeled capital: {capital}. Net/day: {net_day}. 30D ROI: {roi_30d}.\n\n"
            "Risk: VERY HIGH. Confidence: MODERATE. The catch: location, hex occupancy, and station quality "
            "can change the outcome materially.\n\n"
            "{url}"
        ),
        youtube_title="GEODNET ROI looks strong. Here is the catch.",
        youtube_short_script=(
            "GEODNET is one of the clearest examples of why ROI alone is not enough. "
            "The user runs a geospatial base station. GamCryp's current scenario uses {capital} of modeled capital, "
            "{net_day} of net earnings, and {roi_30d} 30D ROI. But this is an empty-hex, quality-dependent model. "
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
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp models the 5000 JEWEL max-lock strategy at {capital} capital, {net_day} net, "
            "and {roi_30d} 30D ROI.\n\n"
            "Confidence: HIGH. Risk: VERY HIGH because the lock and emergency-exit terms dominate the catch.\n\n"
            "{url}"
        ),
    )
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp's axe strategy shows capital {capital}, net/day {net_day}, and 30D ROI of {roi_30d}.\n\n"
            "This is why GamCryp separates modeled return from risk, liquidity, and confidence.\n\n"
            "{url}"
        ),
    )
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp's D1 WiFi Station model uses {capital} capital, net/day of {net_day}, "
            "and 30D ROI of {roi_30d}.\n\n"
            "The catch: station quality, cell-level rewards, and live reward access can change the result.\n\n"
            "{url}"
        ),
    )
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp's Modern Ranked SPS strategy uses {capital} capital, {net_day} net, "
            "and {roi_30d} 30D ROI.\n\n"
            "The catch: win rate and SPS per win are assumptions, so confidence stays LOW and uncertainty is explicit.\n\n"
            "{url}"
        ),
    )
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp's existing-hardware scenario uses {capital} capital, {net_day} net, "
            "and {roi_30d} 30D ROI.\n\n"
            "The catch: storage fill, egress, and held-back amounts matter more than a simple headline ROI.\n\n"
            "{url}"
        ),
    )
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp's software-only compatible-car model uses {capital} capital, {net_day} net, "
            "and {roi_30d} 30D ROI.\n\n"
            "The catch: rewards depend on network points and vehicle-specific eligibility.\n\n"
            "{url}"
        ),
        youtube_title="DIMO: vehicle data rewards need the cost side",
        youtube_short_script=(
            "DIMO is a DePIN vehicle-data project. The user connects a compatible car and may receive DIMO rewards. "
            "GamCryp's software-only scenario uses {capital} of capital, {net_day} net, and {roi_30d} 30D ROI. "
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
    return _with_snapshot_financial_claims(pack)


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
            "GamCryp's B2B existing-device model uses {capital} capital, {net_day} net, "
            "and {roi_30d} 30D ROI.\n\n"
            "The catch: region, IP quality, uptime, and traffic policy can materially change outcomes.\n\n"
            "{url}"
        ),
    )
    return _with_snapshot_financial_claims(pack)


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
    _validate_snapshot_context(strategy, snapshot)
    canonical_url = f"{base_url}/strategies/{strategy['strategy_id']}"
    risk = snapshot["risk"]
    confidence = snapshot["confidence"]
    primary_destination = strategy.get("primary_destination") or {}
    official_source = primary_destination.get("source_reference")
    capital_fact = _money_fact(
        snapshot["capital"]["total_capital"]["amount"],
        snapshot["capital"]["total_capital"]["currency"],
        "snapshot.capital.total_capital.amount",
    )
    modeled_return_fact = _ratio_fact(
        snapshot["roi"]["roi_total_30d"]["value"],
        "snapshot.roi.roi_total_30d.value",
        label="30D ROI",
    )
    net_earnings_fact = _money_day_fact(
        snapshot["earnings"]["net_earnings_day"]["amount"],
        snapshot["earnings"]["net_earnings_day"]["currency"],
        "snapshot.earnings.net_earnings_day.amount",
    )
    display_values = {
        "capital": capital_fact.display,
        "net_day": net_earnings_fact.display,
        "roi_30d": modeled_return_fact.display,
    }
    x_utm_url = build_utm_url(canonical_url, source="x", medium="social", content_id=content_id)
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
            # The catalog/API reference also carries source_role. The
            # distribution content-pack contract intentionally stores only
            # the public label and URL, so do not leak newer fields into this
            # strict legacy serialization model.
            official_source_refs=[SourceReference(label=official_source["label"], url=official_source["url"])] if official_source else [],
        ),
        facts=ContentFactSet(
            project_name=snapshot["game_name"],
            opportunity_type=strategy["opportunity_type"],
            capital=capital_fact,
            modeled_return=modeled_return_fact,
            net_earnings=net_earnings_fact,
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
            x_post=x_post.format(url=x_utm_url, **display_values),
            youtube_title=youtube_title,
            youtube_short_script=(
                youtube_short_script.format(**display_values) if youtube_short_script else None
            ),
            youtube_description=youtube_description,
            visual_plan=visual_plan or [],
            thumbnail_text=thumbnail_text,
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


def _with_claims(pack: ContentPackLite, claims: list[ContentClaim]) -> ContentPackLite:
    updated = pack.model_copy(update={"claims": claims})
    return set_expected_source_hash(updated)


def _with_snapshot_financial_claims(pack: ContentPackLite) -> ContentPackLite:
    facts = (
        ("capital", "Modeled capital is {display}.", pack.facts.capital),
        ("net_day", "Modeled net earnings are {display}.", pack.facts.net_earnings),
        ("roi_30d", "Modeled 30D ROI is {display}.", pack.facts.modeled_return),
    )
    claims: list[ContentClaim] = []
    for claim_id, text_template, fact in facts:
        if fact is None or fact.value is None or fact.status != "available":
            raise ValueError(f"Snapshot-backed claim {claim_id} requires an available source fact")
        claims.append(
            ContentClaim(
                claim_id=claim_id,
                text=text_template.format(display=fact.display),
                source_path=fact.source_path,
                source_value=fact.value,
                display_value=fact.display,
            )
        )
    return _with_claims(pack, claims)


def _finalize_readiness(pack: ContentPackLite) -> ContentPackLite:
    readiness = derive_readiness(pack)
    updated = pack.model_copy(update={"editorial": pack.editorial.model_copy(update={"readiness": readiness})})
    return set_expected_source_hash(updated)


def _validate_snapshot_context(strategy: dict[str, Any], snapshot: dict[str, Any]) -> None:
    expected = {
        "strategy_id": strategy.get("strategy_id"),
        "strategy_version": strategy.get("strategy_version"),
        "opportunity_id": strategy.get("opportunity_id"),
    }
    for field, expected_value in expected.items():
        if not expected_value or snapshot.get(field) != expected_value:
            raise ValueError(f"Latest snapshot {field} does not match the selected strategy context")
    if not snapshot.get("snapshot_id") or not snapshot.get("calculated_at"):
        raise ValueError("Latest snapshot context requires snapshot_id and calculated_at")
    declared_latest = strategy.get("latest_snapshot")
    if isinstance(declared_latest, dict) and declared_latest.get("snapshot_id"):
        if declared_latest["snapshot_id"] != snapshot["snapshot_id"]:
            raise ValueError("Ranking strategy and selected latest snapshot IDs do not match")


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
    return [SourceReference(label=source["label"], url=source["url"])] if source else []


def _format_money(amount: str, currency: str) -> str:
    value = _decimal(amount)
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    prefix = "$" if currency == "USD" else f"{currency} "
    if absolute == 0:
        return f"{prefix}0"
    if absolute < Decimal("0.0001"):
        return f"<{prefix}0.0001"
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
        return "<0.01%"
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
