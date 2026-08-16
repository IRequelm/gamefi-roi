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
→ Game Adapters
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
│   │   ├── storage/
│   │   ├── api/
│   │   ├── jobs/
│   │   ├── doctor/
│   │   └── config/
│   └── tests/
├── frontend/
├── config/
│   └── games/
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

Game logic does not belong here.

### `adapters/`
Game-specific economic interpretation.

Responsibilities:
- identify which assets/data sources matter,
- transform observations/config into strategy inputs,
- validate game-specific prerequisites,
- represent game mechanics that cannot be generic.

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
