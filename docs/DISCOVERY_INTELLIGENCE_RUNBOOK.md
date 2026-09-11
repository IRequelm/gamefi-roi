# Discovery and content intelligence runbook

The first autonomous discovery slice is intentionally fail-closed and additive to the G18 catalog.

Commands (from the repository root):

```powershell
$env:PYTHONPATH = "backend"
.venv\Scripts\python.exe -m app.distribution.content_intelligence_cli status --json
.venv\Scripts\python.exe -m app.distribution.content_intelligence_cli daily-plan --json
.venv\Scripts\python.exe -m app.distribution.content_intelligence_cli daily-plan --dry-run-e2e --json
.venv\Scripts\python.exe -m app.discovery.worker --once
```

`--dry-run-e2e` uses a clearly labeled fixture to demonstrate discovery → scoring → evidence-gated `AUTO_ADD_GUIDE` → editorial brief. It performs no publication. Google Trends query extraction is implemented, but blocked or unparseable provider responses are reported explicitly; fixture values are never substituted.

Persistent records use the production database after Alembic migration `20260910_0009`. The dynamic catalog is additive and visible through `/api/v1/opportunities` when the record is admitted. `build_content_inventory(engine=...)` includes admitted dynamic opportunities. Static curated entries are never overwritten.

Provider status:

- Google Trends: query adapter implemented for normalized relative indices; the latest live attempt in this environment was blocked by HTTP 429 from `trends.google.com`.
- YouTube Data API: blocked without authorized credentials.
- X API: blocked without authorized credentials.
- Official research: evidence records are supported; no unverified financial values are admitted.
- CoinGecko market quotes: the discovery worker now captures live USD token quotes for Akash, Aethir, Grass, and Hivemapper through the existing provenance-preserving `sources/` connector. These are market observations only; they are never treated as earnings, demand, or ROI inputs by themselves.

Safety boundaries:

- `AUTO_ADD_GUIDE` does not imply ROI, earnings, or a referral.
- `AUTO_ADD_MODELED` requires reproducible economic evidence and is not implemented as a shortcut to fill catalog gaps.
- Missing referrals use official destinations and never block catalog/content eligibility.
- Creative QA and existing X/YouTube publish gates remain downstream and fail-closed.
- No public write endpoint or runtime source-code mutation is introduced.

Production sync requires the normal production PostgreSQL URL and migration rollout. Local discovery workers must not write production unless an explicitly authenticated sync path is added in a future change; there is currently no public ingestion endpoint.

The discovery worker is currently a no-publish provider-intelligence loop. It runs one bounded cycle with `--once`, atomically writes provider status/relative signals to `data/local/discovery/worker_state.json`, and can be scheduled separately from the distribution worker. It does not admit records or publish content until the authenticated production sync path is enabled.

The current market-evidence review keeps `akash-provider` as the highest-priority research candidate, but does not promote it to `MODELED`: individual utilization, hardware/energy cost, lease fill, and realizable reward evidence are still required. A spot quote alone is not a reproducible strategy input. The same gate applies to Aethir and Hivemapper; Grass remains points/reward-route limited.

Production recalculation now pauses the three DFK Jeweler strategies because the live contract response produced a non-positive aggregate cJEWEL balance, which would make the reward-share denominator invalid. Historical snapshots and failure records are retained. Public rankings exclude snapshots whose freshness deadline has passed; detail/history surfaces continue to show them with warnings.

For video rebuilds, `reuse_local_narration=True` reuses an approved local ElevenLabs asset for the same content identity and allows a visual-only rebuild when the new visual hook, product asset, scene system, and frame QA pass. It never calls ElevenLabs and never permits music-only fallback.
