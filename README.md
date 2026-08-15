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
```

Run the API locally:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Health endpoint:

```text
GET http://127.0.0.1:8000/health
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

## Test-Only Database Mode

Production and normal local development should use PostgreSQL. Deterministic tests may use SQLite only when both of these are set:

```powershell
$env:GAMEFI_ENVIRONMENT = "test"
$env:GAMEFI_ALLOW_SQLITE_FOR_TESTS = "true"
```
