# GameFi ROI Production Runbook

Updated: 2026-08-16
Gate: G13 - Production

## Architecture

Production target: Render.

Services:

- `gamefi-roi-web`: FastAPI modular monolith serving `/api/v1` and the existing Web MVP.
- `gamefi-roi-recalculation`: Render cron job running scheduled live recalculation and snapshot scoring.
- `gamefi-roi-db`: Render Postgres, PostgreSQL 17.

The repository contains `render.yaml` so the deploy shape is reproducible. Normal API and web requests read persisted snapshots and scores only; they do not call CoinGecko, DFK RPC, Alcor, AtomicAssets, or Splinterlands.

## Platform Decision

Render is selected over Railway for the first public beta because it supports the required FastAPI web service, managed Postgres, cron service, env secrets, custom domains/HTTPS, HTTP health checks, logs, and backups in one Blueprint. Railway is viable, but its documented health checks are deployment-gating rather than continuous monitoring, and its cron skips later executions when a previous run is active. Render cron delays the next run while an existing run is still active.

Decision record: `docs/DECISIONS/0004-production-platform.md`.

## Provider Configuration

Set production provider values only through Render environment variables/secrets.

Required production secrets:

- `GAMEFI_COINGECKO_API_KEY`: CoinGecko API key for production polling.
- `GAMEFI_DFK_CHAIN_RPC_URL`: dedicated DFK Chain RPC provider URL. Do not use the local public default in production.

Required non-secret provider config:

- `GAMEFI_COINGECKO_BASE_URL=https://api.coingecko.com/api/v3`
- `GAMEFI_ALCOR_BASE_URL=https://wax.alcor.exchange/api/v2`
- `GAMEFI_ATOMICASSETS_BASE_URL=https://wax.api.atomicassets.io`
- `GAMEFI_SPLINTERLANDS_BASE_URL=https://api.splinterlands.com`

Rate and retry defaults:

- HTTP timeout: `10` seconds.
- Max retries: `2`.
- Shared source HTTP helper logs provider retries and failures without logging secrets.
- Scheduler cadence: every `30` minutes.

## Environment Variables

Core:

- `GAMEFI_ENVIRONMENT=production`
- `GAMEFI_DATABASE_URL`: from Render Postgres `connectionString`.
- `GAMEFI_API_TITLE=GameFi ROI API`
- `GAMEFI_LOG_LEVEL=INFO`
- `GAMEFI_ALLOW_SQLITE_FOR_TESTS=false`

Database pool:

- `GAMEFI_DATABASE_POOL_SIZE=3` for web, `2` for cron.
- `GAMEFI_DATABASE_MAX_OVERFLOW=2` for web, `1` for cron.
- `GAMEFI_DATABASE_POOL_TIMEOUT_SECONDS=30`
- `GAMEFI_DATABASE_POOL_RECYCLE_SECONDS=1800`

Security:

- `GAMEFI_SECURITY_HEADERS_ENABLED=true`
- `GAMEFI_ALLOWED_CORS_ORIGINS=` blank unless a separate trusted origin is introduced.

Freshness:

- `GAMEFI_MARKET_DATA_PRICE_FRESHNESS_SECONDS=300`
- `GAMEFI_WAX_MARKET_OBSERVATION_FRESHNESS_SECONDS=300`
- `GAMEFI_DFK_CHAIN_OBSERVATION_FRESHNESS_SECONDS=300`
- `GAMEFI_SPLINTERLANDS_OBSERVATION_FRESHNESS_SECONDS=300`
- `GAMEFI_PRODUCTION_HARD_STALE_SECONDS=1800`

## Deploy Procedure

