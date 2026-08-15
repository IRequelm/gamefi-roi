# GameFi ROI — Project Status

Updated: 2026-08-15
Project version: 0.1

## Current state

**ACTIVE GATE: G3 — ROI Core**

G2 is complete and frozen in the G2 baseline Git commit.

Do not implement G3 until the user explicitly asks to proceed.

## Gate board

| Gate | Name | Status |
|---|---|---|
| G0 | Freeze | COMPLETE |
| G1 | Skeleton | COMPLETE |
| G2 | Market Data | COMPLETE |
| G3 | ROI Core | ACTIVE |
| G4 | Adapter #1 | NOT STARTED |
| G5 | Adapter #2 | NOT STARTED |
| G6 | Adapter #3 | NOT STARTED |
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

G3 must satisfy the G3 acceptance principle in `docs/ROI_METHODOLOGY.md` before it can be marked complete.

## Decision backlog (not blockers)

- product/brand name,
- production hosting vendor,
- production market-data subscription/provider,
- final frontend framework,
- first three exact game adapters (must pass feasibility checks),
- monetization pricing,
- legal/commercial launch review.

## Current instruction to Codex

G3 is active. Do not implement G3 until the user explicitly asks to proceed.
