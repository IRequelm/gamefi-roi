# GameFi ROI Production Runbook

Updated: 2026-08-23
Gate: G13 - Production public beta

## Architecture

Production target: Render.

Default public beta Blueprint:

- `gamefi-roi-web`: FastAPI modular monolith serving `/api/v1` and the existing Web MVP.
- `gamefi-roi-db`: Free Render Postgres, PostgreSQL 17.
- `.github/workflows/render-beta-recalculation.yml`: GitHub Actions scheduled recalculation every 30 minutes.

The repository contains `render.yaml` for the low-cost public beta shape. Normal API and web requests read persisted snapshots and scores only; they do not call CoinGecko, DFK RPC, Alcor, AtomicAssets, Splinterlands, or scheduled recalculation jobs.

Paid production upgrade Blueprint:

- `render.production.yaml` preserves the production-grade G13 architecture: paid web service, paid Render Postgres, and Render Cron Job.
- Use this file when backups/PITR, Render Cron single-run scheduling, and always-on web behavior are required.

## Platform Decision

Render remains selected for the first public beta because it supports the required FastAPI web service, managed Postgres, env secrets, custom domains/HTTPS, HTTP health checks, and logs in one Blueprint.

Cost-minimized beta decision:

- `render.yaml` uses a Free Web Service and Free Render Postgres.
- The paid Render Cron Job is removed from the beta Blueprint because Render Cron Jobs have paid billing.
- Scheduled recalculation moves to GitHub Actions for beta.
- GitHub Actions runs the existing `python -m app.jobs.production_recalculation` command, so application-level PostgreSQL advisory locking, G8 snapshot idempotency, hard-stale checks, and per-strategy failure isolation remain unchanged.

Free-tier limitations:

- Free web services can spin down after inactivity and restart on the next request.
- Free Render Postgres expires 30 days after creation, with a 14-day upgrade grace period before deletion.
- Free Render Postgres has a 1 GB limit.
- Free Render Postgres has no Render-managed backups, no PITR, no logical backups, and no managed connection pooling.
- Free beta is not backup-capable production. For G13 public beta, this limitation is explicitly accepted and must remain visible in product/ops reporting and handoff notes.

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

Render web service:

- `GAMEFI_ENVIRONMENT=production`
- `GAMEFI_DATABASE_URL`: from Render Postgres `connectionString`.
- `GAMEFI_API_TITLE=GameFi ROI API`
- `GAMEFI_LOG_LEVEL=INFO`
- `GAMEFI_ALLOW_SQLITE_FOR_TESTS=false`

Render web database pool:

- `GAMEFI_DATABASE_POOL_SIZE=2`
- `GAMEFI_DATABASE_MAX_OVERFLOW=1`
- `GAMEFI_DATABASE_POOL_TIMEOUT_SECONDS=30`
- `GAMEFI_DATABASE_POOL_RECYCLE_SECONDS=1800`

Security:

- `GAMEFI_SECURITY_HEADERS_ENABLED=true`
- `GAMEFI_ALLOWED_CORS_ORIGINS=` blank unless a separate trusted origin is introduced.

Public brand, analytics, and observability:

- `GAMEFI_PUBLIC_BASE_URL`: canonical public origin.
- `GAMEFI_GA_MEASUREMENT_ID`: optional GA4 measurement id such as `G-XXXXXXXXXX`; leave blank to disable Google Analytics and avoid loading Google scripts.
- `GAMEFI_SENTRY_DSN`: optional backend/job Sentry DSN. Store only in Render/GitHub secrets; never commit or paste into chat.
- `GAMEFI_SENTRY_FRONTEND_DSN`: optional browser Sentry DSN exposed through the public HTML config. Store in Render env even though browser DSNs are public by design.
- `GAMEFI_SENTRY_ENVIRONMENT=production`: normalized Sentry environment label.
- `GAMEFI_SENTRY_RELEASE`: optional release/commit identifier. If omitted, Render/GitHub commit env values are used where available.
- `GAMEFI_SENTRY_TRACES_SAMPLE_RATE=0.02`: conservative request tracing sample rate.
- `GAMEFI_SENTRY_ERROR_SAMPLE_RATE=1.0`: error-event sample rate.
- `GAMEFI_POSTHOG_PROJECT_API_KEY`: optional PostHog project API key for consent-gated explicit product events.
- `GAMEFI_POSTHOG_HOST=https://us.i.posthog.com`: PostHog capture host. Use the EU host only if the project was created in the EU region.
- `GAMEFI_POSTHOG_TIMEOUT_SECONDS=2`: bounded server-side capture timeout.
- `GAMEFI_PUBLIC_X_URL=https://x.com/GamCryp`: official public X profile URL.
- `GAMEFI_PUBLIC_YOUTUBE_URL=https://www.youtube.com/@GamCryp`
- `GAMEFI_PUBLIC_CONTACT_EMAIL=info@gamcryp.com`

