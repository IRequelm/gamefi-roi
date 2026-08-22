# GameFi ROI

Working repository for the GameFi ROI data/analytics platform.

## Start here

1. Read `docs/STATUS.md`.
2. Read `AGENTS.md`.
3. Follow the ACTIVE gate only.

## Runtime

Target Python: **3.12.13**.

Python 3.12 is stable, available in the current Codex runtime, and remains suitable for a conservative backend skeleton. The project pins top-level dependencies in `pyproject.toml`; install with the development extra for tests and local commands.

## Dependency choices

- FastAPI: small, typed HTTP API surface for the health endpoint and future read API.
- SQLAlchemy 2.x: mature PostgreSQL-compatible persistence layer without committing to game schemas yet.
- Alembic: standard SQLAlchemy migration tool; G1 includes an empty baseline migration.
- psycopg 3: modern PostgreSQL driver used for real local/deployed database connections.
- pydantic-settings: typed environment configuration with `.env` support.
- httpx: bounded-timeout HTTP client used by source connectors, with deterministic mock transport tests.
- pytest/httpx: deterministic backend and API tests.

No game adapter, risk/confidence scoring, optimization, or frontend business logic is included through G3.

## Local Setup

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

If `py -3.12` is not available, install Python 3.12.13 and rerun the commands.

## Local Services

Start the local PostgreSQL service:

```powershell
docker compose up -d db
```

Apply migrations:

```powershell
.\.venv\Scripts\python -m alembic -c backend/alembic.ini upgrade head
```

Run the doctor:

```powershell
.\.venv\Scripts\python -m app.doctor
```

Run tests:

```powershell
.\.venv\Scripts\python -m pytest
```

## Quality Commands

