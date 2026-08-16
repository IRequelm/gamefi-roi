"""Read-oriented product API v1 routes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Engine

from app import __version__
from app.api.dependencies import get_database_engine
from app.api.v1.schemas import (
    GameDetail,
    GamesPage,
    HealthPayload,
    HistoryPage,
    RankingsPage,
    StrategiesPage,
    StrategySnapshotPayload,
    StrategySummary,
)
from app.api.v1.service import ApiDataService, health_payload
from app.config.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["api-v1"])

Limit = Annotated[int, Query(ge=1, le=100, description="Maximum number of items to return.")]
Offset = Annotated[int, Query(ge=0, description="Number of items to skip.")]
CapitalFilter = Annotated[Decimal | None, Query(ge=0, description="USD capital filter; parsed as Decimal.")]
ScoreFilter = Annotated[int | None, Query(ge=0, le=100)]


@router.get(
    "/health",
    response_model=HealthPayload,
    summary="API v1 health",
    description="Returns API version and service health without touching external providers.",
)
def health_v1(settings: Settings = Depends(get_settings)) -> HealthPayload:
    return health_payload(service=settings.api_title, environment=settings.environment, version=__version__)


@router.get(
    "/games",
    response_model=GamesPage,
    summary="List modeled games",
    description="Returns catalog games currently modeled by completed adapters.",
)
def list_games(limit: Limit = 50, offset: Offset = 0, engine: Engine = Depends(get_database_engine)) -> GamesPage:
    items, total = ApiDataService(engine).games_page(limit=limit, offset=offset)
    return GamesPage(items=items, page={"limit": limit, "offset": offset, "total": total})


@router.get(
    "/games/{game_id}",
    response_model=GameDetail,
    summary="Get modeled game",
    description="Returns a game catalog entry and its modeled strategies.",
)
def get_game(game_id: str, engine: Engine = Depends(get_database_engine)) -> GameDetail:
    detail = ApiDataService(engine).game_detail(game_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown game_id: {game_id}")
    return detail


@router.get(
    "/strategies",
    response_model=StrategiesPage,
    summary="List modeled strategies",
    description="Returns versioned strategy catalog entries with latest persisted snapshot when available.",
)
def list_strategies(
    limit: Limit = 50,
    offset: Offset = 0,
    game_id: str | None = Query(None, description="Filter by modeled game id."),
    chain: str | None = Query(None, description="Filter by modeled chain."),
    economy_type: str | None = Query(None, description="Filter by modeled economy type."),
    engine: Engine = Depends(get_database_engine),
) -> StrategiesPage:
    items, total = ApiDataService(engine).strategies_page(
        limit=limit,
        offset=offset,
        game_id=game_id,
        chain=chain,
        economy_type=economy_type,
    )
    return StrategiesPage(items=items, page={"limit": limit, "offset": offset, "total": total})


@router.get(
    "/strategies/{strategy_id}",
    response_model=StrategySummary,
    summary="Get modeled strategy",
    description="Returns strategy metadata and latest persisted snapshot when available.",
)
def get_strategy(strategy_id: str, engine: Engine = Depends(get_database_engine)) -> StrategySummary:
    strategy = ApiDataService(engine).strategy_detail(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Unknown strategy_id: {strategy_id}")
    return strategy


@router.get(
    "/strategies/{strategy_id}/latest",
    response_model=StrategySnapshotPayload,
    summary="Get latest strategy snapshot",
    description="Reads the latest successful persisted snapshot and its persisted risk/confidence score.",
)
def get_latest_strategy_snapshot(
    strategy_id: str,
    engine: Engine = Depends(get_database_engine),
) -> StrategySnapshotPayload:
    snapshot = ApiDataService(engine).latest_snapshot(strategy_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No latest snapshot for strategy_id: {strategy_id}")
    return snapshot


@router.get(
    "/strategies/{strategy_id}/history",
    response_model=HistoryPage,
    summary="Get strategy history",
    description="Returns successful persisted snapshots in ascending calculated_at order.",
)
def get_strategy_history(
    strategy_id: str,
    limit: Limit = 50,
    offset: Offset = 0,
    start_at: datetime | None = Query(None, description="Inclusive UTC lower bound for calculated_at."),
    end_at: datetime | None = Query(None, description="Inclusive UTC upper bound for calculated_at."),
    engine: Engine = Depends(get_database_engine),
) -> HistoryPage:
    if start_at is not None and end_at is not None and end_at < start_at:
        raise HTTPException(status_code=422, detail="end_at must be greater than or equal to start_at")
    page = ApiDataService(engine).history_page(
        strategy_id,
        limit=limit,
        offset=offset,
        start_at=start_at,
        end_at=end_at,
    )
    if page is None:
        raise HTTPException(status_code=404, detail=f"Unknown strategy_id: {strategy_id}")
    return page


@router.get(
    "/rankings",
    response_model=RankingsPage,
    summary="List strategy rankings",
    description=(
        "Ranks latest successful persisted snapshots by 30-day ROI descending, then confidence descending, "
        "risk ascending, latest calculation time descending, and strategy id ascending."
    ),
)
def get_rankings(
    limit: Limit = 50,
    offset: Offset = 0,
    capital_min: CapitalFilter = None,
    capital_max: CapitalFilter = None,
    confidence_min: ScoreFilter = None,
    risk_max: ScoreFilter = None,
    game_id: str | None = Query(None, description="Filter by modeled game id."),
    chain: str | None = Query(None, description="Filter by modeled chain."),
    economy_type: str | None = Query(None, description="Filter by modeled economy type."),
    engine: Engine = Depends(get_database_engine),
) -> RankingsPage:
    if capital_min is not None and capital_max is not None and capital_min > capital_max:
        raise HTTPException(status_code=422, detail="capital_min must be less than or equal to capital_max")
    return ApiDataService(engine).rankings_page(
        limit=limit,
        offset=offset,
        capital_min=capital_min,
        capital_max=capital_max,
        confidence_min=confidence_min,
        risk_max=risk_max,
        game_id=game_id,
        chain=chain,
        economy_type=economy_type,
    )
