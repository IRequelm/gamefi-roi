# GameFi ROI — Architecture
Version: 0.1
Status: FROZEN FOR G0

## 1. Architecture objective

Create a modular monolith first.

The system must be easy to reason about, test, deploy, and refactor. Do not start with microservices.

Logical flow:

External Sources
→ Source Connectors
→ Raw Observations
→ Opportunity Adapters
→ Strategy Inputs
→ ROI Engine
→ Risk / Confidence
→ Historical Storage
→ API
→ Web / future clients

## 2. Proposed repository shape

```text
gamefi-roi/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── MASTER_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── ROI_METHODOLOGY.md
│   ├── DATA_CONTRACT.md
│   ├── STATUS.md
│   └── DECISIONS/
├── backend/
│   ├── app/
│   │   ├── sources/
│   │   ├── adapters/
│   │   ├── strategies/
│   │   ├── engine/
│   │   ├── risk/
│   │   ├── monetization/
│   │   ├── storage/
│   │   ├── api/
│   │   ├── jobs/
│   │   ├── doctor/
│   │   └── config/
│   └── tests/
├── frontend/
├── config/
│   └── opportunities/
└── scripts/
```

Exact framework/library choices are a G1 decision, not a G0 requirement.

## 3. Module responsibilities

### `sources/`
Shared external-provider connectors.

Examples:
- CoinGecko/GeckoTerminal
- Ronin RPC/provider
- generic EVM RPC
- marketplace APIs
- official game APIs

Responsibilities:
- authentication,
- request formation,
- timeouts/retries,
- provider response validation,
- mapping provider response to raw normalized observations,
- rate-limit/error reporting.

Game/opportunity logic does not belong here.

### `adapters/`
Opportunity-specific economic interpretation.

Responsibilities:
- identify which assets/data sources matter,
- transform observations/config into strategy inputs,
- validate opportunity-specific prerequisites,
- represent game, node, points, or program mechanics that cannot be generic.

Adapters must not own generic ROI formulas.

### `strategies/`
Strategy schemas/definitions and optimization input.

Responsibilities:
- strategy identity/version,
- capital configuration,
- required assets,
- behavioral assumptions,
- claim interval/playtime/uptime assumptions,
- route to realization.

### `engine/`
Generic financial/economic calculations.

Responsibilities:
- capital decomposition,
- reward valuation,
- costs,
- realizable exit,
- ROI,
- break-even,
- exit-adjusted P&L,
- comparative strategy calculation.

The engine should not contain `if game == "Craft World"` logic.
The engine should also not contain `if opportunity_type == "DEPIN_NODE"` or points-program-specific logic.

### `risk/`
Generic risk/confidence logic.

Confidence:
- source quality,
- completeness,
- freshness,
- model certainty.

Risk:
- liquidity,
- price volatility/trend,
- concentration where measurable,
- emission/reward stability where measurable,
- model-specific economic warnings.

### `storage/`
Persistence and query abstractions.

Expected persistent entities:
- opportunities,
- games,
- chains,
- assets,
- contracts,
- data sources,
- observations,
- strategy definitions,
- strategy runs/snapshots,
- risk/confidence outputs,
- model versions.

### `jobs/`
Scheduled collection and recalculation.

Responsibilities:
- refresh observations,
- detect stale data,
- trigger strategy recalculation,
- retain history,
- isolate failures.

### `api/`
Read-oriented product API first.

Likely endpoints later:
- games
- strategies
- rankings
- strategy detail
- history
- source/freshness metadata

### `doctor/`
Environment and dependency checks.

Target command eventually:
`python -m app.doctor`

It should test environment, DB, schema, configured providers, migrations, adapter registry, and scheduler prerequisites without mutating production data.

## 4. Data flow

### Collection
Provider response
→ connector parses
→ `Observation`
→ persistence

### Calculation
Latest valid observations + verified config
→ adapter
→ `StrategyInput`
→ ROI engine
→ risk/confidence
→ `StrategySnapshot`
→ persistence

### Serving
API reads stored snapshots.

Website requests should not trigger live blockchain/API calls synchronously in the normal path.

### G10 API boundary

The G10 product API is versioned under `/api/v1` and is read-oriented. It serves catalog, latest snapshot, historical snapshot, risk/confidence, and ranking data from persisted `strategy_snapshots` and `strategy_snapshot_scores` records.

Normal API requests must not call source providers, blockchain RPCs, adapters, or recalculation jobs. Snapshot creation remains the responsibility of the scheduled recalculation/history pipeline.

### G11 web boundary

The G11 web MVP is a static browser client served by the FastAPI modular monolith. It consumes `/api/v1` only and does not duplicate ROI, risk, confidence, adapter, provider, or optimization logic.

