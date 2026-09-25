from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_default_render_blueprint_uses_free_beta_resources_without_cron() -> None:
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "plan: free" in blueprint
    assert "name: gamefi-roi-web" in blueprint
    assert "name: gamefi-roi-db" in blueprint
    assert 'name: gamefi-roi-db\n    plan: basic-256mb' in blueprint
    assert "type: cron" not in blueprint
    assert "name: gamefi-roi-recalculation" not in blueprint
    assert "preDeployCommand" not in blueprint
    assert "python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn app.main:app" in blueprint
    assert "GAMEFI_COINGECKO_API_KEY" in blueprint
    assert "GAMEFI_DFK_CHAIN_RPC_URL" in blueprint
    assert "sync: false" in blueprint


def test_paid_render_blueprint_preserves_production_cron_and_paid_database() -> None:
    blueprint = (ROOT / "render.production.yaml").read_text(encoding="utf-8")

    assert "type: cron" in blueprint
    assert "name: gamefi-roi-recalculation" in blueprint
    assert "plan: basic-256mb" in blueprint
    assert "schedule: \"2-57/5 * * * *\"" in blueprint
    assert "preDeployCommand" in blueprint
    assert "python -m app.jobs.snapshot_refresh" in blueprint
    assert "python -m app.jobs.production_recalculation" not in blueprint


def test_beta_scheduler_workflow_uses_policy_aware_snapshot_refresh_with_overlap_guard() -> None:
    workflow = (ROOT / ".github/workflows/render-beta-recalculation.yml").read_text(encoding="utf-8")
    beta_blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert 'cron: "17 */4 * * *"' in workflow
    assert "cancel-in-progress: false" in workflow
    assert "vars.GAMEFI_BETA_DATABASE_ENABLED == 'true'" in workflow
    assert "GAMEFI_BETA_DATABASE_URL" in workflow
    assert "GAMEFI_PUBLIC_BASE_URL" in workflow
    assert "vars.GAMEFI_PUBLIC_BASE_URL" in workflow
    assert "https://gamcryp.com" in workflow
    assert "GAMEFI_COINGECKO_API_KEY" in workflow
    assert "GAMEFI_DFK_CHAIN_RPC_URL" in workflow
    assert "GAMEFI_DFK_JEWELER_REFRESH_ENABLED" in workflow
    assert 'GAMEFI_SCHEDULER_CADENCE_MINUTES: "240"' in workflow
    assert 'GAMEFI_PRODUCTION_HARD_STALE_SECONDS: "28800"' in workflow
    assert 'GAMEFI_MARKET_DATA_PRICE_FRESHNESS_SECONDS: "21600"' in workflow
    assert 'GAMEFI_WAX_MARKET_OBSERVATION_FRESHNESS_SECONDS: "21600"' in workflow
    assert 'GAMEFI_DFK_CHAIN_OBSERVATION_FRESHNESS_SECONDS: "21600"' in workflow
    assert 'GAMEFI_SPLINTERLANDS_OBSERVATION_FRESHNESS_SECONDS: "21600"' in workflow
    assert 'key: GAMEFI_SCHEDULER_CADENCE_MINUTES\n        value: "240"' in beta_blueprint
    assert 'key: GAMEFI_PRODUCTION_HARD_STALE_SECONDS\n        value: "28800"' in beta_blueprint
    assert 'key: GAMEFI_MARKET_DATA_PRICE_FRESHNESS_SECONDS\n        value: "21600"' in beta_blueprint
    assert 'key: GAMEFI_WAX_MARKET_OBSERVATION_FRESHNESS_SECONDS\n        value: "21600"' in beta_blueprint
    assert 'key: GAMEFI_DFK_CHAIN_OBSERVATION_FRESHNESS_SECONDS\n        value: "21600"' in beta_blueprint
    assert 'key: GAMEFI_SPLINTERLANDS_OBSERVATION_FRESHNESS_SECONDS\n        value: "21600"' in beta_blueprint
    assert "python -m app.jobs.snapshot_refresh" in workflow
    assert "python -m app.jobs.production_recalculation" not in workflow
