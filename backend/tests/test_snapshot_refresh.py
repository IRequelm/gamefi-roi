from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

from app.adapters.scenario_yield import ScenarioYieldAdapter
from app.config.settings import Settings
from app.distribution.content_pack import (
    ContentFactSet,
    ContentPackLite,
    ContentReadiness,
    ContentSource,
    DistributionLinks,
    EditorialContent,
    MetricFact,
    set_expected_source_hash,
    validate_pack,
)
from app.jobs import snapshot_refresh
from app.jobs.production_recalculation import run_recalculation_tasks
from app.jobs.recalculation import StrategyCalculationTask
from app.jobs.snapshot_refresh import Refreshability, run_snapshot_refresh
from app.adapters.scenario_yield_probe import (
    CONFIG_EVIDENCE_ESTABLISHED_AT,
    _market_price_observation,
    build_scenario_observations,
    load_fixture_observations,
)
from app.adapters.splinterlands import SplinterlandsModernRankedAdapter
from app.adapters.splinterlands_probe import _build_probe_observations
from app.sources.coingecko import CoinGeckoMarketDataSource
from app.sources.market_data import TokenPriceRequest
from app.sources.splinterlands import (
    SETTINGS_SEASON_ID,
    SplinterlandsGameDataSource,
    SplinterlandsSeasonRequest,
    SplinterlandsSettingsRequest,
)
from app.storage.history import HistoryRepository
from app.strategies.scenario_yield import DIMO_SOFTWARE_ONLY_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from test_history_storage import _migrated_engine


def test_dry_run_classifies_existing_production_tasks_without_provider_calls(monkeypatch) -> None:
    settings = _test_settings()
    tasks = tuple(snapshot_refresh.build_production_tasks(settings))
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: (_ for _ in ()).throw(AssertionError()))

    result = run_snapshot_refresh(settings=settings, dry_run=True)

    assert result.mode == "dry-run"
    assert result.refreshed_count == 0
    assert result.failed_count == 0
    assert result.skipped_count == 5
    assert result.partial_skipped == 4
    assert result.not_refreshable_skipped == 1
    assert len(result.refreshability) == len(tasks)
    assert sum(entry.refreshability == Refreshability.AUTO_REFRESHABLE for entry in result.refreshability) == 10
    assert sum(entry.refreshability == Refreshability.PARTIAL_REFRESH_ONLY for entry in result.refreshability) == 4
    assert sum(entry.refreshability == Refreshability.NOT_REFRESHABLE for entry in result.refreshability) == 1


def test_dry_run_can_quarantine_unavailable_dfk_jeweler_refresh() -> None:
    settings = _test_settings()
    tasks = tuple(snapshot_refresh.build_production_tasks(settings))

    result = run_snapshot_refresh(
        settings=settings.model_copy(update={"dfk_jeweler_refresh_enabled": False}),
        dry_run=True,
    )

    assert result.eligible_count == 7
    assert result.skipped_count == 8
    assert result.not_refreshable_skipped == 4
    by_id = {entry.strategy_id: entry for entry in result.refreshability}
    assert by_id["dfk-crystalvale-jeweler-cjewel-max-lock"].refreshability is Refreshability.NOT_REFRESHABLE
    assert "positive current cJEWEL balance" in by_id["dfk-crystalvale-jeweler-cjewel-max-lock"].reason


def test_config_observations_keep_stable_source_identity_across_recalculation_times() -> None:
    first = load_fixture_observations(
        CONFIG_EVIDENCE_ESTABLISHED_AT,
        strategy=DIMO_SOFTWARE_ONLY_V1,
    )
    later = load_fixture_observations(
        CONFIG_EVIDENCE_ESTABLISHED_AT.replace(day=31),
        strategy=DIMO_SOFTWARE_ONLY_V1,
    )

    first_config = {observation.metric: observation for observation in first if observation.metadata.get("classification") == "CONFIG"}
    later_config = {observation.metric: observation for observation in later if observation.metadata.get("classification") == "CONFIG"}
    assert first_config.keys() == later_config.keys()
    for metric in first_config:
        assert later_config[metric].observation_id == first_config[metric].observation_id
        assert later_config[metric].observed_at == CONFIG_EVIDENCE_ESTABLISHED_AT
        assert later_config[metric].fresh_until == first_config[metric].fresh_until


