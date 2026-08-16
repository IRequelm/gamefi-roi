# GameFi ROI — Data Contract
Version: 0.1
Status: BASELINE; ADAPTER CONTRACT V1 FROZEN AT G7

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

## 7. Adapter Contract v1

Adapter Contract v1 is frozen at G7.

Code anchor:

```text
backend/app/adapters/contract.py
ADAPTER_CONTRACT_VERSION = "adapter-contract-v1"
```

Each adapter must expose a `build_engine_input(...)` method compatible with `StrategyAdapterV1`:

```text
build_engine_input(
  observations: tuple[Observation, ...],
  *,
  calculated_at: datetime | None = None
) -> AdapterResultV1
```

The adapter is responsible for game-specific interpretation and must fail explicitly if required inputs are missing, stale, invalid, or economically unsafe to model.

### AdapterResultV1

`AdapterResultV1` is the frozen result envelope produced by adapters.

Fields:

```text
contract_version
economics_input
classifications
derived_values
warnings
uncertainty_ranges
```

`economics_input` is a generic `StrategyEconomicsInput` consumed by the ROI engine. It must include:

- strategy identity and version,
- model version,
- reporting currency,
- sunk cost,
- recoverable entry cost,
- current recoverable value,
- initial operating reserve,
- capital at risk,
- gross nominal daily reward value,
- realizable daily reward value,
- recurring operating cost/day,
- transaction cost/day,
- other cost/day,
- cumulative net cash earnings,
- total cash invested to date,
- explicit break-even basis,
- input observation ids,
- assumptions.

The ROI engine receives only generic economics. It must not branch on game name, strategy id, asset symbol, provider name, or adapter module.

`classifications` maps metric names to:

- `LIVE`: directly current observation from on-chain, official API, or market API,
- `CONFIG`: verified strategy/config assumption,
- `DERIVED`: calculated from observations/config.

Every derived metric exposed in `derived_values` must have a `DERIVED` classification.

`derived_values` contains adapter-calculated Decimal metrics that are useful for explaining how the engine input was produced. Examples across G4-G6:

- DFK cJEWEL received, user reward share, projected JEWEL/day,
- Farmers World FWW/FWF/FWG daily resource quantities,
- Splinterlands expected wins/day and expected SPS/day.

`warnings` contains explicit limitations or modeling caveats that should travel with a result. Examples:

- expected value is not a guaranteed reward,
- reward-per-win is configured until direct live sampling is reliable,
- exit value is based on an approximation rather than an executable quote.

`uncertainty_ranges` maps a base metric to low/base/high metric names when the adapter has supportable range data. The range metrics themselves live in `derived_values`.

### StrategyEconomicsInput

Adapter Contract v1 uses the existing G3 engine input contract as the handoff to generic ROI math:

```text
StrategyEconomicsInput
  strategy_id
  strategy_version
  model_version
  reporting_currency
  capital
  rewards
  costs
  cumulative_net_cash_earnings
  total_cash_invested_to_date
  break_even_basis
  input_observation_ids
  assumptions
```

Capital:

- `sunk_cost`: unrecoverable entry capital,
- `recoverable_entry_cost`: acquisition value of assets intended to be recoverable,
- `current_recoverable_value`: current realizable exit value for recoverable assets,
- `initial_operating_reserve`: explicit initial reserve if required,
- `capital_at_risk`: adapter-defined economic exposure, documented in assumptions.

Rewards:

- deterministic reward flows use base daily values,
- probabilistic or performance-dependent reward flows use supportable expected value as the base daily value,
- low/high ranges are exposed in `uncertainty_ranges`; the G3 ROI engine still calculates base ROI only.

Costs:

- `operating_cost_day`,
- `transaction_cost_day`,
- `other_cost_day`.

Timing and horizon assumptions:

- Adapters normalize modeled flows to a daily base where the G3 stationary ROI engine is used.
- Season ends, claim intervals, cycles/day, battles/day, uptime, and caps remain adapter logic and must be recorded in observations, derived values, or assumptions where economically material.

### Shared Helpers

Shared v1 helpers live in `app.adapters.contract`:

- `verified_config_observation`,
- `derived_observation`,
- `live_observation`,
- `index_required_observations`,
- `observation_decimal_value`,
- `classify_observation`,
- Decimal validation helpers.

Adapters may add game-specific validation, but should not reimplement the shared provenance envelope or classification rules.

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
G7: Adapter Contract v1 is frozen.

## 16. Adapter versioning rules

Adapter Contract v1 is identified by:

```text
adapter-contract-v1
```

Backward-compatible changes allowed within v1:

- adding optional warning codes,
- adding optional derived metrics,
- adding optional uncertainty ranges,
- adding new source connectors,
- adding new game-specific strategy definitions and adapters that produce `AdapterResultV1`.

Breaking changes require Adapter Contract v2:

- removing or renaming `AdapterResultV1` fields,
- changing `StrategyEconomicsInput` semantics,
- changing LIVE / CONFIG / DERIVED meanings,
- requiring the ROI engine to know game ids or adapter types,
- changing required behavior for missing/stale observations,
- making low/base/high range output mandatory for deterministic strategies.

Existing adapters must keep their strategy ids and strategy versions stable unless the modeled game strategy itself changes.

## 17. Adding Adapter #4

Future Adapter #4 must be added without modifying the ROI core.

Required process:

1. Perform and document the Data Feasibility Check.
2. Add shared provider access under `sources/`; do not put provider URLs or HTTP/RPC logic in the adapter.
3. Add an explicit versioned strategy definition under `strategies/`.
4. Implement game-specific economic interpretation under `adapters/`.
5. Return `AdapterResultV1` with `StrategyEconomicsInput`, classifications, derived values, warnings, and uncertainty ranges where applicable.
6. Use shared adapter-contract helpers for config/derived/live observations and freshness checks.
7. Add a deterministic golden fixture with manually verified ROI.
8. Add contract-conformance coverage for the new adapter.
9. Add a separate live probe if live sources are used.
10. Stop and document an architectural gap if the economy cannot be represented as generic capital, reward, cost, timing, realizable value, and optional uncertainty metadata.

Do not modify `engine/` for game-specific mechanics. A core change is allowed only for a genuinely generic financial capability that is documented before implementation.
