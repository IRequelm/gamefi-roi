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
- pytest/httpx: deterministic backend and API tests.

No market-data provider, game adapter, ROI formula, or frontend business logic is included in G1.

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

## Test-Only Database Mode

Production and normal local development should use PostgreSQL. Deterministic tests may use SQLite only when both of these are set:

```powershell
$env:GAMEFI_ENVIRONMENT = "test"
$env:GAMEFI_ALLOW_SQLITE_FOR_TESTS = "true"
```