GA4 consent is handled in the frontend and remains the acquisition analytics surface. PostHog is consent-gated product/funnel analytics with explicit named events only; autocapture and session replay are not enabled. Sentry is production error and request-health instrumentation with request bodies, cookies, tokens, wallet data, and obvious sensitive fields scrubbed. These systems are additive only and must not replace first-party `/go/...` records or influence ROI, Risk, Confidence, snapshots, referrals, or organic rankings.

Operator console:

- `GAMEFI_OPERATOR_USERNAME`: required to enable `/operator/...`.
- `GAMEFI_OPERATOR_PASSWORD`: required to enable `/operator/...`.
- `GAMEFI_REFERRAL_REVERIFY_DAYS=30`
- `GAMEFI_REFERRAL_PENDING_RECHECK_DAYS=14`

The operator console has no default password. If username or password is missing, operator routes fail closed with `503` and remain `noindex,nofollow`. Store operator credentials only in Render environment secrets or an equivalent secret manager; do not commit them or paste them into chat.

Freshness:

- `GAMEFI_MARKET_DATA_PRICE_FRESHNESS_SECONDS=300`
- `GAMEFI_WAX_MARKET_OBSERVATION_FRESHNESS_SECONDS=300`
- `GAMEFI_DFK_CHAIN_OBSERVATION_FRESHNESS_SECONDS=300`
- `GAMEFI_SPLINTERLANDS_OBSERVATION_FRESHNESS_SECONDS=300`
- `GAMEFI_PRODUCTION_HARD_STALE_SECONDS=1800`

GitHub Actions beta scheduler secrets:

- `GAMEFI_BETA_DATABASE_URL`: the external Render Postgres URL for the beta database. Do not use the private/internal Render URL from `fromDatabase.connectionString`; GitHub Actions runs outside Render.
- `GAMEFI_COINGECKO_API_KEY`: same production CoinGecko key used by Render.
- `GAMEFI_DFK_CHAIN_RPC_URL`: same dedicated DFK Chain RPC provider URL used by Render.

GitHub Actions beta scheduler non-secret env:

- defined in `.github/workflows/render-beta-recalculation.yml`,
- `GAMEFI_PUBLIC_BASE_URL` defaults to `https://gamefi-roi-web.onrender.com` and may be overridden with the GitHub repository variable `GAMEFI_PUBLIC_BASE_URL` when a custom domain becomes canonical,
- pool size is `1`, max overflow is `0`,
- cadence is `30` minutes.

## Deploy Procedure

1. Push the verified repository state to the branch Render will deploy.
2. In Render, create or sync a Blueprint from `render.yaml`.
3. When prompted, enter secret values for `GAMEFI_COINGECKO_API_KEY` and `GAMEFI_DFK_CHAIN_RPC_URL`.
4. Confirm the web service is created on the Free plan and the database is created on the Free plan.
5. Confirm the web service deploy runs:
   - build: `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
   - migration plus start: `python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - no `preDeployCommand`, because Render Free Web Services do not support pre-deploy commands
6. After the database exists, copy the database's external URL into the GitHub repository secret `GAMEFI_BETA_DATABASE_URL`.
7. Add GitHub repository secrets for `GAMEFI_COINGECKO_API_KEY` and `GAMEFI_DFK_CHAIN_RPC_URL`.
8. Run the GitHub Actions workflow `Render Beta Recalculation` manually once.
9. Confirm the workflow writes a new snapshot and persisted risk/confidence score.

Do not paste provider keys, database URLs, GitHub tokens, or Render secrets into chat or commit them to Git.

