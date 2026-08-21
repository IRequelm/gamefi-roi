# AGENTS.md — GameFi ROI Project Constitution

## 1. Authority and scope

This repository is the source of truth for the GameFi ROI project.

Before doing any work:
1. Read `docs/STATUS.md`.
2. Read the current gate and its acceptance criteria.
3. Read relevant authoritative documents:
   - `docs/MASTER_SPEC.md`
   - `docs/ARCHITECTURE.md`
   - `docs/ROI_METHODOLOGY.md`
   - `docs/DATA_CONTRACT.md`
4. Work only on the ACTIVE gate unless the user explicitly changes scope.

If chat instructions conflict with the repository, stop and surface the conflict before changing authoritative project decisions.

## 2. Gate discipline

- Do not implement future gates.
- A gate is complete only when all acceptance criteria pass.
- Before marking a gate complete:
  - tests must pass,
  - doctor/health checks required by that gate must pass,
  - documentation must be updated,
  - known issues must be recorded,
  - changes must be reviewable in Git.
- Never mark a gate complete based only on “it seems to work”.
- `docs/STATUS.md` must always state exactly one ACTIVE gate unless the project is paused or completed.

## 3. Engineering rules

- No giant `main.py`. Entry points orchestrate; domain logic lives in modules.
- Do not hard-code provider URLs, API keys, contract addresses, or credentials in game adapters.
- External data providers belong in shared `sources/` connectors.
- Game-specific interpretation belongs in `adapters/`.
- Generic ROI math belongs in `engine/`.
- Generic risk/confidence logic belongs in `risk/`.
- Strategy definitions must be explicit and versioned.
- Every externally sourced observation must preserve provenance and timestamps.
- Money calculations must use deterministic decimal-safe arithmetic; do not use binary floating-point for financial values.
- Store canonical units and currencies explicitly.
- Never silently substitute missing/stale data with zero.
- Never present stale or incomplete model output as current/live.
- All timestamps are stored in UTC; UI may localize them.
- External calls must have timeouts, bounded retries, and structured errors.
- A failed provider must not crash unrelated games.

## 4. Patch and debugging rules

### Three-patch rule
If three attempted fixes fail for the same defect:
1. Stop patching.
2. Reproduce the problem in isolation.
3. Identify whether the defect is architecture, data contract, environment, provider, or implementation.
4. Prefer a clean rewrite of the affected small module over further stacked patches.

### Rabbit-hole rule
If a game/data source cannot pass the Data Feasibility Check within the allocated investigation window, mark it `PARKED` or `REJECTED`; do not weaken the core architecture to force it in.

### Recovery rule
Preserve a last-known-green Git state. If an experimental change destabilizes the system, revert to the last green state instead of layering compensating patches.

## 5. Testing rules

- ROI formulas require unit tests with manually verified expected values.
- Each adapter requires at least one golden fixture independent of live APIs.
- Source connectors require contract/parsing tests using recorded fixtures.
- Any bug affecting financial output requires a regression test.
- Live integration tests must be separable from deterministic unit tests.
- No production deployment with failing deterministic tests.

## 6. Data integrity rules

Every external observation must include, at minimum:
- source/provider,
- source type,
- retrieved time,
- observed time if available,
- asset/game/entity identity,
- value,
- unit,
- freshness/staleness status.

Derived metrics must preserve references to the input observation set/model version used to calculate them.

## 7. Product integrity rules

- The primary modeled object is a **strategy**, not merely a game.
- Never label a game's single value as “the ROI” without strategy/assumption context.
- Distinguish:
  - total capital,
  - sunk cost,
  - recoverable capital,
  - capital at risk,
  - gross earnings,
  - realizable earnings,
  - net earnings,
  - exit-adjusted P&L.
- `confidence` means confidence in the model/data.
- `risk` means economic/market/game risk.
- Confidence and risk are independent.
- Affiliate/sponsor relationships must never affect ROI, Risk, Confidence, or organic rankings.
- Sponsored placements, if implemented, must be explicitly labeled and separated from organic ranking order and analytical metrics.
- Do not imply guaranteed returns or investment advice.

## 8. Security rules

- Never commit secrets.
- Use `.env` locally and provide `.env.example`.
- Prefer least-privilege credentials.
- Do not automate bypassing authentication, anti-bot protections, paywalls, or access controls.
- Public/authorized APIs, public chain data, documented endpoints, and explicitly permitted client data are acceptable.
- Do not scrape or access data in ways that violate provider terms; flag licensing/ToS uncertainty for review.
- No private wallet keys are ever required for ROI analytics.

## 9. Dependency rules

Before adding a dependency:
- state why it is needed,
- prefer mature maintained libraries,
- avoid introducing a framework for a one-line problem,
- update the lockfile/environment reproducibly.

## 10. Documentation rules

The authoritative documents are intentionally few. Do not create documentation sprawl.

Primary files:
- `docs/MASTER_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/ROI_METHODOLOGY.md`
- `docs/DATA_CONTRACT.md`
- `docs/STATUS.md`

Major irreversible architectural/product decisions may be recorded under `docs/DECISIONS/`.

## 11. Communication at the end of a task

Report:
1. what changed,
2. what was verified,
3. commands/tests run,
4. unresolved issues,
5. whether the current gate acceptance criteria are fully met.

Do not claim completion if acceptance criteria are not met.
