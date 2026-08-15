# GameFi ROI — Data Contract
Version: 0.1
Status: BASELINE; ADAPTER CONTRACT NOT YET FROZEN

## 1. Purpose

Define a stable language between external data acquisition, game-specific interpretation, generic ROI calculation, and product output.

This document will evolve through G4–G7. Adapter Contract v1 freezes at G7.

## 2. Observation

An `Observation` represents an externally observed or verified configured fact.

Minimum conceptual fields:

```text
observation_id
entity_type
entity_id
metric
value
unit
quote_currency (optional)
source_provider
source_type
source_locator/reference
observed_at
retrieved_at
fresh_until
status
metadata
```

### Source types

Initial categories:
- `onchain`
- `official_api`
- `market_api`
- `official_docs`
- `verified_config`
- `derived_provider_data`

Do not overload `source_type` to mean confidence.

## 3. Observation status

At minimum:
- `fresh`
- `stale`
- `invalid`
- `missing`

Missing required input must not become numeric zero.

## 4. Asset identity

Every asset must have unambiguous identity.

For blockchain assets, prefer:
- chain,
- contract address,
- token standard/type,
- token id/collection attributes where necessary.

Symbols alone are not unique identifiers.

## 5. Game identity

Conceptual fields:
- game id/slug,
- official name,
- supported platforms,
- chain(s),
- official source references,
- status (candidate/active/parked/rejected),
- adapter version.

## 6. StrategyDefinition

Conceptual fields:

```text
strategy_id
strategy_version
game_id
name
description
entry_requirements
capital_configuration
behavior_assumptions
reward_model_parameters
cost_model_parameters
exit_route
time_horizon_assumptions
required_observation_metrics
config_dependencies
```

Strategies are versioned because game rules and modeling assumptions change.

## 7. StrategyInput

Adapter output consumed by the generic ROI engine.

The exact interface is deliberately not frozen until G7.

Candidate generic concepts:
- acquisition cash flows,
- recoverable assets and current exit values,
- period reward quantities,
- executable/realisable reward values,
- recurring costs,
- transaction costs,
- timing,
- uncertainty/quality metadata.

No game name checks should be necessary in the ROI engine.

## 8. StrategySnapshot

A calculated result at time `t`.

Conceptual fields:

```text
snapshot_id
strategy_id
strategy_version
model_version
calculated_at

total_capital
sunk_cost
recoverable_capital
capital_at_risk

gross_nominal_earnings_day
realizable_earnings_day
operating_cost_day
transaction_cost_day
net_earnings_day

break_even_days
roi_7d
roi_30d
roi_90d
exit_adjusted_pnl

confidence_score
risk_score
risk_label
trend_label

input_observation_ids
freshness_summary
warnings
```

Not all values are mandatory for every economy type; unavailable metrics must be explicit, not fake zeros.

## 9. Provenance

Every snapshot must be reproducible enough to answer:

> Why did the platform publish this value at this time?

Therefore retain:
- model version,
- strategy version,
- input observations/config versions,
- relevant assumptions.

## 10. Units

Never pass naked numbers across module boundaries.

Examples:
- `0.0021 RON`
- `40 MRON/hour`
- `18.22 USD`
- `12 hours`

Implementation may use typed models rather than literal unit objects, but the semantic contract must remain explicit.

## 11. Freshness

Each metric/source may have different freshness requirements.

Examples:
- token price: minutes,
- liquidity/pool state: minutes,
- game rule config: hours/days,
- subscription price: days,
- season end: until event change.

Freshness policy belongs to source/config definition, not arbitrary frontend logic.

## 12. Data Feasibility Check

Before implementing a new game adapter, record whether the following can be obtained reliably enough:

- reward formula/rate,
- entry requirements,
- entry asset price/value,
- reward asset identity,
- exit route,
- market price/quote route,
- liquidity/slippage inputs,
- recurring costs,
- claim/transaction costs,
- reward caps/season constraints,
- update/change detection,
- historical availability or ability to snapshot forward.

Result:
- `GO`
- `PARTIAL`
- `PARKED`
- `REJECTED`

A game may proceed with `PARTIAL` only when missing data can be modeled transparently and confidence reflects the limitation.

## 13. Live / Derived / Config presentation

For user-facing trust, metrics should be traceable to:
- `LIVE`: directly current observation,
- `DERIVED`: calculated from observations,
- `CONFIG`: rule/assumption.

This is presentation metadata; underlying source provenance remains more detailed.

## 14. Error handling

Connector/adapters return structured errors.

Do not:
- swallow exceptions and return zero,
- substitute yesterday's value without stale status,
- infer contract identity from ticker symbol only.

## 15. Contract freeze process

G4: observe requirements from economy type 1.
G5: adapt for economy type 2 without contaminating core.
G6: validate against economy type 3.
G7: freeze Adapter Contract v1 and document migration/version policy.
