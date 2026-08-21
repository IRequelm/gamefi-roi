# Decision 0004: Production Platform

Date: 2026-08-16
Gate: G13 - Production
Decision: Select Render for the public beta deployment target.

## Context

G13 needs the simplest managed production architecture that supports:

- Python/FastAPI web service
- PostgreSQL
- scheduled recalculation/cron
- environment secrets
- HTTPS and optional custom domain
- logs, health checks, and platform monitoring
- database backups and restore workflow

The MVP remains a modular monolith. No new games, optimization, auth, portfolio, monetization, or major UI work belongs in this gate.

## Platform Review

| Requirement | Render | Railway | Decision Note |
|---|---|---|---|
| FastAPI web service | Native web services support Python/FastAPI, public `onrender.com` URL, custom domains, and `$PORT` binding. | FastAPI deploy is supported from GitHub, CLI, or Docker, but public URL generation is a separate service networking step. | Both viable. Render Blueprint is slightly simpler for this repo. |
| PostgreSQL | Managed Render Postgres supports internal connection URLs, major versions 13-18, metrics/logs, and paid database PITR/logical backups. | PostgreSQL service is supported with documented backups/PITR features. | Both viable. Render's database reference syntax fits the Blueprint. |
| Cron/scheduler | Render cron services support env vars and a single-run guarantee. If a run is active, the next run is delayed. | Railway cron runs scheduled service executions. If the previous execution is still active, later executions are skipped. | Render better matches "prevent overlapping runs" without losing a scheduled run. |
| Health monitoring | Render HTTP health checks can call an application path and are used for readiness and active restarts. | Railway deployment health checks only gate deployment and are not continuous monitoring. | Render is better for the minimum monitoring requirement. |
| HTTPS/custom domain | Render provides automatic TLS and redirects HTTP to HTTPS for custom domains. | Railway supports domains and SSL. | Both viable. |
| Backups/restore | Paid Render Postgres includes PITR and on-demand logical exports; restore creates a separate database for validation. | Railway PITR is available and restore creates a new service; setup requires enabling PITR. | Both viable. |
| Operational complexity | One `render.yaml` can define the web service, cron service, database, env vars, pre-deploy migration, and health path. | Railway would need service config plus manual public networking and separate continuous monitoring setup. | Render is the simpler public beta choice. |

## Selected Architecture

Render:

- `gamefi-roi-web`: Python web service running `uvicorn app.main:app`.
- `gamefi-roi-recalculation`: Python cron service running `python -m app.jobs.production_recalculation` every 30 minutes.
- `gamefi-roi-db`: Render Postgres, PostgreSQL 17, paid basic tier to enable backups.

The web service serves both `/api/v1` and the existing static Web MVP. The cron service writes historical strategy snapshots and persisted risk/confidence scores. Normal API and web requests never call live providers.

## Key Constraints

- Production must set `GAMEFI_COINGECKO_API_KEY` through Render secrets.
- Production must set `GAMEFI_DFK_CHAIN_RPC_URL` through Render secrets to a dedicated provider endpoint. The local public default is rejected in production.
- The application uses SQLAlchemy's conservative local pool settings first. Render PgBouncer is not enabled initially because the scheduler uses a PostgreSQL advisory lock, and Render's PgBouncer runs in transaction mode.
- Render's platform single-run guarantee is supplemented by the app-level advisory lock.

## Evidence

- Render Web Services: https://render.com/docs/web-services
- Render Cron Jobs: https://render.com/docs/cronjobs
- Render Health Checks: https://render.com/docs/health-checks
- Render Postgres creation/connection: https://render.com/docs/postgresql-creating-connecting
- Render Postgres backups: https://render.com/docs/postgresql-backups
- Render Blueprint reference: https://render.com/docs/blueprint-spec
- Render custom domains/TLS: https://render.com/docs/custom-domains
- Render Postgres connection pooling: https://render.com/docs/postgresql-connection-pooling
- Railway FastAPI guide: https://docs.railway.com/guides/fastapi
- Railway Cron Jobs: https://docs.railway.com/cron-jobs
- Railway deployment health checks: https://docs.railway.com/deployments/healthchecks
- Railway PostgreSQL/PITR: https://docs.railway.com/databases/postgresql and https://docs.railway.com/volumes/point-in-time-recovery

## Status

The decision and deployment configuration are prepared. Actual public deployment still requires a Render workspace, linked repository, production provider secrets, and a deployed URL to verify.
