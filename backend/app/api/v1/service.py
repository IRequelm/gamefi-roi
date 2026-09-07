"""Read-only API service over catalog, history, and scores."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.schemas import (
    BreakEvenMetric,
    CapitalMetrics,
    ClassificationSummaryPayload,
    EarningsMetrics,
    FreshnessPayload,
    GameDetail,
    GameSummary,
    HealthPayload,
    HistoryPage,
    MoneyAmount,
    OpsStatusPayload,
    OpportunitiesPage,
    OpportunityDetail,
    OpportunityLogoPayload,
    OpportunityGuidancePayload,
    RoiUnavailablePayload,
    OpportunitySummary,
    OutboundDestinationPayload,
    PageMeta,
    RankingItem,
    RankingsPage,
    RatioMetric,
    RoiMetrics,
    ScoreContributionPayload,
    ScorePayload,
    SourceReferencePayload,
    StrategiesPage,
    StrategySnapshotPayload,
    StrategyOpsStatusPayload,
    StrategySummary,
    SponsoredPlacementPayload,
    UnavailableFactorPayload,
    UncertaintyRangePayload,
    VersionPayload,
    WarningPayload,
)
from app.config.settings import Settings
from app.risk.results import METHODOLOGY_VERSION, SnapshotScoreResult
from app.storage.history import HistoryRepository, StrategyCalculationFailure, StrategySnapshot
from app.storage.monetization import MonetizationRepository
from app.storage.scoring import ScoringRepository
from app.strategies.catalog import (
    GameCatalogEntry,
    OpportunityCatalogEntry,
    OutboundDestination,
    SourceReference,
    StrategyCatalogEntry,
    get_game,
    get_opportunity,
    get_strategy,
    list_games,
    list_opportunities,
    list_strategies,
    outbound_destinations_for_opportunity,
    outbound_destinations_for_strategy,
    primary_destination_for_opportunity,
    primary_destination_for_strategy,
)

RANKING_ORDERING = [
    "roi_total_30d desc",
    "confidence_score desc",
    "risk_score asc",
    "calculated_at desc",
    "strategy_id asc",
]


class ApiDataService:
    def __init__(self, engine: Engine) -> None:
        self.history = HistoryRepository(engine)
        self.monetization = MonetizationRepository(engine)
        self.scoring = ScoringRepository(engine)

    def games_page(self, *, limit: int, offset: int) -> tuple[list[GameSummary], int]:
        games = list(list_games())
        page = _paginate(games, limit=limit, offset=offset)
        return [_game_summary(game) for game in page], len(games)

    def opportunities_page(self, *, limit: int, offset: int) -> tuple[list[OpportunitySummary], int]:
        opportunities = list(list_opportunities())
        page = _paginate(opportunities, limit=limit, offset=offset)
        return [_opportunity_summary(opportunity) for opportunity in page], len(opportunities)

    def opportunity_detail(self, opportunity_id: str) -> OpportunityDetail | None:
        opportunity = get_opportunity(opportunity_id)
        if opportunity is None:
            return None
        strategies = [
            self.strategy_summary(strategy, include_latest=True)
            for strategy in list_strategies()
            if strategy.opportunity_id == opportunity.opportunity_id
        ]
        return _opportunity_detail(opportunity, strategies=strategies)

    def game_detail(self, game_id: str) -> GameDetail | None:
        game = get_game(game_id)
        if game is None:
            return None
        strategies = [
            self.strategy_summary(strategy, include_latest=True)
            for strategy in list_strategies()
            if strategy.game_id == game.game_id
        ]
        return GameDetail(
            **_game_summary(game).model_dump(),
            strategies=[strategy for strategy in strategies if strategy is not None],
            outbound_destinations=[
                _outbound_destination(destination) for destination in outbound_destinations_for_opportunity(game.opportunity_id)
            ],
        )

    def strategies_page(
        self,
        *,
        limit: int,
        offset: int,
        game_id: str | None = None,
        opportunity_id: str | None = None,
        opportunity_type: str | None = None,
        chain: str | None = None,
        economy_type: str | None = None,
    ) -> tuple[list[StrategySummary], int]:
        strategies = [
            strategy
            for strategy in list_strategies()
            if (game_id is None or strategy.game_id == game_id)
            and (opportunity_id is None or strategy.opportunity_id == opportunity_id)
            and (opportunity_type is None or strategy.opportunity_type == opportunity_type)
            and (chain is None or strategy.chain == chain)
            and (economy_type is None or strategy.economy_type == economy_type)
        ]
        page = _paginate(strategies, limit=limit, offset=offset)
        return [self.strategy_summary(strategy, include_latest=True) for strategy in page], len(strategies)

    def strategy_summary(
        self,
        strategy: StrategyCatalogEntry,
        *,
        include_latest: bool = False,
    ) -> StrategySummary:
        latest = None
        if include_latest:
            snapshot = self.history.latest_snapshot(strategy.strategy_id, strategy_version=strategy.strategy_version)
            if snapshot is not None:
                score = self.scoring.get_score(snapshot.snapshot_id)
                latest = snapshot_payload(snapshot, strategy=strategy, score=score)
        return StrategySummary(
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.strategy_version,
            opportunity_id=strategy.opportunity_id,
            opportunity_type=strategy.opportunity_type,
            game_id=strategy.game_id,
            game_name=strategy.game_name,
            name=strategy.name,
            chain=strategy.chain,
            economy_type=strategy.economy_type,
            description=strategy.description,
            outbound_destinations=[
                _outbound_destination(destination) for destination in outbound_destinations_for_strategy(strategy.strategy_id)
            ],
            primary_destination=_maybe_outbound_destination(primary_destination_for_strategy(strategy.strategy_id)),
            latest_snapshot=latest,
            logo=_logo_payload(get_opportunity(strategy.opportunity_id)),
        )

    def strategy_detail(self, strategy_id: str) -> StrategySummary | None:
        strategy = get_strategy(strategy_id)
        if strategy is None:
            return None
        return self.strategy_summary(strategy, include_latest=True)

    def latest_snapshot(self, strategy_id: str) -> StrategySnapshotPayload | None:
        strategy = get_strategy(strategy_id)
        if strategy is None:
            return None
        snapshot = self.history.latest_snapshot(strategy.strategy_id, strategy_version=strategy.strategy_version)
        if snapshot is None:
            return None
        score = self.scoring.get_score(snapshot.snapshot_id)
        return snapshot_payload(snapshot, strategy=strategy, score=score)

    def history_page(
        self,
        strategy_id: str,
        *,
        limit: int,
        offset: int,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> HistoryPage | None:
        strategy = get_strategy(strategy_id)
        if strategy is None:
            return None
        start = _normalize_utc(start_at) if start_at is not None else datetime(1970, 1, 1, tzinfo=UTC)
        end = _normalize_utc(end_at) if end_at is not None else datetime.now(UTC)
        snapshots = self.history.ordered_time_series(
            strategy.strategy_id,
            start=start,
            end=end,
            strategy_version=strategy.strategy_version,
        )
        page = _paginate(snapshots, limit=limit, offset=offset)
        scores = self.scoring.get_scores_for_snapshots(tuple(snapshot.snapshot_id for snapshot in page))
        return HistoryPage(
            items=[
                snapshot_payload(snapshot, strategy=strategy, score=scores.get(snapshot.snapshot_id))
                for snapshot in page
            ],
            page=PageMeta(limit=limit, offset=offset, total=len(snapshots)),
        )

    def rankings_page(
        self,
        *,
        limit: int,
        offset: int,
        capital_min: Decimal | None = None,
        capital_max: Decimal | None = None,
        confidence_min: int | None = None,
        risk_max: int | None = None,
        game_id: str | None = None,
        opportunity_id: str | None = None,
        opportunity_type: str | None = None,
        chain: str | None = None,
        economy_type: str | None = None,
    ) -> RankingsPage:
        latest_snapshots = self.history.latest_snapshots()
        strategy_by_id = {strategy.strategy_id: strategy for strategy in list_strategies()}
        scores = self.scoring.get_scores_for_snapshots(tuple(snapshot.snapshot_id for snapshot in latest_snapshots))
        rows: list[tuple[StrategyCatalogEntry, StrategySnapshot, SnapshotScoreResult | None]] = []
        for snapshot in latest_snapshots:
            strategy = strategy_by_id.get(snapshot.strategy_id)
            if strategy is None:
                continue
            score = scores.get(snapshot.snapshot_id)
            if not _passes_filters(
                strategy=strategy,
                snapshot=snapshot,
                score=score,
                capital_min=capital_min,
                capital_max=capital_max,
                confidence_min=confidence_min,
                risk_max=risk_max,
                game_id=game_id,
                opportunity_id=opportunity_id,
                opportunity_type=opportunity_type,
                chain=chain,
                economy_type=economy_type,
            ):
                continue
            rows.append((strategy, snapshot, score))

        rows.sort(key=_ranking_sort_key)
        page_rows = _paginate(rows, limit=limit, offset=offset)
        return RankingsPage(
            items=[
                RankingItem(
                    rank=index + 1 + offset,
                    strategy=self.strategy_summary(strategy, include_latest=False),
                    latest_snapshot=snapshot_payload(snapshot, strategy=strategy, score=score),
                )
                for index, (strategy, snapshot, score) in enumerate(page_rows)
            ],
            page=PageMeta(limit=limit, offset=offset, total=len(rows)),
            ordering=RANKING_ORDERING,
            sponsored_placements=[
                SponsoredPlacementPayload(
                    placement_id=placement.placement_id,
                    opportunity_id=placement.opportunity_id,
                    strategy_id=placement.strategy_id,
                    surface=placement.surface,
                    status=placement.status.value,
                    label=placement.label,
                    disclosure_text=placement.disclosure_text,
                    campaign_name=placement.campaign_name,
                    sponsor_name=placement.sponsor_name,
                )
                for placement in self.monetization.active_sponsored_placements(surface="rankings")
            ],
        )


def snapshot_payload(
    snapshot: StrategySnapshot,
    *,
    strategy: StrategyCatalogEntry,
    score: SnapshotScoreResult | None,
) -> StrategySnapshotPayload:
    confidence, risk, scoring_methodology_version = _score_payloads(score)
    return StrategySnapshotPayload(
        snapshot_id=snapshot.snapshot_id,
        strategy_id=snapshot.strategy_id,
        strategy_version=snapshot.strategy_version,
        opportunity_id=strategy.opportunity_id,
        opportunity_type=strategy.opportunity_type,
        game_id=strategy.game_id,
        game_name=strategy.game_name,
        chain=strategy.chain,
        economy_type=strategy.economy_type,
        calculated_at=snapshot.calculated_at,
        capital=CapitalMetrics(
            total_capital=_money(snapshot.capital_metrics["total_capital"]),
            sunk_cost=_money(snapshot.capital_metrics["sunk_cost"]),
            recoverable_capital=_money(snapshot.capital_metrics["recoverable_capital"]),
            capital_at_risk=_money(snapshot.capital_metrics["capital_at_risk"]),
        ),
        earnings=EarningsMetrics(
            gross_nominal_earnings_day=_money(snapshot.earnings_cost_metrics["gross_nominal_earnings_day"]),
            realizable_earnings_day=_money(snapshot.earnings_cost_metrics["realizable_earnings_day"]),
            operating_cost_day=_money(snapshot.earnings_cost_metrics["operating_cost_day"]),
            transaction_cost_day=_money(snapshot.earnings_cost_metrics["transaction_cost_day"]),
            other_cost_day=_money(snapshot.earnings_cost_metrics["other_cost_day"]),
            net_earnings_day=_money(snapshot.earnings_cost_metrics["net_earnings_day"]),
        ),
        roi=RoiMetrics(
            break_even=_break_even(snapshot.roi_outputs["break_even"]),
            roi_total_7d=_ratio(snapshot.roi_outputs["roi_total_7d"]),
            roi_total_30d=_ratio(snapshot.roi_outputs["roi_total_30d"]),
            roi_total_90d=_ratio(snapshot.roi_outputs["roi_total_90d"]),
            roi_risk_7d=_ratio(snapshot.roi_outputs["roi_risk_7d"]),
            roi_risk_30d=_ratio(snapshot.roi_outputs["roi_risk_30d"]),
            roi_risk_90d=_ratio(snapshot.roi_outputs["roi_risk_90d"]),
            exit_adjusted_pnl=_money(snapshot.roi_outputs["exit_adjusted_pnl"]),
        ),
        confidence=confidence,
        risk=risk,
        warnings=[WarningPayload(**dict(warning)) for warning in snapshot.warnings],
        freshness=_freshness(snapshot),
        versions=VersionPayload(
            adapter_contract_version=snapshot.adapter_contract_version,
            model_version=snapshot.model_version,
            scoring_methodology_version=scoring_methodology_version,
        ),
        uncertainty_ranges=_uncertainty_ranges(snapshot),
        classification_summary=_classification_summary(snapshot),
    )


def health_payload(*, service: str, environment: str, version: str) -> HealthPayload:
    return HealthPayload(
        status="ok",
        service=service,
        environment=environment,
        version=version,
        api_version="v1",
    )


def ops_status_payload(*, engine: Engine, settings: Settings) -> OpsStatusPayload:
    generated_at = _utc_now()
    database_status = _database_status(engine)
    if database_status["status"] != "ok":
        return OpsStatusPayload(
            status="unhealthy",
            generated_at=generated_at,
            database=database_status,
            scheduler={"cadence_minutes": settings.scheduler_cadence_minutes, "last_successful_run_at": None},
            strategies=[],
            failed_calculation_count=0,
            stale_strategy_count=0,
            provider_errors={},
            application_errors={"available": False, "reason": "Database unavailable; application logs are on the platform."},
        )

    history = HistoryRepository(engine)
    latest_snapshots = {snapshot.strategy_id: snapshot for snapshot in history.latest_snapshots()}
    failures = history.list_failures()
    strategies: list[StrategyOpsStatusPayload] = []
    stale_count = 0
    last_successful_run_at: datetime | None = None
    for strategy in list_strategies():
        snapshot = latest_snapshots.get(strategy.strategy_id)
        freshness_status = None
        if snapshot is not None:
            last_successful_run_at = (
                snapshot.calculated_at
                if last_successful_run_at is None
                else max(last_successful_run_at, snapshot.calculated_at)
            )
            freshness_status = _overall_freshness(
                {key: int(value) for key, value in dict(snapshot.freshness_summary.get("status_counts", {})).items()},
                snapshot=snapshot,
                now=generated_at,
            )
            if freshness_status != "fresh":
                stale_count += 1
        strategies.append(
            StrategyOpsStatusPayload(
                strategy_id=strategy.strategy_id,
                strategy_version=strategy.strategy_version,
                latest_snapshot_id=snapshot.snapshot_id if snapshot is not None else None,
                latest_calculated_at=snapshot.calculated_at if snapshot is not None else None,
                freshness_status=freshness_status,
            )
        )

    return OpsStatusPayload(
        status="ok",
        generated_at=generated_at,
        database=database_status,
        scheduler={
            "cadence_minutes": settings.scheduler_cadence_minutes,
            "last_successful_run_at": last_successful_run_at,
            "last_successful_snapshot_per_strategy": {
                strategy.strategy_id: (
                    latest_snapshots[strategy.strategy_id].calculated_at
                    if strategy.strategy_id in latest_snapshots
                    else None
                )
                for strategy in list_strategies()
            },
        },
        strategies=strategies,
        failed_calculation_count=len(failures),
        stale_strategy_count=stale_count,
        provider_errors=_failure_counts(failures),
        application_errors={
            "available": False,
            "reason": "Application errors are emitted to platform logs; no separate error sink is configured in G13.",
        },
    )


def _database_status(engine: Engine) -> dict[str, Any]:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError as exc:
        return {"status": "error", "detail": str(exc)}
    return {"status": "ok"}


def _failure_counts(failures: Sequence[StrategyCalculationFailure]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for failure in failures:
        counts[failure.error_type] = counts.get(failure.error_type, 0) + 1
    return counts


def _score_payloads(score: SnapshotScoreResult | None) -> tuple[ScorePayload, ScorePayload, str | None]:
    if score is None:
        missing = [
            UnavailableFactorPayload(
                factor="score",
                reason="No persisted risk/confidence score exists for this snapshot and methodology.",
            )
        ]
        return (
            ScorePayload(available=False, unavailable_factors=missing),
            ScorePayload(available=False, unavailable_factors=missing),
            None,
        )
    return (
        ScorePayload(
            available=True,
            score=score.confidence.score,
            label=score.confidence.label.value,
            methodology_version=score.methodology_version,
            contributions=[
                ScoreContributionPayload(
                    factor=contribution.factor,
                    points=contribution.points,
                    reason=contribution.reason,
                    evidence=dict(contribution.evidence),
                )
                for contribution in score.confidence.contributions
            ],
            unavailable_factors=[
                UnavailableFactorPayload(factor=factor.factor, reason=factor.reason)
                for factor in score.confidence.unavailable_factors
            ],
        ),
        ScorePayload(
            available=True,
            score=score.risk.score,
            label=score.risk.label.value,
            methodology_version=score.methodology_version,
            contributions=[
                ScoreContributionPayload(
                    factor=contribution.factor,
                    points=contribution.points,
                    reason=contribution.reason,
                    evidence=dict(contribution.evidence),
                )
                for contribution in score.risk.contributions
            ],
            unavailable_factors=[
                UnavailableFactorPayload(factor=factor.factor, reason=factor.reason)
                for factor in score.risk.unavailable_factors
            ],
        ),
        score.methodology_version,
    )


def _game_summary(game: GameCatalogEntry) -> GameSummary:
    return GameSummary(
        game_id=game.game_id,
        opportunity_id=game.opportunity_id,
        opportunity_type=game.opportunity_type,
        name=game.name,
        chains=list(game.chains),
        economy_types=list(game.economy_types),
        status=game.status,
        strategy_count=len(game.strategy_ids),
        primary_destination=_maybe_outbound_destination(primary_destination_for_opportunity(game.opportunity_id)),
        logo=_logo_payload(get_opportunity(game.opportunity_id)),
    )


def _opportunity_summary(opportunity: OpportunityCatalogEntry) -> OpportunitySummary:
    return OpportunitySummary(
        opportunity_id=opportunity.opportunity_id,
        opportunity_type=opportunity.opportunity_type,
        name=opportunity.name,
        status=opportunity.status,
        platforms=list(opportunity.platforms),
        chains=list(opportunity.chains),
        economy_types=list(opportunity.economy_types),
        reward_asset_or_points_type=list(opportunity.reward_asset_or_points_type),
        value_realization_status=opportunity.value_realization_status,
        data_feasibility_status=opportunity.data_feasibility_status,
        strategy_count=len(opportunity.strategy_ids),
        admission_mode=opportunity.admission_mode,
        legacy_game_id=opportunity.legacy_game_id,
        primary_destination=_maybe_outbound_destination(primary_destination_for_opportunity(opportunity.opportunity_id)),
        roi_unavailable=(
            RoiUnavailablePayload(
                reason=opportunity.roi_unavailable.reason,
                missing_evidence=list(opportunity.roi_unavailable.missing_evidence) if opportunity.roi_unavailable.missing_evidence else None,
                modeling_requirements=list(opportunity.roi_unavailable.modeling_requirements) if opportunity.roi_unavailable.modeling_requirements else None,
            )
            if opportunity.roi_unavailable
            else None
        ),
        logo=_logo_payload(opportunity),
        guidance=(
            OpportunityGuidancePayload(
                how_to_start=list(opportunity.guidance.how_to_start) if opportunity.guidance and opportunity.guidance.how_to_start else None,
                what_you_need=list(opportunity.guidance.what_you_need) if opportunity.guidance and opportunity.guidance.what_you_need else None,
                how_you_earn=list(opportunity.guidance.how_you_earn) if opportunity.guidance and opportunity.guidance.how_you_earn else None,
                how_to_exit_or_claim=list(opportunity.guidance.how_to_exit_or_claim) if opportunity.guidance and opportunity.guidance.how_to_exit_or_claim else None,
            )
            if opportunity.guidance
            else None
        ),
    )


def _opportunity_detail(
    opportunity: OpportunityCatalogEntry,
    *,
    strategies: list[StrategySummary],
) -> OpportunityDetail:
    return OpportunityDetail(
        **_opportunity_summary(opportunity).model_dump(),
        feasibility_summary=opportunity.feasibility_summary,
        official_source_references=[_source_reference(reference) for reference in opportunity.official_source_references],
        outbound_destinations=[
            _outbound_destination(destination)
            for destination in outbound_destinations_for_opportunity(opportunity.opportunity_id)
        ],
        strategies=strategies,
    )


def _maybe_outbound_destination(destination: OutboundDestination | None) -> OutboundDestinationPayload | None:
    if destination is None:
        return None
    return _outbound_destination(destination)


def _logo_payload(opportunity: OpportunityCatalogEntry | None) -> OpportunityLogoPayload | None:
    if opportunity is None or not opportunity.logo_asset or not opportunity.logo_alt:
        return None
    return OpportunityLogoPayload(
        asset=opportunity.logo_asset,
        alt=opportunity.logo_alt,
        source_reference=(
            _source_reference(opportunity.logo_source_reference)
            if opportunity.logo_source_reference
            else None
        ),
    )


def _outbound_destination(destination: OutboundDestination) -> OutboundDestinationPayload:
    return OutboundDestinationPayload(
        destination_id=destination.destination_id,
        destination_slug=destination.destination_slug,
        opportunity_id=destination.opportunity_id,
        opportunity_type=destination.opportunity_type,
        game_id=destination.game_id,
        strategy_id=destination.strategy_id,
        destination_type=destination.destination_type,
        label=destination.label,
        redirect_url=f"/go/{destination.destination_slug}",
        official_url=destination.official_url,
        referral_url=destination.referral_url,
        referral_code=destination.referral_code,
        status=destination.status,
        is_affiliate=destination.is_affiliate,
        affiliate_program=destination.affiliate_program,
        commercial_relationship=destination.commercial_relationship,
        disclosure_text=destination.disclosure_text,
        source_reference=_source_reference(destination.source_reference),
        reviewed_at=destination.reviewed_at,
        verification_status=destination.verification_status,
        allowed_surfaces=list(destination.allowed_surfaces),
        referral_status=destination.referral_status,
    )


def _source_reference(reference: SourceReference) -> SourceReferencePayload:
    return SourceReferencePayload(
        label=reference.label,
        url=reference.url,
        source_role=reference.source_role,
    )


def _money(payload: Any) -> MoneyAmount:
    data = dict(payload)
    return MoneyAmount(amount=str(data["amount"]), currency=str(data["currency"]))


def _ratio(payload: Any) -> RatioMetric:
    data = dict(payload)
    value = data.get("value")
    return RatioMetric(
        value=str(value) if value is not None else None,
        status=str(data["status"]),
        reason=data.get("reason"),
    )


def _break_even(payload: Any) -> BreakEvenMetric:
    data = dict(payload)
    days = data.get("days")
    return BreakEvenMetric(
        basis=str(data["basis"]),
        recovery_target=_money(data["recovery_target"]),
        days=str(days) if days is not None else None,
        status=str(data["status"]),
        reason=data.get("reason"),
    )


def _freshness(snapshot: StrategySnapshot) -> FreshnessPayload:
    counts = {key: int(value) for key, value in dict(snapshot.freshness_summary.get("status_counts", {})).items()}
    return FreshnessPayload(
        overall_status=_overall_freshness(counts, snapshot=snapshot),
        calculated_at=snapshot.calculated_at,
        status_counts=counts,
        input_count=int(snapshot.freshness_summary.get("input_count", len(snapshot.input_observation_ids))),
        oldest_retrieved_at=_parse_datetime(snapshot.freshness_summary.get("oldest_retrieved_at")),
        newest_retrieved_at=_parse_datetime(snapshot.freshness_summary.get("newest_retrieved_at")),
        earliest_fresh_until=_parse_datetime(snapshot.freshness_summary.get("earliest_fresh_until")),
    )


def _uncertainty_ranges(snapshot: StrategySnapshot) -> list[UncertaintyRangePayload]:
    ranges: list[UncertaintyRangePayload] = []
    for metric, payload in sorted(dict(snapshot.uncertainty_ranges).items()):
        data = dict(payload)
        values = {
            name: str(snapshot.adapter_derived_values.get(str(data.get(name))))
            if snapshot.adapter_derived_values.get(str(data.get(name))) is not None
            else None
            for name in ("low_metric", "base_metric", "high_metric")
        }
        ranges.append(
            UncertaintyRangePayload(
                metric=str(data.get("metric", metric)),
                low_metric=str(data["low_metric"]),
                base_metric=str(data["base_metric"]),
                high_metric=str(data["high_metric"]),
                unit=data.get("unit"),
                description=data.get("description"),
                values=values,
            )
        )
    return ranges


def _classification_summary(snapshot: StrategySnapshot) -> ClassificationSummaryPayload:
    summary = dict(snapshot.classification_summary)
    counts = {key: int(value) for key, value in dict(summary.get("counts", {})).items()}
    metrics = {str(key): str(value) for key, value in dict(summary.get("metrics", {})).items()}
    return ClassificationSummaryPayload(counts=counts, metrics=metrics)


def _overall_freshness(
    counts: dict[str, int],
    *,
    snapshot: StrategySnapshot | None = None,
    now: datetime | None = None,
) -> str:
    if counts.get("invalid", 0) > 0:
        return "invalid"
    if counts.get("missing", 0) > 0:
        return "missing"
    if counts.get("stale", 0) > 0:
        return "stale"
    if snapshot is not None and _snapshot_deadline_has_passed(snapshot, now=now):
        return "stale"
    return "fresh"


def _snapshot_deadline_has_passed(snapshot: StrategySnapshot, *, now: datetime | None = None) -> bool:
    deadline = _parse_datetime(snapshot.freshness_summary.get("earliest_fresh_until"))
    if deadline is None:
        return False
    return (now or _utc_now()) > deadline


def _passes_filters(
    *,
    strategy: StrategyCatalogEntry,
    snapshot: StrategySnapshot,
    score: SnapshotScoreResult | None,
    capital_min: Decimal | None,
    capital_max: Decimal | None,
    confidence_min: int | None,
    risk_max: int | None,
    game_id: str | None,
    opportunity_id: str | None,
    opportunity_type: str | None,
    chain: str | None,
    economy_type: str | None,
) -> bool:
    capital = _decimal_from_money(snapshot.capital_metrics["total_capital"])
    if capital_min is not None and capital < capital_min:
        return False
    if capital_max is not None and capital > capital_max:
        return False
    if confidence_min is not None and (score is None or score.confidence.score < confidence_min):
        return False
    if risk_max is not None and (score is None or score.risk.score > risk_max):
        return False
    if game_id is not None and strategy.game_id != game_id:
        return False
    if opportunity_id is not None and strategy.opportunity_id != opportunity_id:
        return False
    if opportunity_type is not None and strategy.opportunity_type != opportunity_type:
        return False
    if chain is not None and strategy.chain != chain:
        return False
    return economy_type is None or strategy.economy_type == economy_type


def _ranking_sort_key(row: tuple[StrategyCatalogEntry, StrategySnapshot, SnapshotScoreResult | None]):
    strategy, snapshot, score = row
    roi_30d = _decimal_or_floor(snapshot.roi_outputs["roi_total_30d"].get("value"))
    confidence = score.confidence.score if score is not None else -1
    risk = score.risk.score if score is not None else 101
    return (
        -roi_30d,
        -confidence,
        risk,
        -snapshot.calculated_at.timestamp(),
        strategy.strategy_id,
    )


def _decimal_from_money(payload: Any) -> Decimal:
    return Decimal(str(dict(payload)["amount"]))


def _decimal_or_floor(value: Any) -> Decimal:
    if value is None:
        return Decimal("-Infinity")
    return Decimal(str(value))


def _paginate(items: Sequence, *, limit: int, offset: int) -> list:
    return list(items[offset : offset + limit])


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _normalize_utc(value)
    return _normalize_utc(datetime.fromisoformat(str(value)))


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)