def test_partial_and_not_refreshable_strategies_are_never_eligible_for_refresh(monkeypatch) -> None:
    settings = _test_settings()
    tasks = tuple(snapshot_refresh.build_production_tasks(settings))
    plan = snapshot_refresh.build_refresh_plan(tasks)
    by_id = {entry.strategy_id: entry for entry in plan}
    assert by_id["geodnet-empty-hex-triple-band-base-station"].refreshability is Refreshability.PARTIAL_REFRESH_ONLY
    assert by_id["storj-existing-hardware-storage-node"].refreshability is Refreshability.NOT_REFRESHABLE


def test_recalculation_time_cannot_renew_stale_config_evidence() -> None:
    observations = load_fixture_observations(
        CONFIG_EVIDENCE_ESTABLISHED_AT.replace(year=2027, month=9, day=1),
        strategy=DIMO_SOFTWARE_ONLY_V1,
    )
    config_observation = next(
        observation for observation in observations if observation.metadata.get("classification") == "CONFIG"
    )
    assert config_observation.status_at(CONFIG_EVIDENCE_ESTABLISHED_AT.replace(year=2027, month=9, day=1)).value == "stale"


def test_refresh_plan_requires_explicit_registration_for_unknown_adapter() -> None:
    class UnknownAdapter:
        __module__ = "app.adapters.unknown"

    class Task:
        strategy_id = "unknown-strategy"
        strategy_version = "v1"
        adapter = UnknownAdapter()

    entry = snapshot_refresh.build_refresh_plan((Task(),))[0]
    assert entry.refreshability is Refreshability.NOT_REFRESHABLE
    assert "No approved production refreshability classification" in entry.reason


def test_refresh_summary_separates_refresh_and_skip_categories(monkeypatch) -> None:
    class SuccessfulSummary:
        status = "ok"
        snapshot_ids = ("snapshot-1",)
        failure_ids = ()

    monkeypatch.setattr(snapshot_refresh, "_database_engine", lambda settings: _DisposableEngine())
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: SuccessfulSummary())
    result = run_snapshot_refresh(settings=_test_settings())
    assert result.auto_refreshed == 1
    assert result.partial_skipped == 4
    assert result.not_refreshable_skipped == 1
    assert result.failed == 0


def test_refresh_does_not_regenerate_distribution_after_strategy_failure(monkeypatch, tmp_path: Path) -> None:
    class FailedSummary:
        status = "ok"
        snapshot_ids = ("snapshot-1",)
        failure_ids = ("failure-1",)

    monkeypatch.setattr(snapshot_refresh, "_database_engine", lambda settings: _DisposableEngine())
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: FailedSummary())
    monkeypatch.setattr(snapshot_refresh, "_fetch_json", lambda url: (_ for _ in ()).throw(AssertionError()))

    result = run_snapshot_refresh(settings=_test_settings(), regenerate_distribution=True, distribution_output=tmp_path / "batch.json")

    assert result.refreshed_count == 1
    assert result.failed_count == 1
    assert result.distribution_regenerated is False
    assert not (tmp_path / "batch.json").exists()


def test_refresh_regenerates_distribution_only_after_zero_failure_refresh(monkeypatch, tmp_path: Path) -> None:
    class SuccessfulSummary:
        status = "ok"
        snapshot_ids = ("snapshot-1",)
        failure_ids = ()

    monkeypatch.setattr(snapshot_refresh, "_database_engine", lambda settings: _DisposableEngine())
    monkeypatch.setattr(snapshot_refresh, "run_recalculation_tasks", lambda **kwargs: SuccessfulSummary())
    monkeypatch.setattr(snapshot_refresh, "_fetch_json", lambda url: {"items": [], "page": {"total": 0}})
    monkeypatch.setattr(snapshot_refresh, "build_learning_batch", lambda *args, **kwargs: [])

    result = run_snapshot_refresh(settings=_test_settings(), regenerate_distribution=True, distribution_output=tmp_path / "batch.json")

    assert result.distribution_regenerated is True
    assert (tmp_path / "batch.json").exists()