Run these before committing backend changes:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m pip check
.\.venv\Scripts\python -m compileall -q backend
.\.venv\Scripts\python -m app.doctor
node --test frontend/tests/app.test.mjs
```

Run the API locally:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Health endpoint:

```text
GET http://127.0.0.1:8000/health
```

Versioned API health endpoint:

```text
GET http://127.0.0.1:8000/api/v1/health
```

## Market Data Source Layer

G2 establishes shared market-data infrastructure only:

- Provider-neutral contracts live in `backend/app/sources/market_data.py`.
- Normalized observations live in `backend/app/sources/observations.py`.
- Source connector errors are structured in `backend/app/sources/errors.py`.
- HTTP source calls use configured timeouts and bounded retries in `backend/app/sources/http.py`.
- Raw observations persist through `backend/app/storage/observations.py` and the Alembic observation migration.
- `backend/app/sources/coingecko.py` implements a CoinGecko simple-price connector behind the source interface.

The CoinGecko connector is tested with recorded fixtures and mock transports. The default test suite does not make live provider calls.

Source configuration:

```powershell
$env:GAMEFI_MARKET_DATA_HTTP_TIMEOUT_SECONDS = "10"
$env:GAMEFI_MARKET_DATA_HTTP_MAX_RETRIES = "2"
$env:GAMEFI_MARKET_DATA_PRICE_FRESHNESS_SECONDS = "300"
$env:GAMEFI_COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
```

`GAMEFI_COINGECKO_API_KEY` is optional and blank in `.env.example`; do not commit real provider keys.

The connector currently supports token price observations. Pool state, executable sell quotes, and OHLCV are explicit unsupported capabilities until a later gate chooses providers and acceptance criteria for those capabilities.

## ROI Core

G3 establishes the generic ROI calculation core in `backend/app/engine/`.

Implemented formulas:

- `total_capital = sunk_cost + recoverable_entry_cost + initial_operating_reserve`
- `net_earnings_day = realizable_value_day - operating_cost_day - transaction_cost_day - other_cost_day`
- `break_even_days = recovery_target / net_earnings_day`
- `roi_total_N = (N * net_earnings_day) / total_capital`
- `roi_risk_N = (N * net_earnings_day) / capital_at_risk`
- `exit_adjusted_pnl = cumulative_net_cash_earnings + current_recoverable_value - total_cash_invested_to_date`

Break-even basis is explicit: `total_capital`, `sunk_cost`, or `capital_at_risk`.

All money crossing the engine boundary uses `Money` with a `Decimal` amount and explicit currency. Required inputs fail with `EngineInputError`; they are never silently treated as zero. Zero-cost or no-cost cases must pass `Money.zero(...)` explicitly.

The engine accepts a realizable reward value that may come from a future executable quote or documented approximation. It does not implement AMM math, market-data fetching, game-specific reward logic, risk/confidence scoring, strategy optimization, or frontend presentation.

## Adapter #1: DeFi Kingdoms Jeweler

G4 adds the first game adapter for a single versioned strategy:

```text
DeFi Kingdoms Crystalvale Jeweler cJEWEL Max Lock, v1
```

The adapter models a player locking 1,000 JEWEL for 1,095 days in Jeweler 2.0 and claiming once per day. It uses official DFK contract data for yesterday's cJEWEL denominator and JEWEL reward pool, a configured lock strategy, and DFK wJEWEL-USDC pool reserves for derived USD valuation and slippage-aware reward/exit quotes.

G4 source boundaries:

- Generic EVM JSON-RPC reads live in `backend/app/sources/evm.py`.
- Constant-product AMM quote math lives in `backend/app/sources/amm.py`.
- DFK-specific strategy constants live in `backend/app/strategies/defi_kingdoms.py`.
- DFK economic interpretation lives in `backend/app/adapters/defi_kingdoms_jeweler.py`.
- The ROI engine remains generic and unchanged.

The deterministic test suite uses recorded/manual fixtures only. Live probing is opt-in:

```powershell
.\.venv\Scripts\python -m app.adapters.defi_kingdoms_jeweler_probe
```

DFK source configuration:

```powershell
$env:GAMEFI_DFK_CHAIN_RPC_URL = "https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc"
$env:GAMEFI_DFK_CHAIN_OBSERVATION_FRESHNESS_SECONDS = "300"
```

No new package dependencies were added for G4; the existing `httpx` source layer is reused for JSON-RPC POSTs.

## Adapter #2: Farmers World Axe Wood Production

G5 adds a materially different economy type: resource production with input-resource costs, NFT entry/exit pricing, DEX realization, and player-market liquidity.

The implemented strategy is:

```text
Farmers World Axe Wood Production, v1
```

The adapter models 1 Farmers World Axe NFT producing wood for 12 one-hour cycles per day. Each cycle is configured to produce 5 FWW and consume 2 FWF plus 1 FWG. The adapter maps these economics into the generic ROI engine; no ROI-core game branches were added.

G5 source boundaries:

- Alcor WAX market observations live in `backend/app/sources/alcor.py`.
- AtomicAssets WAX NFT floor observations live in `backend/app/sources/atomicassets.py`.
- Generic constant-product sell and buy quote math lives in `backend/app/sources/amm.py`.
- Farmers World strategy constants live in `backend/app/strategies/farmers_world.py`.
- Farmers World economic interpretation lives in `backend/app/adapters/farmers_world.py`.

LIVE values:

- FWW/WAX, FWF/WAX, and FWG/WAX ticker/liquidity/fee/frozen observations from Alcor.
- Axe template floor listing and collection fee from AtomicAssets.
- WAX/USD from CoinGecko.

CONFIG values:

- Tool count, cycle count, cycle length, production per cycle, resource input costs per cycle, and zero WAX transaction/resource cost assumption.

DERIVED values:

- Entry value USD, exit value USD, FWW reference price USD, realizable FWW reward value USD, FWF/FWG operating costs USD, and ROI engine outputs.

The deterministic test suite uses recorded/manual fixtures only. Live probing is opt-in:

```powershell
.\.venv\Scripts\python -m app.adapters.farmers_world_probe
```

Farmers World source configuration:

```powershell
$env:GAMEFI_ALCOR_BASE_URL = "https://wax.alcor.exchange/api/v2"
$env:GAMEFI_ATOMICASSETS_BASE_URL = "https://wax.api.atomicassets.io"
$env:GAMEFI_WAX_MARKET_OBSERVATION_FRESHNESS_SECONDS = "300"
```

No new package dependencies were added for G5; the existing `httpx` source layer is reused for public WAX market APIs.

## Adapter #3: Splinterlands Modern Ranked SPS Expected Value

G6 adds a materially different economy type: performance-dependent PvP combat rewards with explicit uncertainty.

The implemented strategy is:

```text
Splinterlands Modern Ranked SPS Expected Value, v1
```

The adapter models a player with a Summoner's Spellbook playing 20 Modern Ranked battles per day with a configured 55% expected win probability and 45%-65% uncertainty range. Expected wins are converted into expected SPS/day using a configured representative SPS reward per win, then valued with live SPS/USD pricing and a configured realization haircut.

G6 source boundaries:

- Splinterlands official settings and season observations live in `backend/app/sources/splinterlands.py`.
- SPS/USD pricing uses the existing CoinGecko source connector.
- Splinterlands strategy constants live in `backend/app/strategies/splinterlands.py`.
- Splinterlands economic interpretation lives in `backend/app/adapters/splinterlands.py`.
- The ROI engine remains generic and unchanged.

LIVE values:

- Spellbook/starter pack price, season id/end, energy max, and energy regeneration from Splinterlands official API.
- SPS/USD from CoinGecko.

CONFIG values:

- Battles/day, win-probability range, representative SPS reward per win, rental cost, transaction cost, and realization haircut.

DERIVED values:

- Sustainable energy/day, expected wins/day, expected SPS/day, low/high reward range, realizable value, low/high net range, and ROI engine outputs.

The deterministic test suite uses recorded/manual fixtures only. Live probing is opt-in:

```powershell
.\.venv\Scripts\python -m app.adapters.splinterlands_probe
```

Splinterlands source configuration:

```powershell
$env:GAMEFI_SPLINTERLANDS_BASE_URL = "https://api.splinterlands.com"
$env:GAMEFI_SPLINTERLANDS_OBSERVATION_FRESHNESS_SECONDS = "300"
```

No new package dependencies were added for G6; the existing `httpx` source layer is reused for public official API calls.

## Adapter Contract v1

G7 freezes `adapter-contract-v1` in `backend/app/adapters/contract.py` and `docs/DATA_CONTRACT.md`.

All future adapters must:

- keep provider access in `sources/`,
- keep game-specific mechanics in `adapters/`,
- define explicit versioned strategies in `strategies/`,
- return `AdapterResultV1`,
- pass contract-conformance tests,
- avoid ROI-core game branches.

Adapter #4 should be added by following the checklist in `docs/DATA_CONTRACT.md`; if the economy needs a genuinely new generic capability, document the gap before touching `engine/`.

## Historical Snapshots

G8 adds historical snapshot persistence and a simple scheduled recalculation runner.

Successful strategy calculations are stored in `strategy_snapshots`; failed calculation windows are stored in `strategy_calculation_failures` without numeric ROI output. Snapshot numeric values are serialized as exact Decimal strings, and each snapshot preserves adapter contract version, model version, strategy version, input observation references, freshness summary, LIVE / CONFIG / DERIVED classification summary, assumptions, warnings, and uncertainty ranges.

Idempotency is per `(strategy_id, strategy_version, adapter_contract_version, model_version, intended_window_start, intended_window_end)`. Re-running the same intended window returns the existing snapshot/failure; new windows or versions create new history.

Run migrations before using history locally:

```powershell
.\.venv\Scripts\python -m alembic -c backend/alembic.ini upgrade head
```

Run the deterministic local history probe:

```powershell
.\.venv\Scripts\python -m app.jobs.history_probe
```

The probe runs the existing DFK Jeweler, Farmers World, and Splinterlands adapters through the history pipeline using local deterministic observations. It does not call live provider APIs.

## Risk And Confidence

G9 adds independent, explainable risk and confidence scoring for historical snapshots.

Methodology version:

```text
risk-confidence-v1
```

Confidence starts at 100 and loses points for data/model trust issues. Risk starts at 0 and gains points for economic downside/instability. Each score persists with factor-level contributions and unavailable factors under `strategy_snapshot_scores`; scores are linked to immutable historical snapshots.

Labels:

- Confidence: `LOW` 0-49, `MODERATE` 50-79, `HIGH` 80-100
- Risk: `LOW` 0-24, `MEDIUM` 25-49, `HIGH` 50-74, `VERY HIGH` 75-100

Run the deterministic local scoring probe:

```powershell
.\.venv\Scripts\python -m app.risk.scoring_probe
```

Current deterministic probe scores:

| Strategy | Confidence | Risk |
|---|---:|---:|
| DFK Jeweler cJEWEL Max Lock | 82 HIGH | 79 VERY HIGH |
| Farmers World Axe Wood Production | 77 MODERATE | 31 MEDIUM |
| Splinterlands Modern Ranked SPS EV | 39 LOW | 100 VERY HIGH |

## Product API v1

G10 exposes a stable read-oriented API under `/api/v1`. Normal API requests read stored history and scoring rows only; they do not trigger live provider, blockchain, adapter, or recalculation work.

Endpoints:

- `GET /api/v1/health`
- `GET /api/v1/opportunities`
- `GET /api/v1/opportunities/{opportunity_id}`
- `GET /api/v1/games`
- `GET /api/v1/games/{game_id}`
- `GET /api/v1/strategies`
- `GET /api/v1/strategies/{strategy_id}`
- `GET /api/v1/strategies/{strategy_id}/latest`
- `GET /api/v1/strategies/{strategy_id}/history`
- `GET /api/v1/rankings`

Lists use `limit` and `offset` pagination. Rankings support only currently modeled filters: `capital_min`, `capital_max`, `confidence_min`, `risk_max`, `game_id`, `opportunity_id`, `opportunity_type`, `chain`, and `economy_type`.

Ranking order is deterministic:

```text
roi_total_30d desc
confidence_score desc
risk_score asc
calculated_at desc
strategy_id asc
```

Decimal policy: monetary amounts, ratios, break-even days, and range values are serialized as exact JSON strings. Unavailable values are `null` with explicit status/reason fields; missing persisted risk/confidence scores return `available=false` instead of a numeric zero.

Run the deterministic local API probe after migrations:

```powershell
.\.venv\Scripts\python -m app.api.v1_probe
```

The probe creates deterministic sample snapshots/scores only if the database has no snapshots, then reads the API surface through FastAPI's local test client.

## Web MVP

G11 adds a minimal public web interface served by the existing FastAPI app. The frontend is plain HTML/CSS/JavaScript with no npm package dependencies and no build step. This keeps the first web surface reproducible while the product is still validating the data model.

G14 expands the public interface to show a backward-compatible Opportunity catalog and a first-party outbound redirect layer. Opportunity candidates with no lawful, reproducible financial value show ROI unavailable rather than zero.

Routes:

- `/` ROI Finder
- `/rankings`
- `/opportunities`
- `/opportunities/{opportunity_id}`
- `/games/{game_id}`
- `/strategies/{strategy_id}`
- `/methodology`
- `/go/{destination_slug}` reviewed outbound redirect

Frontend boundary:

- Browser data access goes through `/api/v1` only.
- The UI displays stored API values and does not call adapters, providers, blockchain RPCs, or recalculation jobs.
- Monetary amounts, ROI ratios, break-even days, and uncertainty values are treated as exact strings from the API. The UI does not use binary-float financial calculations.
- Money, ROI, and break-even may be formatted for readability, but exact API strings remain the source values and are not recomputed into business logic.
- Missing scores and unavailable optional values remain visibly unavailable instead of becoming zero.
- Start/Play/Open calls use `/go/{destination_slug}` reviewed destinations with disclosure metadata. Affiliate or sponsor metadata must never affect ROI, Risk, Confidence, history snapshots, or organic rankings.

Run backend and frontend together locally:

```powershell
docker compose up -d db
.\.venv\Scripts\python -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python -m app.api.v1_probe
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

Run the deterministic web smoke probe:

```powershell
.\.venv\Scripts\python -m app.web_probe
```

Frontend tests use Node's built-in test runner and have no package install step:

```powershell
node --test frontend/tests/app.test.mjs
```

If `node` is not on PATH in the Codex desktop environment, use the bundled Node path reported by the workspace dependency loader.

## Test-Only Database Mode

Production and normal local development should use PostgreSQL. Deterministic tests may use SQLite only when both of these are set:

```powershell
$env:GAMEFI_ENVIRONMENT = "test"
$env:GAMEFI_ALLOW_SQLITE_FOR_TESTS = "true"
```
