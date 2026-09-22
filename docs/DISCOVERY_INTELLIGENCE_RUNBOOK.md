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

On Windows, register the no-publish discovery loop for a six-hour cadence from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_discovery_worker.ps1
```

The scheduled runner only executes `app.discovery.worker --once`; it never publishes to X or YouTube. It writes an append-only transcript to `data/local/discovery/worker.log` and the atomic provider state to `data/local/discovery/worker_state.json`. Research leads are persisted as `PENDING` records even when mail is disabled. In that mode, new leads also receive unsent token-bound `.eml` drafts under `data/local/discovery/approval_outbox/`; these drafts are not counted as delivered email, and candidate admission remains fail-closed until the database and SMTP/IMAP settings are configured.

Google discovery seeds are configured with `GAMEFI_DISCOVERY_GOOGLE_KEYWORDS` as a comma-separated list (maximum five terms). `GAMEFI_DISCOVERY_GOOGLE_GEO` bounds the Explore request to a two-letter regional code (default `US`) instead of the noisier global request. The default seeds cover GameFi, DePIN, crypto nodes, GPU compute, and storage nodes; related queries remain research leads until official evidence and operator approval exist. The Trends adapter persists only its public session cookie state under ignored `data/local` (configurable with `GAMEFI_DISCOVERY_GOOGLE_TRENDS_COOKIE_FILE`) so scheduled runs can reuse a warmed session; it never stores an account token or treats cookie persistence as a readiness requirement.

`--dry-run-e2e` uses a clearly labeled fixture to demonstrate discovery → scoring → evidence-gated `AUTO_ADD_GUIDE` → editorial brief. It performs no publication. Google Trends query extraction uses a cookie-backed session for Explore/widget requests; blocked or unparseable provider responses are reported explicitly, and fixture values are never substituted.

Persistent records use the production database after Alembic migration `20260910_0009`. The dynamic catalog is additive and visible through `/api/v1/opportunities` when the record is admitted. `build_content_inventory(engine=...)` includes admitted dynamic opportunities. Static curated entries are never overwritten.

Provider status:

- Google Trends: query adapter implemented for normalized relative indices, cookie-backed Explore/widget requests, and official RSS fallback; rate limits remain explicit and do not become fabricated signals. When Trends is empty, blocked, or returns only seed-term momentum without candidate-level related queries, Google News RSS supplies bounded article-level research leads; these are not search volume or demand measurements.
- YouTube Data API: blocked without authorized credentials.
- X API: blocked without authorized credentials.
- Official research: evidence records are supported; no unverified financial values are admitted.
- CoinGecko market quotes: the discovery worker now captures live USD token quotes for Akash, Aethir, Grass, and Hivemapper through the existing provenance-preserving `sources/` connector. These are market observations only; they are never treated as earnings, demand, or ROI inputs by themselves.

Safety boundaries:

- `AUTO_ADD_GUIDE` does not imply ROI, earnings, or a referral.
- `AUTO_ADD_MODELED` requires reproducible economic evidence and is not implemented as a shortcut to fill catalog gaps.
- Missing referrals use official destinations and never block catalog/content eligibility.
- Creative QA and existing X/YouTube publish gates remain downstream and fail-closed.
- A newly discovered candidate is never added to the public dynamic catalog on discovery alone. When approval email is enabled, the candidate remains `PENDING` until an explicit `SITEYE_EKLE <token>` reply is processed. The token is stored only as a SHA-256 hash; ordinary email prose cannot approve a candidate.
- No public write endpoint or runtime source-code mutation is introduced.

Production sync requires the normal production PostgreSQL URL and migration rollout. Local discovery workers must not write production unless an explicitly authenticated sync path is added in a future change; there is currently no public ingestion endpoint.

The discovery worker is currently a no-publish provider-intelligence loop. It runs one bounded cycle with `--once`, atomically writes provider status/relative signals to `data/local/discovery/worker_state.json`, and can be scheduled separately from the distribution worker. It does not admit records or publish content until the authenticated production sync path is enabled.

Each new lead is persisted with a one-time token even while SMTP is disabled. When SMTP is disabled, the same approval message is written as an unsent local draft; when SMTP approval settings are enabled, a pending token is rotated as needed and the lead receives the message with the article and search locators. A `SITEYE_EKLE <token>` reply adds a clearly labelled `RESEARCH` candidate page with those references explicitly marked as non-official and with ROI unavailable; it does not invent an official URL, reward value, exit path, or financial model. The candidate can become an official GUIDE_ONLY or MODELED opportunity only after a later evidence-verification pass supplies the required sources.

If SMTP delivery fails after a lead is persisted, the next worker cycle rotates
the pending one-time token and retries the message. The failed token is no
longer valid, so a reply must use the newest email's command.

The current market-evidence review keeps `akash-provider` as the highest-priority research candidate, but does not promote it to `MODELED`: individual utilization, hardware/energy cost, lease fill, and realizable reward evidence are still required. A spot quote alone is not a reproducible strategy input. The same gate applies to Aethir and Hivemapper; Grass remains points/reward-route limited.

Production recalculation now pauses the three DFK Jeweler strategies because the live contract response produced a non-positive aggregate cJEWEL balance, which would make the reward-share denominator invalid. Historical snapshots and failure records are retained. Public rankings exclude snapshots whose freshness deadline has passed; detail/history surfaces continue to show them with warnings.

For video rebuilds, `reuse_local_narration=True` reuses an approved local ElevenLabs asset for the same content identity and allows a visual-only rebuild when the new visual hook, product asset, scene system, and frame QA pass. It never calls ElevenLabs and never permits music-only fallback.

## Candidate approval mailbox

Configure the SMTP/IMAP variables in `.env` only with an app password. Keep
`GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED=false` until the mailbox has been
tested. From the repository root:

```powershell
$env:PYTHONPATH = "backend"
.venv\Scripts\python.exe -m app.discovery.approval_cli poll
```

An approval email contains an exact, token-bound command:

```text
SITEYE_EKLE <token>
```

`REDDET <token>` rejects the candidate. The public catalog changes only after a
valid pending token is approved; MODELED candidates still require reproducible
ROI evidence before any financial result is presented.

When SMTP is disabled, inspect the unsent drafts with:

```powershell
Get-ChildItem .\data\local\discovery\approval_outbox\*.eml
```

An outbox draft is a local handoff artifact, not proof that the email was delivered.

The read-only growth report exposes missing mailbox variable names under
`discovery.approval_email_missing` without printing credential values. Set the
`GAMEFI_DISCOVERY_APPROVAL_EMAIL_*` SMTP variables and
`GAMEFI_DISCOVERY_APPROVAL_IMAP_*` variables before enabling the mailbox loop.

After approval, the database-backed content inventory includes the dynamic
opportunity automatically. The distribution worker passes the live catalog
engine into Short preparation when available, so the next refill can generate
an evidence-bound candidate package; if the database is unavailable it falls
back to the static catalog and does not invent content.

## Enriching an approved research candidate

An approved `RESEARCH` candidate is not yet an official opportunity. Before it
can become a GUIDE_ONLY catalog entry, the operator must review the official
sources and provide a JSON array of evidence facts. Each fact must identify its
kind (`identity`, `participation`, `requirements`, `reward_mechanism`, or
`exit_path`), use an HTTPS source, and set `verified` to `true` only after
review. The command requires an explicit `--confirm-reviewed` flag:

```powershell
$env:PYTHONPATH = "backend"
.venv\Scripts\python.exe -m app.discovery.approval_cli enrich <discovery-id> `
  --category DEPIN_NODE `
  --official-url https://official.example/ `
  --evidence-json .\data\local\discovery\evidence\<discovery-id>.json `
  --confirm-reviewed
```

Example evidence JSON:

```json
[
  {"fact_kind":"identity","fact":"The official project identity is documented.","source_role":"OFFICIAL_PROJECT","source_url":"https://official.example/","verified":true},
  {"fact_kind":"participation","fact":"Operators follow the documented participation steps.","source_role":"OFFICIAL_PROJECT","source_url":"https://official.example/start","verified":true},
  {"fact_kind":"reward_mechanism","fact":"The project documents its reward mechanism.","source_role":"OFFICIAL_PROJECT","source_url":"https://official.example/rewards","verified":true}
]
```

The command promotes only when identity, participation, and reward evidence
are present. It carries the reviewed facts into content guidance, retires the
old research-only card, and keeps ROI unavailable until reproducible economic
inputs and a realizable exit route are separately evidenced.