def test_auto_provider_to_snapshot_to_distribution_can_qualify(monkeypatch, tmp_path: Path) -> None:
    active_time = datetime.now(UTC).replace(microsecond=0)
    settings = _provider_test_settings()

    def game_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/settings":
            return httpx.Response(
                200,
                json={
                    "starter_pack_price": 10,
                    "sps_price": 0.003,
                    "config_version": 208,
                    "timestamp": int(active_time.timestamp() * 1000),
                    "season": {"id": 189, "name": "Season", "ends": (active_time + timedelta(days=1)).isoformat()},
                    "energy": {"max_energy": 50, "hourly_regen_rate": 1},
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={"id": 189, "ends": (active_time + timedelta(days=1)).isoformat(), "reset_block_num": None},
            request=request,
        )

    def price_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=f'{{"splinterlands":{{"usd":0.003,"last_updated_at":{int(active_time.timestamp())}}}}}',
            request=request,
        )

    game_source = SplinterlandsGameDataSource(settings, transport=httpx.MockTransport(game_handler))
    price_source = CoinGeckoMarketDataSource(settings, transport=httpx.MockTransport(price_handler))
    try:
        settings_observations = game_source.get_settings(SplinterlandsSettingsRequest(freshness_window=timedelta(minutes=5)))
        season_id = next(observation for observation in settings_observations if observation.metric == SETTINGS_SEASON_ID)
        season_observations = game_source.get_season(
            SplinterlandsSeasonRequest(season_id=str(season_id.value), freshness_window=timedelta(minutes=5))
        )
        price_observations = tuple(
            price_source.get_token_prices(
                TokenPriceRequest(
                    provider_asset_ids=(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.reward_coingecko_asset_id,),
                    quote_currency="USD",
                    freshness_window=timedelta(minutes=5),
                )
            )
        )
    finally:
        game_source.close()
        price_source.close()

    observations = _build_probe_observations(
        strategy=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1,
        settings_observations=settings_observations,
        season_observations=season_observations,
        sps_price=price_observations,
        retrieved_at=active_time,
    )
    engine = _migrated_engine(monkeypatch, tmp_path, "refresh-auto-integration.db")
    task = StrategyCalculationTask(
        strategy_id=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_id,
        strategy_version=SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.strategy_version,
        adapter=SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1),
        load_observations=lambda _: observations,
    )
    summary = run_recalculation_tasks(engine=engine, tasks=(task,), calculated_at=active_time, cadence_minutes=30)
    snapshot = HistoryRepository(engine).latest_snapshot(task.strategy_id)

    assert len(summary.snapshot_ids) == 1
    assert snapshot is not None
    pack = _snapshot_pack(snapshot, Refreshability.AUTO_REFRESHABLE)
    assert validate_pack(pack).readiness is ContentReadiness.GREEN


def test_mixed_live_config_recent_snapshot_remains_distribution_red(monkeypatch, tmp_path: Path) -> None:
    active_time = datetime.now(UTC).replace(microsecond=0)
    settings = _provider_test_settings()

    def price_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=f'{{"dimo":{{"usd":0.08,"last_updated_at":{int(active_time.timestamp())}}}}}',
            request=request,
        )

    source = CoinGeckoMarketDataSource(settings, transport=httpx.MockTransport(price_handler))
    try:
        raw_price = source.get_token_prices(
            TokenPriceRequest(
                provider_asset_ids=("dimo",),
                quote_currency="USD",
                freshness_window=timedelta(minutes=5),
            )
        )[0]
    finally:
        source.close()
    observations = build_scenario_observations(
        active_time,
        strategy=DIMO_SOFTWARE_ONLY_V1,
        price_observation=_market_price_observation(DIMO_SOFTWARE_ONLY_V1, raw_price),
    )
    engine = _migrated_engine(monkeypatch, tmp_path, "refresh-partial-integration.db")
    task = StrategyCalculationTask(
        strategy_id=DIMO_SOFTWARE_ONLY_V1.strategy_id,
        strategy_version=DIMO_SOFTWARE_ONLY_V1.strategy_version,
        adapter=ScenarioYieldAdapter(DIMO_SOFTWARE_ONLY_V1),
        load_observations=lambda _: observations,
    )
    summary = run_recalculation_tasks(engine=engine, tasks=(task,), calculated_at=active_time, cadence_minutes=30)
    snapshot = HistoryRepository(engine).latest_snapshot(task.strategy_id)

    assert len(summary.snapshot_ids) == 1
    assert snapshot is not None
    assert any(reference["metadata"].get("classification") == "CONFIG" for reference in snapshot.input_observation_references.values())
    pack = _snapshot_pack(snapshot, Refreshability.PARTIAL_REFRESH_ONLY)
    validation = validate_pack(pack)
    assert validation.readiness is ContentReadiness.RED
    assert "refreshability: PARTIAL_REFRESH_ONLY" in " ".join(validation.warnings)