## Paid Production Upgrade Procedure

Upgrade from low-cost beta when real production reliability is required:

1. In Render, upgrade `gamefi-roi-db` from Free to a paid Postgres instance, or create a new paid database and restore/migrate data into it.
2. Sync a Blueprint using `render.production.yaml` instead of `render.yaml`.
3. Confirm `gamefi-roi-recalculation` exists as a Render Cron Job with schedule `*/30 * * * *`.
4. Disable the GitHub Actions `Render Beta Recalculation` workflow to avoid duplicate scheduler runs.
5. Confirm paid Postgres PITR/logical backup capability.
6. Perform restore verification before treating the service as backup/PITR-grade production.

## Migration Procedure

Free beta migration command:

```bash
python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For the Free Web Service beta, Alembic runs at the beginning of `startCommand`. If migration fails, the app server does not start, so the deploy fails closed instead of serving an outdated schema. Alembic migrations remain idempotent and reproducible; rerunning the same start command must leave an already-current schema unchanged.

For paid production, `render.production.yaml` keeps the Render web service `preDeployCommand`:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Before destructive schema changes in future gates:

1. Confirm latest backup/PITR availability.
2. Run migration in staging first.
3. Run the G12 validation suite against staging data.
4. Deploy production during a low-traffic window.

## Scheduler

### Snapshot Freshness Refresh

The canonical operator command remains:

```bash
PYTHONPATH=backend python -m app.jobs.snapshot_refresh --dry-run
PYTHONPATH=backend python -m app.jobs.snapshot_refresh --regenerate-distribution
```

`--dry-run` classifies the currently registered production strategy tasks without provider or database calls. A normal run delegates to the existing production recalculation pipeline: source loader, freshness validation, adapter, generic ROI engine, append-only history persistence, scoring, and PostgreSQL idempotency/lock protection. It does not publish content or deploy the application.

The optional `--regenerate-distribution` flag writes the file-based learning batch only after the recalculation returns zero failures. It reads the public read-only API after that successful run; it never converts stale or missing values into fresh values and never publishes drafts.

At the freshness audit on 2026-08-31, the distribution candidates' latest snapshots were calculated around `15:16 UTC` and had five-minute source deadlines around `15:21 UTC`. They were stale because no later successful recalculation had replaced them, not because the documented thresholds were loosened or because persisted source-status counts were changed.

Current distribution-relevant modeled strategies are auto-refreshable through the existing configured loaders when their provider credentials/configuration are available: DFK Jeweler, Farmers World, Splinterlands, GEODNET, WeatherXM, DIMO, Mysterium Network Node, and Storj Storage Node. The command records provider failures and skips no current registered strategy; future unsupported tasks must be explicitly classified as `MANUAL_SOURCE_REFRESH` or `NOT_REFRESHABLE` rather than assigned guessed values.

Refresh policy remains fail-closed:

- fresh source observations can produce a new snapshot;
- stale, missing, invalid, or provider-failed required inputs produce a failure, not a fresh snapshot;
- identical source state and intended window remain idempotent;
- historical snapshots are retained;
- distribution numeric packs remain RED while their source snapshot is stale;
- re-saving old data is never treated as a refresh.

Shared recalculation command:

```bash
python -m app.jobs.production_recalculation
```

Beta cadence: every 30 minutes UTC through GitHub Actions schedule `*/30 * * * *`.

Paid production cadence: every 30 minutes UTC through Render Cron.

Overlap prevention:

- Beta GitHub Actions uses workflow-level concurrency with `cancel-in-progress: false`.
- Paid Render cron provides a platform single-run guarantee.
- The application also acquires a PostgreSQL advisory lock before recalculation.

Idempotency:

- Snapshot idempotency remains the G8 policy: `(strategy_id, strategy_version, adapter_contract_version, model_version, intended_window_start, intended_window_end)`.
- Re-running the same calculation window returns the existing snapshot or failure record.

Failure isolation:

- Each strategy is calculated independently.
- One failed adapter/provider records a failure and does not create fake numeric snapshots.
- Other strategies can still persist valid snapshots and scores.

Beta limitation:

- GitHub Actions schedules can be delayed by GitHub platform availability.
- Free Render web service sleep does not affect the GitHub Actions scheduler because recalculation connects directly to Postgres and providers.
- The workflow must use the database external URL because GitHub Actions is outside Render's private network.

## Backups And Restore

Low-cost beta backup policy:

- Free Render Postgres expires 30 days after creation.
- Free Render Postgres has no Render-managed backups, no PITR, and no Render-created logical backups.
- If beta data must be retained before expiry, run a manual `pg_dump` from a trusted local machine using the external database URL and store the dump outside Git.
- No secret-bearing database dump may be committed.
- G13 public beta treats this as an accepted limitation, not a production-grade backup guarantee.
- Paid Postgres plus restore verification remains required before claiming backup/PITR-grade production.

Paid production backup policy:

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

G13 public-beta status note: no Render-managed restore verification is available on Free Postgres. The accepted beta scope documents the limitation explicitly and keeps the paid upgrade path below as the route to backup/PITR-grade production.

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
- Provider errors: `/api/v1/ops/status` `provider_errors` plus GitHub Actions beta logs or Render cron logs after paid upgrade.
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
- Operator console credentials are configured only by environment secrets.
- Operator pages set `X-Robots-Tag: noindex, nofollow`, are excluded from sitemap, and are disallowed by robots.
- Operator pages use Basic Auth and no session cookies, so the G17 console does not introduce cookie-backed CSRF state.

Render controls:

- Store secrets only in Render env/secrets and GitHub Actions repository secrets.
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
- `/opportunities`
- `/opportunities/{opportunity_id}`
- `/games/{game_id}`
- `/strategies/{strategy_id}`
- `/methodology`
- `/operator/referrals` behind Basic Auth when operator credentials are configured.

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
- Manual GitHub Actions beta scheduler run or paid Render cron run creates a new snapshot.
- History retains older snapshots.
- Simulated provider failure records a calculation failure and does not bring down the app.

## Incident Recovery

Provider outage:

1. Confirm `/api/v1/ops/status` provider error/failure count.
2. Check GitHub Actions beta scheduler logs or Render cron logs after paid upgrade.
3. Do not edit snapshots manually.
4. Let stale state remain visible until fresh observations return.

Database issue:

1. Check Render Postgres metrics/logs.
2. Run `python -m app.doctor` from a one-off shell if available, or from a trusted local machine using the same env values.
3. Restore to a new database if corruption or bad migration is confirmed.
4. Point services to the verified restore instance.

Bad deploy:

1. Roll back web service to prior Render deploy.
2. If a migration caused data corruption on Free Postgres, there is no Render PITR; restore only from a separately created `pg_dump` if one exists.
3. If a migration caused data corruption on paid Postgres, restore database to a new instance.
4. Re-run G12 validation and production validation before resuming scheduler runs.

## Rollback

Application rollback:

- Use Render's service rollback to redeploy the previous working version.
- Keep the GitHub Actions beta workflow disabled, or paid cron paused, if the failure can write bad snapshots.

Database rollback:

- On Free Postgres, restore-to-new-instance is only possible from a manual external dump; otherwise upgrade/recreate and reseed.
- On paid Postgres, prefer restore-to-new-instance over in-place mutation.
- Switch `GAMEFI_DATABASE_URL` only after staging validation succeeds against the restored database.

## Secret Rotation

1. Create the new provider key/URL at the provider.
2. Update Render environment variable and GitHub Actions repository secret.
3. Redeploy the web service.
4. Trigger a manual GitHub Actions beta run or paid cron run.
5. Confirm `/api/v1/ops/status` and Render logs.
6. Revoke the old key.

## Current Deployment Status

Public URL: `https://gamefi-roi-web.onrender.com`.

G13 public beta is complete with accepted free-tier limitations:

- Render Free Web Service may cold start after inactivity.
- Free Render Postgres expires after 30 days and has no production-grade backup/PITR.
- GitHub Actions provides the beta recalculation schedule because Render Cron Jobs are paid.
- The paid upgrade path remains `render.production.yaml`, paid Render Postgres, Render Cron, and restore verification before backup/PITR-grade production claims.

Final public validation verified `/api/v1/health`, `/api/v1/ops/status`, `/api/v1/rankings`, all three strategy latest/history endpoints, all five web pages, exact API/web Decimal-string rendering, scheduler history retention, and duplicate-window idempotency.
