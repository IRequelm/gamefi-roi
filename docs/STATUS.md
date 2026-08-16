# GameFi ROI — Project Status

Updated: 2026-08-16
Project version: 0.1

## Current state

**ACTIVE GATE: G10 — API**

G9 is complete and frozen in the G9 baseline Git commit.

Do not implement G10 until the user explicitly asks to proceed.

## Gate board

| Gate | Name | Status |
|---|---|---|
| G0 | Freeze | COMPLETE |
| G1 | Skeleton | COMPLETE |
| G2 | Market Data | COMPLETE |
| G3 | ROI Core | COMPLETE |
| G4 | Adapter #1 | COMPLETE |
| G5 | Adapter #2 | COMPLETE |
| G6 | Adapter #3 | COMPLETE |
| G7 | Interface Freeze | COMPLETE |
| G8 | History | COMPLETE |
| G9 | Risk / Confidence | COMPLETE |
| G10 | API | ACTIVE |
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

## G6 objective

Implement a third game adapter for a materially different economy from DeFi Kingdoms Jeweler and Farmers World, focused on seasonal, probabilistic, performance-dependent, leaderboard, combat, quest, or similar reward economics.

## G6 acceptance criteria

- [x] Data Feasibility Candidate Scan evaluates at least five active GameFi candidates in the target economy class,
- [x] selected Adapter #3 candidate has a documented `GO` decision with evidence and unresolved assumptions,
- [x] Adapter #3 represents a materially different economy from DFK Jeweler and Farmers World,
- [x] adapter implements exactly one versioned strategy definition for Adapter #3,
- [x] provider access and HTTP behavior live in shared `sources/` connectors, not in the game adapter,
- [x] adapter maps uncertainty/time-dependent game economics into the generic G3 ROI engine without game-specific ROI-core branches,
- [x] if rewards are probabilistic or performance-dependent, expected value is used only under explicit assumptions and uncertainty is exposed,
- [x] adapter preserves LIVE / DERIVED / CONFIG classification for live observations, derived values, and configured assumptions,
- [x] required missing or stale inputs fail explicitly and are never substituted with zero,
- [x] deterministic golden fixture contains manually verified expected ROI values independent of live APIs,
- [x] live integration/probe path exists separately from deterministic tests,
- [x] G6 documentation explains feasibility result, modeled strategy, source boundaries, commands, dependency choices, and assumptions,
- [x] no optimization, risk/confidence scoring, history, frontend, G7 work, or unrelated game adapter is added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and live probe pass,
- [x] baseline Git commit for G6.

## G6 adapter decision

Adapter #3 is `splinterlands-modern-ranked-sps-ev` version `v1`.

See `docs/DECISIONS/0003-adapter-3-feasibility-scan.md`.

## Decision backlog (not blockers)

- product/brand name,
- production hosting vendor,
- production market-data subscription/provider,
- final frontend framework,
- monetization pricing,
- legal/commercial launch review.

## G7 objective

Freeze Adapter Contract v1 by reviewing patterns from the first three materially different adapters and documenting the stable adapter/source/strategy boundaries for future gates.

## G7 acceptance criteria

- [x] DFK Jeweler, Farmers World, and Splinterlands adapters are compared for generic inputs, generic outputs, game-specific mechanics, duplicated patterns, and accidental engine assumptions,
- [x] Adapter Contract v1 is defined and supports all three completed adapters without game-name conditionals in the ROI core,
- [x] contract explicitly covers strategy identity/version, capital decomposition, recoverable assets/value, deterministic or expected reward flows, uncertainty ranges, recurring costs, transaction costs, timing assumptions, realizable exit value, required observations, LIVE / CONFIG / DERIVED provenance, and warnings/limitations,
- [x] necessary shared contract/helpers are implemented without aesthetic-only refactors,
- [x] existing golden fixture ROI outputs remain backward-equivalent,
- [x] contract-level tests prove all three adapters conform to Adapter Contract v1,
- [x] `docs/DATA_CONTRACT.md` is updated with frozen Adapter Contract v1 and versioning rules,
- [x] future Adapter #4 process is documented without requiring ROI-core modification,
- [x] no new game adapter, history, risk/confidence, API, frontend, optimization, or new product feature is added,
- [x] all tests, doctor checks, dependency checks, compile checks, and whitespace checks pass,
- [x] baseline Git commit for G7.

## G7 adapter contract decision

Adapter Contract v1 is `adapter-contract-v1`.

The code anchor is `backend/app/adapters/contract.py`. The authoritative documentation is `docs/DATA_CONTRACT.md`.

## G8 objective