def test_provider_failure_creates_no_snapshot_or_publishable_distribution_basis(monkeypatch, tmp_path: Path) -> None:
    active_time = datetime.now(UTC).replace(microsecond=0)
    settings = _provider_test_settings()

    def failing_price_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "provider unavailable"}, request=request)

    source = CoinGeckoMarketDataSource(settings, transport=httpx.MockTransport(failing_price_handler))

    def load_observations(_):
        raw_price = source.get_token_prices(
            TokenPriceRequest(
                provider_asset_ids=("dimo",),
                quote_currency="USD",
                freshness_window=timedelta(minutes=5),
            )
        )[0]
        return build_scenario_observations(
            active_time,
            strategy=DIMO_SOFTWARE_ONLY_V1,
            price_observation=_market_price_observation(DIMO_SOFTWARE_ONLY_V1, raw_price),
        )

    engine = _migrated_engine(monkeypatch, tmp_path, "refresh-provider-failure.db")
    task = StrategyCalculationTask(
        strategy_id=DIMO_SOFTWARE_ONLY_V1.strategy_id,
        strategy_version=DIMO_SOFTWARE_ONLY_V1.strategy_version,
        adapter=ScenarioYieldAdapter(DIMO_SOFTWARE_ONLY_V1),
        load_observations=load_observations,
    )
    try:
        summary = run_recalculation_tasks(engine=engine, tasks=(task,), calculated_at=active_time, cadence_minutes=30)
    finally:
        source.close()

    assert summary.snapshot_ids == ()
    assert len(summary.failure_ids) == 1
    assert HistoryRepository(engine).latest_snapshot(task.strategy_id) is None


class _DisposableEngine:
    def dispose(self) -> None:
        pass


def _test_settings() -> Settings:
    return Settings(database_url="sqlite+pysqlite:///:memory:", environment="test", allow_sqlite_for_tests=True)


def _provider_test_settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        environment="test",
        allow_sqlite_for_tests=True,
        coingecko_base_url="https://market.provider.example/api/v3",
        splinterlands_base_url="https://game.provider.example",
        market_data_http_max_retries=0,
    )


def _snapshot_pack(snapshot, refreshability: Refreshability) -> ContentPackLite:
    pack = ContentPackLite(
        content_id=f"integration-{snapshot.strategy_id}",
        source=ContentSource(
            opportunity_id=snapshot.strategy_id,
            strategy_id=snapshot.strategy_id,
            snapshot_id=snapshot.snapshot_id,
            snapshot_timestamp=snapshot.calculated_at.isoformat(),
            source_snapshot_hash="",
            strategy_version=snapshot.strategy_version,
            adapter_contract_version=snapshot.adapter_contract_version,
            model_version=snapshot.model_version,
            refreshability=refreshability,
        ),
        facts=ContentFactSet(
            project_name=snapshot.strategy_id,
            opportunity_type="TEST",
            capital=MetricFact(
                value=str(snapshot.capital_metrics["total_capital"]["amount"]),
                unit="USD",
                display="available",
                source_path="snapshot.capital.total_capital.amount",
            ),
            freshness=MetricFact(
                value="fresh",
                display="fresh",
                source_path="snapshot.freshness.overall_status",
            ),
            reward_source="Controlled authoritative provider response.",
            major_catch="Integration test only.",
        ),
        editorial=EditorialContent(
            content_angle="integration",
            readiness=(ContentReadiness.GREEN if refreshability is Refreshability.AUTO_REFRESHABLE else ContentReadiness.RED),
            hook="Provider-backed snapshot test.",
            core_message="Publication readiness follows authoritative refreshability.",
            x_post="Provider-backed snapshot test.",
            disclosure="Test artifact.",
        ),
        distribution=DistributionLinks(
            canonical_site_url=f"https://gamcryp.com/strategies/{snapshot.strategy_id}",
            content_id=f"integration-{snapshot.strategy_id}",
            x_utm_url=f"https://gamcryp.com/strategies/{snapshot.strategy_id}?utm_source=x",
            youtube_utm_url=f"https://gamcryp.com/strategies/{snapshot.strategy_id}?utm_source=youtube",
        ),
        created_at=snapshot.calculated_at.isoformat(),
    )
    return set_expected_source_hash(pack)