The web routes are public read-only pages for ROI Finder, Rankings, Game Detail, Strategy Detail, and Methodology. Authentication, portfolio tracking, alerts, production deployment, monetization, AI chat, and native mobile surfaces remain out of scope.

### G14/G15 outbound and monetization boundary

Outbound/referral metadata is product metadata, not ROI model input.

G14 may add a canonical `Opportunity` catalog while keeping the existing `Game` model as a compatibility view over `Opportunity` records where `opportunity_type = GAME`.

Backward-compatibility rules:

- existing `game_id` values for DeFi Kingdoms, Farmers World, and Splinterlands remain stable,
- existing GameFi adapters and strategy definitions are not renamed merely for taxonomy cleanup,
- `/api/v1/games` remains available as a GAME-only compatibility surface,
- new canonical opportunity surfaces may be additive, for example `/api/v1/opportunities`,
- old API fields may be deprecated only after new `opportunity_id` / `opportunity_type` fields exist and tests prove old clients still work.

Supported planned opportunity types:

- `GAME`,
- `DEPIN_NODE`,
- `POINTS`.

G14 may add structured opportunity/strategy outbound destination metadata and a first-party `/go/...` redirect layer. The redirect layer must resolve only allowlisted reviewed destinations and fail closed for unknown or disabled destinations.

G15 adds affiliate attribution/reporting foundations, sponsored placement metadata, and commercial analytics on top of the G14 foundation.

Commercial data must remain separated from:
- adapter observations,
- ROI engine inputs/outputs,
- risk/confidence scoring inputs/outputs,
- historical strategy snapshots,
- organic ranking inputs and ordering.

Affiliate/sponsor relationships must never affect ROI, Risk, Confidence, or organic rankings. Sponsored placements must be separately modeled, explicitly labeled, and served outside organic ranking order.

Points-only opportunities must not publish financial ROI until a lawful, reproducible, realizable value route exists. The platform may show points production, capital/cost burden, warnings, and confidence/risk context with ROI marked unavailable rather than zero.

G15 commercial storage uses four separate tables:

- `outbound_click_events`: privacy-minimal `/go/...` click events with destination, source surface, coarse optional session, user-agent category, and official/referral target kind.
- `referral_programs`: referral lifecycle metadata with explicit statuses `NONE`, `DISCOVERED`, `APPLICATION_REQUIRED`, `PENDING`, `VERIFIED`, `ACTIVE`, `PAUSED`, `REJECTED`, and `EXPIRED`.
- `revenue_attributions`: verified/manual partner attribution imports. Pending or rejected imports are retained for audit but do not contribute to EPC or conversion-rate metrics.
- `sponsored_placements`: labeled commercial placement metadata with campaign status, placement surface, disclosure text, and audit trail.

`/api/v1/rankings` continues to return organic ranking `items` from snapshots/scores only. Sponsored placements, when present, are exposed in a separate `sponsored_placements` collection and must not be merged into the organic list.

### G16 search / AI discovery boundary

G16 converts the public web shell from JavaScript-only pages into server-rendered, crawlable HTML for the canonical public pages while preserving the browser client as progressive enhancement.

Canonical crawlable URL families:

- `/`,
- `/opportunities`,
- `/opportunities/{opportunity_id}`,
- `/strategies/{strategy_id}`,
- `/games/{game_id}`,
- `/rankings`,
- curated ranking landing pages under `/rankings/{slug}`,
- `/methodology`.

The canonical public host is configured by `GAMEFI_PUBLIC_BASE_URL`. Search, sitemap, JSON-LD, Open Graph, Twitter metadata, and IndexNow submission code must derive absolute URLs from this setting and must not hard-code a hosting provider URL in application logic.

Search modules:

- `app.web.seo`: builds server-rendered HTML, page-specific metadata, truthful JSON-LD, crawlable anchor links, and human-readable display formatting from existing API service payloads.
- `app.search.canonical`: owns the canonical public URL inventory, curated ranking page definitions, canonical URL normalization, sitemap inputs, and IndexNow eligibility checks.
- `app.search.indexnow`: submits explicitly selected canonical URLs to IndexNow with host validation, timeouts, bounded retries, and secret redaction.
- `app.search.indexnow_cli`: manual operator CLI for all-canonical or explicit URL submissions.

Public page requests may read persisted snapshots, scores, catalog records, outbound metadata, and commercial placement metadata already exposed by the read-oriented API. They must not call adapters, live providers, blockchain RPCs, source connectors, recalculation jobs, or ROI/risk/confidence logic.

Search metadata must remain truthful:

- no guaranteed-return language,
- no page-level “game ROI” without strategy context,
- unavailable ROI is rendered as unavailable, never zero,
- sponsored/referral/commercial relationships never affect ROI, Risk, Confidence, historical snapshots, or organic ranking order,
- sponsored placements remain labeled and separate where rendered.