Add historical strategy snapshot persistence and retrieval using the frozen Adapter Contract v1 outputs, without changing adapter economics.

## G8 acceptance criteria

- [x] successful `AdapterResultV1` + ROI engine outputs persist as historical strategy snapshots,
- [x] snapshots include strategy id/version, adapter contract version, model/engine version, calculated-at UTC timestamp, intended calculation window, capital metrics, earnings/cost metrics, ROI/break-even/exit-adjusted outputs, uncertainty range metadata, warnings, classification summary, input observation references, and freshness summary,
- [x] historical records preserve enough observations, assumptions, classifications, warnings, versions, timestamps, and Decimal-safe outputs to explain why a result was published at that time,
- [x] PostgreSQL-compatible history schema exists with an Alembic migration,
- [x] repository/query layer retrieves latest snapshot, time-range snapshots, ordered time series, and strategy/model version information,
- [x] scheduled recalculation runner exists for the modular monolith without distributed queues or microservices,
- [x] failed adapter/provider calculations are isolated, logged as failures, and do not create fake numeric snapshots,
- [x] stale or missing required inputs fail explicitly and are not substituted with zero,
- [x] repeated execution for the same strategy/version/model/contract/window is idempotent and does not create duplicate snapshots,
- [x] historical snapshots are retained across strategy/model version changes,
- [x] deterministic tests cover persistence, latest snapshot, ordered history, version changes, provenance, duplicate/idempotency behavior, failure isolation, stale input behavior, and uncertainty metadata,
- [x] local history/scheduler probe runs with the existing adapters,
- [x] no risk/confidence scoring, product API endpoints, frontend, optimization, or new game adapters are added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and the history probe pass,
- [x] baseline Git commit for G8.

## G8 history decision

Historical snapshot idempotency is keyed by `strategy_id`, `strategy_version`, `adapter_contract_version`, `model_version`, `intended_window_start`, and `intended_window_end`.

Successful calculations are stored in `strategy_snapshots`; failures are stored separately in `strategy_calculation_failures` without numeric ROI output.

See `docs/DATA_CONTRACT.md`.

## G9 objective

Implement independent, transparent confidence and risk scoring for historical strategy snapshots.

## G9 acceptance criteria

- [x] confidence and risk are implemented as independent concepts and are not merged into one score,
- [x] confidence scores measure calculation/data trust on a 0-100 scale where higher is more trustworthy,
- [x] risk scores measure economic downside/instability on a 0-100 scale where higher is more risky,
- [x] confidence labels are documented as LOW, MODERATE, and HIGH,
- [x] risk labels are documented as LOW, MEDIUM, HIGH, and VERY HIGH,
- [x] scoring thresholds and weights are documented in `docs/ROI_METHODOLOGY.md`,
- [x] score results are decomposable into factor-level point contributions with evidence and explanations,
- [x] factors without stored evidence are marked unavailable instead of guessed,
- [x] G8 history is used for trend risk only when at least three comparable snapshots exist,
- [x] confidence penalizes CONFIG-heavy strategies separately from engine correctness,
- [x] risk captures supported evidence for lock/exit penalties, thin liquidity/slippage, probabilistic uncertainty, weak yield, recoverable exit loss, and adapter warnings,
- [x] versioned scoring results are persisted in `strategy_snapshot_scores` linked to historical snapshots,
- [x] scoring methodology version is preserved as `risk-confidence-v1`,
- [x] deterministic tests cover high-confidence/low-risk, high-confidence/high-risk, low confidence, stale data, missing optional history, heavy CONFIG dependence, poor liquidity/slippage, lock/exit penalty, probabilistic uncertainty, score explanations/contributions, methodology versioning, and the three existing adapters,
- [x] local scoring probe runs against the existing DFK Jeweler, Farmers World, and Splinterlands adapters,
- [x] no API product endpoints, frontend, optimization, new adapters, portfolio features, or production deployment are added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, history probe, and scoring probe pass,
- [x] baseline Git commit for G9.

## G9 scoring decision

Scoring methodology version is `risk-confidence-v1`.

Scores are stored separately from snapshots in `strategy_snapshot_scores`, uniquely by `snapshot_id` and `methodology_version`.

Current deterministic probe scores:

| Strategy | Confidence | Risk |
|---|---:|---:|
| `dfk-crystalvale-jeweler-cjewel-max-lock` | 82 HIGH | 79 VERY HIGH |
| `farmers-world-axe-wood-production` | 77 MODERATE | 31 MEDIUM |
| `splinterlands-modern-ranked-sps-ev` | 39 LOW | 100 VERY HIGH |

## Current instruction to Codex

G10 is active. Do not implement G10 until the user explicitly asks to proceed.
