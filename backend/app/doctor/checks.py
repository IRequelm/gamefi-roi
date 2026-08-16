"""Local environment doctor checks."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config.runtime import current_runtime_status
from app.config.settings import Settings, get_settings
from app.storage.database import check_connectivity

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
REQUIRED_IMPORTS = (
    "app",
    "app.api.app",
    "app.api.dependencies",
    "app.api.v1.routes",
    "app.api.v1.schemas",
    "app.api.v1.service",
    "app.api.v1_probe",
    "app.config.settings",
    "app.storage.database",
    "app.storage.history",
    "app.storage.metadata",
    "app.storage.models",
    "app.storage.models.scoring",
    "app.storage.models.strategy_history",
    "app.storage.observations",
    "app.storage.scoring",
    "app.engine.decimal_context",
    "app.engine.calculator",
    "app.engine.inputs",
    "app.engine.money",
    "app.engine.results",
    "app.adapters.contract",
    "app.adapters.defi_kingdoms_jeweler",
    "app.adapters.defi_kingdoms_jeweler_probe",
    "app.adapters.farmers_world",
    "app.adapters.farmers_world_probe",
    "app.adapters.splinterlands",
    "app.adapters.splinterlands_probe",
    "app.sources.alcor",
    "app.sources.atomicassets",
    "app.sources.coingecko",
    "app.sources.amm",
    "app.sources.evm",
    "app.sources.http",
    "app.sources.market_data",
    "app.sources.observations",
    "app.sources.splinterlands",
    "app.strategies.defi_kingdoms",
    "app.strategies.farmers_world",
    "app.strategies.splinterlands",
    "app.strategies.catalog",
    "app.jobs.recalculation",
    "app.jobs.history_probe",
    "app.risk.results",
    "app.risk.scoring",
    "app.risk.scoring_probe",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def build_alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def check_runtime() -> CheckResult:
    status = current_runtime_status()
    if status.supported:
        return CheckResult(
            name="runtime",
            ok=True,
            detail=f"Python {status.version} satisfies {status.requirement}",
        )
    return CheckResult(
        name="runtime",
        ok=False,
        detail=f"Python {status.version} does not satisfy {status.requirement}",
    )


def check_config(settings_loader: Callable[[], Settings] = get_settings) -> tuple[CheckResult, Settings | None]:
    try:
        settings = settings_loader()
    except (ValidationError, ValueError) as exc:
        return (
            CheckResult(
                name="config",
                ok=False,
                detail=f"Configuration invalid: {exc}",
            ),
            None,
        )

    return (
        CheckResult(
            name="config",
            ok=True,
            detail=f"{settings.environment} configuration loaded for {settings.database_backend}",
        ),
        settings,
    )


def check_imports() -> CheckResult:
    missing: list[str] = []
    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            missing.append(f"{module_name}: {exc}")

    if missing:
        return CheckResult(name="imports", ok=False, detail="; ".join(missing))
    return CheckResult(name="imports", ok=True, detail="Backend package imports successfully")


def check_market_source_config(settings: Settings | None) -> CheckResult:
    if settings is None:
        return CheckResult(name="market-source-config", ok=False, detail="Skipped because configuration failed")

    return CheckResult(
        name="market-source-config",
        ok=True,
        detail=(
            "Market source config loaded "
            f"(timeout={settings.market_data_http_timeout_seconds}s, "
            f"retries={settings.market_data_http_max_retries}, "
            f"price_freshness={settings.market_data_price_freshness_seconds}s)"
        ),
    )


def check_adapter_source_config(settings: Settings | None) -> CheckResult:
    if settings is None:
        return CheckResult(name="adapter-source-config", ok=False, detail="Skipped because configuration failed")

    return CheckResult(
        name="adapter-source-config",
        ok=True,
        detail=(
            "Adapter source config loaded "
            f"(dfk_rpc_configured={bool(settings.dfk_chain_rpc_url)}, "
            f"dfk_freshness={settings.dfk_chain_observation_freshness_seconds}s, "
            f"alcor_configured={bool(settings.alcor_base_url)}, "
            f"atomicassets_configured={bool(settings.atomicassets_base_url)}, "
            f"wax_market_freshness={settings.wax_market_observation_freshness_seconds}s, "
            f"splinterlands_configured={bool(settings.splinterlands_base_url)}, "
            f"splinterlands_freshness={settings.splinterlands_observation_freshness_seconds}s)"
        ),
    )


def check_database(settings: Settings | None) -> tuple[CheckResult, Engine | None]:
    if settings is None:
        return CheckResult(name="database", ok=False, detail="Skipped because configuration failed"), None

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        check_connectivity(engine)
    except SQLAlchemyError as exc:
        engine.dispose()
        return CheckResult(name="database", ok=False, detail=f"Database check failed: {exc}"), None

    return CheckResult(name="database", ok=True, detail="Database connectivity verified"), engine


def check_migrations(settings: Settings | None, engine: Engine | None) -> CheckResult:
    if settings is None or engine is None:
        return CheckResult(name="migrations", ok=False, detail="Skipped because database check failed")

    try:
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        heads = set(script.get_heads())
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_heads = set(context.get_current_heads())
    except Exception as exc:  # Alembic can raise several config/runtime exceptions.
        return CheckResult(name="migrations", ok=False, detail=f"Migration check failed: {exc}")

    if current_heads == heads:
        return CheckResult(name="migrations", ok=True, detail=f"Database at head {', '.join(sorted(heads))}")

    current_display = ", ".join(sorted(current_heads)) if current_heads else "none"
    head_display = ", ".join(sorted(heads)) if heads else "none"
    return CheckResult(
        name="migrations",
        ok=False,
        detail=f"Database revision {current_display}; expected {head_display}",
    )


def run_all_checks(settings_loader: Callable[[], Settings] = get_settings) -> list[CheckResult]:
    results: list[CheckResult] = [check_runtime()]

    config_result, settings = check_config(settings_loader)
    results.append(config_result)
    results.append(check_imports())
    results.append(check_market_source_config(settings))
    results.append(check_adapter_source_config(settings))

    database_result, engine = check_database(settings)
    results.append(database_result)
    try:
        results.append(check_migrations(settings, engine))
    finally:
        if engine is not None:
            engine.dispose()

    return results


def main() -> int:
    results = run_all_checks()
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
    return 0 if all(result.ok for result in results) else 1