`/sitemap.xml` contains absolute canonical URLs only and excludes `/api`, `/go`, assets, query permutations, debug/test/internal paths, and arbitrary filtered ranking URLs. Query-parameter pages render `noindex,follow` and canonicalize to their clean path unless they are explicit curated landing pages.

`/robots.txt` allows public content and disallows `/api`, `/go`, admin/internal/debug/test paths, and query traps. It intentionally does not block Googlebot, Bingbot, OAI-SearchBot, or PerplexityBot. OAI-SearchBot is treated as the ChatGPT search discovery crawler; GPTBot is documented separately as OpenAI's training crawler and is not controlled by the OAI-SearchBot policy.

Inbound acquisition attribution is privacy-minimal and separate from monetization attribution:

- landing path,
- referrer domain,
- UTM source/medium/campaign,
- normalized channel,
- timestamp,
- optional coarse session id only when already supplied.

It does not set cookies, fingerprint users, store raw IP addresses, trigger provider calls, alter rankings, or join into ROI/risk/confidence calculations.

### G17 referral operations boundary

G17 adds a small single-operator workflow layer for managing referral program coverage. It is intentionally separate from the analytical core.

Modules:

- `app.monetization.referral_operations`: derives referral coverage states from stored metadata, validates operator-provided URLs, creates referral work queue tasks, overlays safe active referral destinations for `/go`, and validates manual revenue records.
- `app.operator.routes`: serves the protected HTML operator console. It is included in the FastAPI app but excluded from OpenAPI, sitemap, and indexable search surfaces.
- `app.storage.monetization`: persists expanded referral program metadata, referral task queue rows, outbound clicks, sponsored placements, and revenue attribution.

Request boundaries:

- normal public API/web requests may read reviewed destination metadata and redirect through `/go/{destination_slug}`,
- normal public API/web requests must not create referral tasks or execute referral health checks,
- `/go/{destination_slug}` does not accept arbitrary target URLs and falls back to the reviewed official URL when a referral URL is invalid, missing, unverified, expired, or paused,
- operator pages require Basic Auth credentials from environment secrets and set `noindex,nofollow` headers.

Commercial integrity boundary:

- referral status,
- referral URL/code,
- affiliate program metadata,
- click events,
- revenue attribution,
- sponsored placement data,
- operator task state,

must never feed:

- ROI engine inputs/outputs,
- adapter result construction,
- risk/confidence scoring,
- historical strategy snapshot persistence,
- validation outputs,
- organic ranking inputs or ordering.

## 5. Provider abstraction

No provider-specific URL should be embedded inside an adapter.

Example concept:

```text
MarketDataSource
  get_token_price(...)
  get_pool_state(...)
  quote_sell(...)
  get_ohlcv(...)
```

Multiple providers may eventually satisfy the same capability.

Prototype may use a single provider, but the architecture must not assume it is permanent.

## 6. Financial arithmetic

Use decimal-safe arithmetic.

Canonical practice:
- use `Decimal` or equivalent for monetary values,
- carry explicit currency/unit,
- specify rounding policy at display boundaries,
- retain high precision internally,
- never infer USD equivalence without an observation/source.

## 7. Time and freshness

- store UTC,
- retain `observed_at` and `retrieved_at`,
- source/config defines freshness windows,
- stale values are not silently treated as live,
- strategy snapshot records input freshness.

## 8. Fault isolation

If one provider or game fails:
- other games continue,
- last known data may be displayed only with explicit stale status,
- calculation should fail closed when required inputs are unavailable.

## 9. Caching and polling

Prototype polling may use public/free APIs within their documented limits.

Production must use appropriately licensed/reliable providers and respect rate limits/terms.

Do not design the system around unlimited public RPC/API access.

## 10. Adapter interface freeze

The universal adapter contract is **not frozen at G0**. Adapter Contract v1 is frozen at G7 in `docs/DATA_CONTRACT.md` and implemented in `backend/app/adapters/contract.py`.

Process:
- build adapter #1,
- build materially different adapter #2,
- build materially different adapter #3,
- compare common patterns,
- freeze Adapter Contract v1 at G7.

This prevents premature abstraction.

## 11. Deployment principle

Initial production should remain simple:
- one backend service,
- one relational database,
- one worker/scheduler process if necessary,
- one frontend deployment.

Split services only when measured operational needs justify it.

## 12. Security boundary

The analytics platform should not require custody or private keys.

Wallet addresses may eventually be optional public inputs for portfolio verification, but not for MVP core calculations.

## 13. Deferred decisions

G1 or later:
- exact Python version,
- FastAPI vs alternative,
- PostgreSQL hosting provider,
- ORM,
- scheduler library,
- frontend framework,
- deployment provider,
- observability vendor.

Choose these only when the gate requires them.
