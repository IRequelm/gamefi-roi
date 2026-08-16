"""Read-only API service over catalog, history, and scores."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine

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
    PageMeta,
    RankingItem,
    RankingsPage,
    RatioMetric,
    RoiMetrics,
    ScoreContributionPayload,
    ScorePayload,
    StrategiesPage,
    StrategySnapshotPayload,
    StrategySummary,
    UnavailableFactorPayload,
    UncertaintyRangePayload,
    VersionPayload,
    WarningPayload,
)
from app.risk.results import METHODOLOGY_VERSION, SnapshotScoreResult
from app.storage.history import HistoryRepository, StrategySnapshot
from app.storage.scoring import ScoringRepository
from app.strategies.catalog import GameCatalogEntry, StrategyCatalogEntry, get_game, get_strategy, list_games, list_strategies

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
        self.scoring = ScoringRepository(engine)

    def games_page(self, *, limit: int, offset: int) -> tuple[list[GameSummary], int]:
        games = list(list_games())
        page = _paginate(games, limit=limit, offset=offset)
        return [_game_summary(game) for game in page], len(games)

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
        )

    def strategies_page(
        self,
        *,
        limit: int,
        offset: int,
        game_id: str | None = None,
        chain: str | None = None,
        economy_type: str | None = None,
    ) -> tuple[list[StrategySummary], int]:
        strategies = [
            strategy
            for strategy in list_strategies()
            if (game_id is None or strategy.game_id == game_id)
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
            game_id=strategy.game_id,
            game_name=strategy.game_name,
            name=strategy.name,
            chain=strategy.chain,
            economy_type=strategy.economy_type,
            description=strategy.description,
            latest_snapshot=latest,
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
        name=game.name,
        chains=list(game.chains),
        economy_types=list(game.economy_types),
        status=game.status,
        strategy_count=len(game.strategy_ids),
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
        overall_status=_overall_freshness(counts),
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


def _overall_freshness(counts: dict[str, int]) -> str:
    if counts.get("invalid", 0) > 0:
        return "invalid"
    if counts.get("missing", 0) > 0:
        return "missing"
    if counts.get("stale", 0) > 0:
        return "stale"
    return "fresh"


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
