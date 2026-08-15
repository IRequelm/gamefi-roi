# GameFi ROI — Project Status

Updated: 2026-08-15
Project version: 0.1

## Current state

**ACTIVE GATE: G6 — Adapter #3**

G5 is complete and frozen in the G5 baseline Git commit.

Do not implement G6 until the user explicitly asks to proceed.

## Gate board

| Gate | Name | Status |
|---|---|---|
| G0 | Freeze | COMPLETE |
| G1 | Skeleton | COMPLETE |
| G2 | Market Data | COMPLETE |
| G3 | ROI Core | COMPLETE |
| G4 | Adapter #1 | COMPLETE |
| G5 | Adapter #2 | COMPLETE |
| G6 | Adapter #3 | ACTIVE |
| G7 | Interface Freeze | NOT STARTED |
| G8 | History | NOT STARTED |
| G9 | Risk / Confidence | NOT STARTED |
| G10 | API | NOT STARTED |
| G11 | Web MVP | NOT STARTED |
| G12 | Validation | NOT STARTED |
| G13 | Production | NOT STARTED |
| G14 | Scale | NOT STARTED |

## G0 objective

Transform the conversation/product idea into durable authoritative repository context so future work does not depend on chat memory.

## G0 deliverables

- [x] `AGENTS.md`
- [x] `docs/MASTER_SPEC.md`
- [x] `docs/ARCHITECTURE.md`
- [x] `docs/ROI_METHODOLOGY.md`
- [x] `docs/DATA_CONTRACT.md`
- [x] `docs/STATUS.md`
- [x] User/Codex review confirms no critical contradiction
- [x] Git repository created
- [x] Baseline commit/tag created

## G0 acceptance criteria

G0 may be marked COMPLETE only when:
1. the six authoritative files exist in the local project repo,
2. user accepts the baseline scope,
3. no unresolved critical product/architecture contradiction remains,
4. repository is initialized in Git,
5. baseline is committed,
6. `STATUS.md` is updated to `G0 COMPLETE` and `G1 ACTIVE`.

## G1 objective

Create a reproducible local development skeleton with no game-specific business logic.

## G1 acceptance criteria

- [x] reproducible Python environment,
- [x] backend package imports cleanly,
- [x] PostgreSQL-compatible persistence setup,
- [x] migrations initialized,
- [x] deterministic test runner works,
- [x] `.env.example`,
- [x] no secrets committed,
- [x] `doctor` command exists and validates minimum environment,
- [x] CI/local quality commands documented,
- [x] one command starts required local development services or clearly documented minimal commands do,
- [x] all G1 tests/doctor checks green,
- [x] baseline Git commit for G1.

## G2 objective

Establish shared market-data source infrastructure without game-specific adapter logic.

## G2 acceptance criteria

- [x] provider-neutral market-data contracts live in `sources/`, not `adapters`,
- [x] normalized `Observation` objects preserve Data Contract fields, decimal-safe values, UTC timestamps, source provenance, and freshness/status,
- [x] source HTTP helper enforces configured timeouts, bounded retries, and structured errors,
- [x] at least one market-data provider connector parses recorded fixtures deterministically behind the provider-neutral interface,
- [x] PostgreSQL-compatible persistence for raw observations exists with an Alembic migration,
- [x] doctor/import checks include market-source configuration and package health without requiring live provider calls,
- [x] deterministic tests cover source parsing, missing/stale handling, HTTP errors/retries, persistence, and doctor behavior,
- [x] G2 documentation explains local commands, provider configuration, dependency choices, and scope boundaries,
- [x] no game adapter logic, ROI formulas, strategy calculations, frontend business logic, live integration tests, or provider secrets are added,
- [x] all tests, doctor checks, dependency checks, compile checks, and whitespace checks pass,
- [x] baseline Git commit for G2.

## G3 objective

Implement the generic ROI calculation core using manually verified deterministic scenarios, without live game adapters.

## G3 planned acceptance criteria