1. Push the verified repository state to the branch Render will deploy.
2. In Render, create or sync a Blueprint from `render.yaml`.
3. When prompted, enter secret values for `GAMEFI_COINGECKO_API_KEY` and `GAMEFI_DFK_CHAIN_RPC_URL`.
4. Confirm the database is created on the paid `basic-256mb` plan so backups/PITR are available.
5. Confirm the web service deploy runs:
   - build: `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
   - pre-deploy migration: `python -m alembic -c backend/alembic.ini upgrade head`
   - start: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Confirm the cron service command:
   - `python -m app.jobs.production_recalculation`
   - schedule: `*/30 * * * *`
7. Trigger one manual cron run after the first web deploy.

## Migration Procedure

Render web service pre-deploy command:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Before destructive schema changes in future gates:

1. Confirm latest backup/PITR availability.
2. Run migration in staging first.
3. Run the G12 validation suite against staging data.
4. Deploy production during a low-traffic window.

## Scheduler

Production command:

```bash
python -m app.jobs.production_recalculation
```

Cadence: every 30 minutes UTC.

Overlap prevention:

- Render cron provides a single-run guarantee.
- The application also acquires a PostgreSQL advisory lock before recalculation.

Idempotency:

- Snapshot idempotency remains the G8 policy: `(strategy_id, strategy_version, adapter_contract_version, model_version, intended_window_start, intended_window_end)`.
- Re-running the same calculation window returns the existing snapshot or failure record.

Failure isolation:

- Each strategy is calculated independently.
- One failed adapter/provider records a failure and does not create fake numeric snapshots.
- Other strategies can still persist valid snapshots and scores.

## Backups And Restore

Backup policy:

- Use paid Render Postgres so PITR and logical backups are available.
- Keep Render-managed PITR enabled.
- Use logical exports for longer-term off-platform retention before major migrations.

Restore verification:

1. In Render Postgres, trigger PITR or logical restore to a new database instance.
2. Point a staging web service at the restored database.
3. Run:

```bash
python -m app.doctor
python -m app.api.v1_probe
python -m app.web_probe
```

4. Verify `/api/v1/ops/status`, `/api/v1/rankings`, and all three strategy latest endpoints.
5. Delete the restore instance only after verification.

G13 status note: no restore verification has been performed from this Codex environment because no Render workspace/database is connected.

## Monitoring

HTTP health check:

- Render health path: `/api/v1/ops/status`.
- This endpoint verifies database connectivity and reports scheduler/history state without provider calls.

Minimum fields to monitor:

- API health: `/api/v1/health`.
- Database health: `/api/v1/ops/status` `database.status`.
- Last successful scheduler run: `/api/v1/ops/status` `scheduler.last_successful_run_at`.
- Last successful snapshot per strategy: `/api/v1/ops/status` `scheduler.last_successful_snapshot_per_strategy`.
- Failed calculation count: `/api/v1/ops/status` `failed_calculation_count`.
- Stale strategy count: `/api/v1/ops/status` `stale_strategy_count`.
- Provider errors: `/api/v1/ops/status` `provider_errors` plus Render cron logs.
- Application errors: Render web service logs.

Recommended alert thresholds:

- `/api/v1/ops/status` not returning 2xx for two consecutive checks.
- `scheduler.last_successful_run_at` older than 2 scheduler intervals.
- Any strategy with no latest snapshot after the first manual cron run.
- Any hard-stale LIVE input preventing a new valid snapshot.
- Repeated provider failure for the same strategy across 3 consecutive runs.

## Security

Production controls in code/config:

- Production settings reject SQLite.
- Production settings reject missing `GAMEFI_COINGECKO_API_KEY`.
- Production settings reject the local public DFK RPC default.
- Production settings reject wildcard CORS.
- Security headers are enabled in production.
- FastAPI debug mode is not enabled.
- Static files are served from explicit assets, with no directory listing.
- Normal API requests do not expose internal exception traces by design.

Render controls:

- Store secrets only in Render env/secrets.
- Use the internal Postgres URL for Render services.
- Keep custom domain HTTPS enabled; Render terminates TLS and redirects HTTP to HTTPS.

Dependency review:

- Run `python -m pip check` before deployment.
- Keep dependency additions gated by AGENTS.md dependency rules.
- No private wallet keys are required for production analytics.

## Web

The existing FastAPI app serves:

- `/`
- `/rankings`
- `/games/{game_id}`
- `/strategies/{strategy_id}`
- `/methodology`

HTTPS is required. If no custom domain is available, use the Render `onrender.com` URL for beta and document the custom domain as pending.

Custom domain procedure:

1. Add the domain to `gamefi-roi-web` in Render.
2. Configure DNS at the registrar.
3. Wait for Render verification and TLS issuance.
4. Set `GAMEFI_ALLOWED_CORS_ORIGINS` only if the API is intentionally consumed from a separate trusted origin.

## Production Validation

After deployment, verify from outside the local machine:

```bash
curl https://<production-host>/api/v1/health
curl https://<production-host>/api/v1/ops/status
curl https://<production-host>/api/v1/rankings
curl https://<production-host>/api/v1/strategies/dfk-crystalvale-jeweler-cjewel-max-lock/latest
curl https://<production-host>/api/v1/strategies/farmers-world-axe-wood-production/latest
curl https://<production-host>/api/v1/strategies/splinterlands-modern-ranked-sps-ev/latest
```

Browser pages:

- `https://<production-host>/`
- `https://<production-host>/rankings`
- `https://<production-host>/games/defi-kingdoms`
- `https://<production-host>/strategies/dfk-crystalvale-jeweler-cjewel-max-lock`
- `https://<production-host>/methodology`

Required checks:

- Rankings loads stored snapshots only.
- Risk/confidence displays on strategy detail.
- Stale/warning state is visible where present.
- API values match web displayed values exactly.
- Manual cron run creates a new snapshot.
- History retains older snapshots.
- Simulated provider failure records a calculation failure and does not bring down the app.

## Incident Recovery

Provider outage:

1. Confirm `/api/v1/ops/status` provider error/failure count.
2. Check Render cron logs.
3. Do not edit snapshots manually.
4. Let stale state remain visible until fresh observations return.

Database issue:

1. Check Render Postgres metrics/logs.
2. Run `python -m app.doctor` from a one-off shell if available.
3. Restore to a new database if corruption or bad migration is confirmed.
4. Point services to the verified restore instance.

Bad deploy:

1. Roll back web service to prior Render deploy.
2. If a migration caused data corruption, restore database to a new instance.
3. Re-run G12 validation and production validation before resuming cron.

## Rollback

Application rollback:

- Use Render's service rollback to redeploy the previous working version.
- Keep cron paused if the failure can write bad snapshots.

Database rollback:

- Prefer restore-to-new-instance over in-place mutation.
- Switch `GAMEFI_DATABASE_URL` only after staging validation succeeds against the restored database.

## Secret Rotation

1. Create the new provider key/URL at the provider.
2. Update Render environment variable.
3. Redeploy the web and cron services.
4. Trigger a manual cron run.
5. Confirm `/api/v1/ops/status` and Render logs.
6. Revoke the old key.

## Current Deployment Status

Public URL: pending.

This repository is prepared for Render deployment, but G13 cannot be marked complete until a Render workspace, production provider secrets, production database, actual deployed URL, scheduler run, backup/restore verification, and external production validation are completed.