- [x] generic ROI engine lives in `engine/` and contains no game-specific checks,
- [x] money and ratio calculations are deterministic and Decimal-safe with explicit currencies,
- [x] engine input contract distinguishes sunk cost, recoverable entry cost, current recoverable value, initial operating reserve, capital at risk, rewards, recurring costs, transaction costs, and other costs,
- [x] engine calculates total capital, recoverable capital, capital at risk, gross nominal earnings, realizable earnings, operating/transaction/other costs, net earnings, break-even, 7D/30D/90D ROI on total capital, 7D/30D/90D ROI on capital at risk, and exit-adjusted P&L,
- [x] break-even basis is explicit and supports total capital, sunk cost, and capital-at-risk recovery targets,
- [x] required missing inputs fail explicitly and are never treated as zero,
- [x] deterministic manually-verifiable fixtures cover simple reward, transaction fee, recurring cost, slippage/executable quote, recoverable entry asset, break-even, exit-adjusted P&L, zero/negative earnings behavior, and missing input failure behavior,
- [x] G3 documentation explains engine scope, formulas implemented, and boundaries,
- [x] no game adapter logic, market provider changes, risk/confidence scoring, optimization, frontend business logic, or live integration tests are added,
- [x] all tests, doctor checks, dependency checks, compile checks, and whitespace checks pass,
- [x] baseline Git commit for G3.

## G4 objective

Implement the first game adapter only after a Data Feasibility Check passes for the selected game.

## G4 acceptance criteria

- [x] Data Feasibility Candidate Scan evaluates at least five currently active GameFi games with materially measurable earning economies,
- [x] selected Adapter #1 candidate has a documented `GO` decision with evidence and unresolved assumptions,
- [x] parked mRON candidate is not implemented or forced into the architecture,
- [x] adapter implements exactly one versioned strategy definition for Adapter #1,
- [x] provider access and HTTP/RPC behavior live in shared `sources/` connectors, not in the game adapter,
- [x] adapter maps game-specific economics into the generic G3 ROI engine without game-specific ROI-core branches,
- [x] adapter preserves LIVE / DERIVED / CONFIG classification for live observations, derived values, and configured assumptions,
- [x] required missing or stale inputs fail explicitly and are never substituted with zero,
- [x] deterministic golden fixture contains manually verified expected ROI values independent of live APIs,
- [x] live integration/probe path exists separately from deterministic tests,
- [x] G4 documentation explains feasibility result, modeled strategy, source boundaries, commands, and dependency choices,
- [x] no optimization, risk/confidence scoring, history, frontend, G5 work, or unrelated game adapter is added,
- [x] all tests, doctor checks, dependency checks, compile checks, and live probe pass,
- [x] baseline Git commit for G4.

## G4 adapter decision

Adapter #1 is `dfk-crystalvale-jeweler-cjewel-max-lock` version `v1`.

See `docs/DECISIONS/0001-adapter-1-feasibility-scan.md`.

## G5 objective

Implement a second game adapter for a materially different economy from DeFi Kingdoms Jeweler, focused on resource production, resource inputs/outputs, conversion/crafting economics, player-market realizable value, operating/transaction costs, entry capital, and exit value.

## G5 acceptance criteria

- [x] Data Feasibility Candidate Scan evaluates at least five active resource-production/crafting/conversion/player-market games,
- [x] Craft World is included in the scan and is not forced when required production/crafting data is not reliably machine-readable,
- [x] selected Adapter #2 candidate has a documented `GO` decision with evidence and unresolved assumptions,
- [x] Adapter #2 represents a materially different economy from DFK Jeweler,
- [x] adapter implements exactly one versioned strategy definition for Adapter #2,
- [x] provider access and HTTP behavior live in shared `sources/` connectors, not in the game adapter,
- [x] adapter maps game-specific economics into the generic G3 ROI engine without game-specific ROI-core branches,
- [x] any new capability is generic and outside the ROI core unless a documented architectural gap requires stopping,
- [x] adapter preserves LIVE / DERIVED / CONFIG classification for live observations, derived values, and configured assumptions,
- [x] required missing or stale inputs fail explicitly and are never substituted with zero,
- [x] deterministic golden fixture contains manually verified expected ROI values independent of live APIs,
- [x] live integration/probe path exists separately from deterministic tests,
- [x] G5 documentation explains feasibility result, modeled strategy, source boundaries, commands, dependency choices, and assumptions,
- [x] no optimization, risk/confidence scoring, history, frontend, G6 work, or unrelated game adapter is added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and live probe pass,
- [x] baseline Git commit for G5.

## G5 adapter decision

Adapter #2 is `farmers-world-axe-wood-production` version `v1`.

See `docs/DECISIONS/0002-adapter-2-feasibility-scan.md`.

## Decision backlog (not blockers)

- product/brand name,
- production hosting vendor,
- production market-data subscription/provider,
- final frontend framework,
- first three exact game adapters (must pass feasibility checks),
- monetization pricing,
- legal/commercial launch review.

## Current instruction to Codex

G6 is active. Do not implement G6 until the user explicitly asks to proceed.
