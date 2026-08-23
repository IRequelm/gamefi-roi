# GameFi ROI — Data Contract
Version: 0.1
Status: BASELINE; ADAPTER CONTRACT V1 FROZEN AT G7

## 1. Purpose

Define a stable language between external data acquisition, opportunity-specific interpretation, generic ROI calculation, and product output.

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

## 5. Opportunity identity

G14 will introduce `Opportunity` as the canonical catalog entity. A game is one opportunity type.

Conceptual fields:

- opportunity id/slug,
- opportunity type,
- official name,
- supported platforms/devices,
- chain(s) when applicable,
- official source references,
- status (candidate/active/parked/rejected),
- adapter version when an adapter exists,
- compatibility game id when `opportunity_type = GAME`.

Planned opportunity types:

- `GAME`: blockchain game, GameFi, or play-to-earn economy.
- `DEPIN_NODE`: node, bandwidth, compute, storage, or resource-contribution network.
- `POINTS`: points/pre-token/reward-credit program where financial value may be unavailable.

### Game identity compatibility

Existing GameFi catalog records remain valid and must not be renamed during the G14 model expansion.

For `GAME` opportunities:

- `game_id` remains the stable backward-compatible alias of `opportunity_id`,
- existing `/api/v1/games` responses remain a filtered GAME-only compatibility view,
- existing strategy ids and versions remain unchanged unless the modeled strategy itself changes.

For non-game opportunities:

- new code should use `opportunity_id` and `opportunity_type`,
- `game_id` must not be treated as a semantic requirement by the ROI engine, risk/confidence scoring, history, or adapters.

## 6. Legacy game identity

Conceptual fields:
- game id/slug,
- official name,
- supported platforms,
- chain(s),
- official source references,
- status (candidate/active/parked/rejected),
- adapter version.

## 7. StrategyDefinition

Conceptual fields:

```text
strategy_id
strategy_version
opportunity_id
opportunity_type
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

`game_id` is required for existing GAME strategies for backward compatibility. New non-game strategies should use `opportunity_id` and `opportunity_type`; any legacy `game_id` alias must be documented and must not leak into the ROI engine as business logic.

## 8. Adapter Contract v1

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

The adapter is responsible for opportunity-specific interpretation and must fail explicitly if required inputs are missing, stale, invalid, or economically unsafe to model.

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

Adapters may add opportunity-specific validation, but should not reimplement the shared provenance envelope or classification rules.

## 9. StrategySnapshot

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

### G8 persistence contract

G8 persists historical calculation output through:

```text
backend/app/storage/history.py
backend/app/storage/models/strategy_history.py
strategy_snapshots
strategy_calculation_failures
```

`strategy_snapshots` records successful `AdapterResultV1` + ROI engine outputs. Each snapshot stores:

- strategy id and version,
- adapter contract version,
- model/engine version,
- calculated-at UTC timestamp,
- intended calculation window,
- reporting currency,
- capital metrics,
- earnings/cost metrics,
- ROI, break-even, and exit-adjusted P&L outputs,
- adapter derived values,
- uncertainty range metadata,
- warnings,
- LIVE / CONFIG / DERIVED classification summary,
- input observation ids,
- input observation references,
- freshness summary,
- assumptions.

Decimal financial values are serialized as exact decimal strings in JSON payloads rather than binary floats or truncated database numeric scales.

`strategy_calculation_failures` records failed calculation windows without fake numeric outputs. A stale, missing, invalid, or provider-failed input must create a failure record/log entry, not a fabricated snapshot.

### Snapshot idempotency

G8 idempotency key:

```text
sha256(
  strategy_id |
  strategy_version |
  adapter_contract_version |
  model_version |
  intended_window_start |
  intended_window_end
)
```

Repeated execution for the same strategy/version/model/contract/window returns the existing snapshot or failure record. A new strategy version, model version, adapter contract version, or calculation window creates a new historical record. Historical snapshots are append-only for new windows/versions and are not overwritten to backfill changed assumptions.

### History query surface

`HistoryRepository` supports:

- latest successful snapshot for a strategy,
- successful snapshots over an inclusive UTC time range,
- ordered time series,
- strategy/model/adapter-contract version summaries,
- recorded calculation failures.

This is a storage/query layer only. Product API endpoints, charts, risk/confidence scoring, and frontend history views are deferred to later gates.

### Scheduled recalculation surface

`ScheduledRecalculator` in `backend/app/jobs/recalculation.py` is the G8 scheduled recalculation boundary. It accepts versioned strategy calculation tasks, loads observations, calls the adapter, runs the generic ROI engine, and persists history. Each task is isolated: one failed adapter/provider records a failure and does not stop other strategy tasks in the same run.

The local probe command is:

```powershell
.\.venv\Scripts\python -m app.jobs.history_probe
```

Run it against a migrated local/test database. It uses deterministic existing-adapter observations and writes idempotent hourly snapshots.

### G9 scoring result

G9 persists independent confidence and risk scoring through:

```text
backend/app/risk/scoring.py
backend/app/storage/scoring.py
strategy_snapshot_scores
```

`strategy_snapshot_scores` is linked to `strategy_snapshots.snapshot_id`. Scores are versioned by `methodology_version`, so a later methodology can coexist with old historical scores.

Fields:

```text
score_id
snapshot_id
strategy_id
strategy_version
methodology_version
scored_at
confidence_score
confidence_label
confidence_contributions
risk_score
risk_label
risk_contributions
unavailable_factors
created_at
```

Current methodology version:

```text
risk-confidence-v1
```

Confidence and Risk are independent:

- Confidence starts at 100 and loses points for evidence quality/model trust issues.
- Risk starts at 0 and gains points for economic downside/instability.

Each contribution records the factor name, point impact, reason, and evidence. Factors without enough stored evidence are recorded in `unavailable_factors`; unavailable factors must not be guessed or treated as zero risk.

The local deterministic scoring probe is:

```powershell
.\.venv\Scripts\python -m app.risk.scoring_probe
```

### G10 API v1 response contract

G10 exposes a read-only product API under `/api/v1`. The API serves catalog, history, ranking, and score data from persisted snapshots and persisted scoring results.

Routes:

```text
GET /api/v1/health
GET /api/v1/games
GET /api/v1/games/{game_id}
GET /api/v1/strategies
GET /api/v1/strategies/{strategy_id}
GET /api/v1/strategies/{strategy_id}/latest
GET /api/v1/strategies/{strategy_id}/history
GET /api/v1/rankings
```

Snapshot payloads include:

- strategy id and version,
- game id, game name, chain, and economy type,
- capital metrics,
- daily earnings and cost metrics,
- break-even, ROI, and exit-adjusted P&L outputs,
- independent confidence and risk score payloads,
- warnings,
- freshness and last-calculated timestamp,
- adapter contract, ROI model, and scoring methodology versions,
- uncertainty ranges when present,
- LIVE / CONFIG / DERIVED classification summary.

JSON serialization policy:

- monetary values are `{ "amount": "<decimal-string>", "currency": "<unit>" }`,
- ratios and break-even days are exact decimal strings or `null`,
- unavailable optional values must include explicit availability/status/reason metadata,
- unavailable scores use `available=false` and `score=null`,
- monetary/financial values must not be serialized through binary floating-point.

Ranking filters are limited to modeled fields:

- `capital_min`,
- `capital_max`,
- `confidence_min`,
- `risk_max`,
- `game_id`,
- `chain`,
- `economy_type`.

Ranking order is deterministic:

```text
roi_total_30d desc
confidence_score desc
risk_score asc
calculated_at desc
strategy_id asc
```

Failed calculations from `strategy_calculation_failures` are not exposed as valid snapshots. Staleness is exposed in each snapshot's freshness payload; stale or unavailable values must never be converted to numeric zero.

### G11 web consumption contract

The public web MVP is a client of `/api/v1`, not a second calculation layer.

Frontend rules:

- construct supported ranking filters and pass them to `/api/v1/rankings`,
- display returned strategy, capital, earnings, ROI, freshness, warning, risk, confidence, uncertainty, and version fields,
- show insufficient-history and unavailable-value states explicitly,
- treat Decimal-sensitive strings as display data rather than binary-float calculation inputs,
- do not call provider URLs, blockchain RPCs, adapters, scheduler jobs, or storage internals.

### G14 Opportunity model and outbound/referral metadata contract

G14 must expand the catalog model from `Game` to `Opportunity` without breaking existing adapters or API clients.

Conceptual `OpportunityCatalogEntry` fields:

```text
opportunity_id
opportunity_type
name
status
platforms
chains
economy_types
reward_asset_or_points_type
value_realization_status
official_source_references
data_feasibility_status
strategy_ids
legacy_game_id (optional)
```

`value_realization_status` examples:

- `realizable`: reward has a lawful executable claim/market route,
- `non_transferable_points`: points have no current realizable financial value,
- `future_airdrop_claim`: possible future reward exists but value/timing is not deterministic,
- `unknown`: value route is not sufficiently documented.

Points-only opportunities may produce points/day or contribution metrics, but financial ROI fields must be unavailable unless a lawful, reproducible, realizable value route exists. Missing realizable value must not become zero.

G14 may introduce structured outbound destination metadata and a first-party redirect layer.

Conceptual `OutboundDestination` fields:

```text
destination_id
destination_slug
opportunity_id
opportunity_type
game_id (optional compatibility alias)
strategy_id (optional)
destination_type
label
target_url
status
is_affiliate
affiliate_program_id (optional)
commercial_relationship
disclosure_text
source_reference
reviewed_at
expires_at (optional)
allowed_surfaces
```

`destination_type` examples:

- official_site,
- play,
- marketplace,
- docs,
- community,
- referral.

`commercial_relationship` examples:

- none,
- affiliate,
- sponsor,
- partner.

The first-party redirect route should be shaped as:

```text
GET /go/{destination_slug}
```

Redirect requirements:

- resolve only allowlisted active `OutboundDestination` records,
- fail closed for missing, disabled, expired, malformed, or unreviewed destinations,
- never accept arbitrary user-supplied target URLs,
- preserve required disclosure metadata for API/web consumers,
- avoid committing secrets or private partner tokens.

Outbound/referral metadata is not a strategy observation, not an adapter input, not a derived ROI value, and not a score factor.

Native program referral rewards, such as a DePIN network awarding points for referred users, are distinct from GameFi ROI commercial referral metadata. Native referral economics may only be modeled as part of a strategy when evidence is public/authorized, versioned, and disclosed. A GameFi ROI affiliate relationship must never cause a native referral bonus to be added to ROI.

### G14 API implementation

G14 adds these read-only API routes without changing the G10 compatibility routes:

```text
GET /api/v1/opportunities
GET /api/v1/opportunities/{opportunity_id}
```

`/api/v1/games` remains a GAME-only compatibility view. Existing strategy ids, strategy versions, `game_id` values, and snapshot payload semantics remain stable.

Opportunity and strategy payloads may include outbound destination metadata. The exposed destination payload includes:

- `destination_id`,
- `destination_slug`,
- `opportunity_id`,
- `opportunity_type`,
- optional `game_id`,
- optional `strategy_id`,
- `destination_type`,
- `label`,
- first-party `redirect_url`,
- reviewed `official_url`,
- optional `referral_url`,
- optional `referral_code`,
- optional `affiliate_program`,
- `status`,
- `is_affiliate`,
- `commercial_relationship`,
- `disclosure_text`,
- `source_reference`,
- `reviewed_at`,
- `verification_status`,
- `allowed_surfaces`.

The public web must use the first-party `redirect_url` for Start/Play/Open calls. It may display disclosure text and commercial relationship status, but must not use those fields to recalculate ROI, score confidence/risk, create snapshots, or reorder organic rankings.

G14 redirect behavior:

- `GET /go/{destination_slug}` resolves only active, verified, allowlisted destination records,
- missing, disabled, expired, malformed, non-HTTPS, or unreviewed destinations return an error instead of redirecting,
- no arbitrary target URL query parameter is accepted,
- G14 logs only a minimal aggregate redirect event and does not set tracking cookies or store per-user click records,
- affiliate attribution/reporting, conversion tracking, sponsored placements, and commercial analytics remain G15.

### G15 monetization data boundary

G15 may add affiliate attribution/reporting, sponsored placements, and commercial analytics.

Commercial entities such as campaigns, sponsors, clicks, conversions, and revenue must be stored and queried separately from:

- `strategy_snapshots`,
- `strategy_snapshot_scores`,
- adapter observations,
- ROI engine inputs/outputs,
- organic ranking inputs.

Affiliate/sponsor relationships must never affect ROI, Risk, Confidence, historical strategy snapshots, validation results, or organic ranking order. Sponsored placements must be explicit commercial surfaces, not modified organic results.

G15 commercial records:

`OutboundClickEvent`

- `event_id`,
- `destination_slug`,
- `destination_id`,
- `opportunity_id`,
- `opportunity_type`,
- optional `game_id`,
- optional `strategy_id`,
- `destination_type`,
- `referral_status`,
- `commercial_relationship`,
- `is_affiliate`,
- `target_url_kind` (`official` or `referral`),
- optional `source_page`,
- optional `placement`,
- optional coarse session id,
- coarse `user_agent_category`,
- `occurred_at`,
- `created_at`.

The `/go/{destination_slug}` route may persist click events after destination validation. It must not accept an arbitrary target URL, set tracking cookies, store raw private identifiers, or require personal tracking. If no active referral URL exists, the redirect uses the official URL.

Referral lifecycle statuses:

- `NONE`,
- `DISCOVERED`,
- `RESEARCH_REQUIRED`,
- `APPLICATION_REQUIRED`,
- `PENDING`,
- `VERIFIED`,
- `ACTIVE`,
- `PAUSED`,
- `REJECTED`,
- `EXPIRED`,
- `NO_PROGRAM_FOUND`,
- `REVERIFY`.

`ReferralProgram` records store lifecycle status, affiliate program name if any, disclosure text, verification status/timestamps, and evidence. They are commercial metadata only.

`RevenueAttribution` records are partner/manual imports linked to destinations, opportunities, and optionally strategies. Only `VERIFIED` records may contribute to reporting metrics. Pending or rejected attribution must not be counted as conversion or revenue.

G15 commercial metrics:

- outbound clicks,
- coarse sessions where available,
- CTR only when a verified impression denominator exists,
- verified conversions,
- verified revenue,
- EPC only as `verified revenue / outbound clicks`,
- conversion rate only when verified conversions and outbound clicks both exist.

Unavailable denominators or unverified partner data remain unavailable; they must not be presented as zero.

`SponsoredPlacement` records contain placement id, opportunity id, optional strategy id, surface, status, label, disclosure text, campaign/sponsor metadata, active window, and audit trail. API/web responses must distinguish sponsored placement collections from organic ranking results.

### G17 referral operations data contract

G17 extends the G14/G15 referral foundation with operator workflow metadata. These records remain commercial operations data only. They must not be used by the ROI engine, adapter contracts, risk/confidence scoring, historical snapshots, validation, or organic ranking inputs.

Coverage states:

- `REFERRAL_ACTIVE`: reviewed active referral link is safe and current,
- `REFERRAL_PENDING`: affiliate/referral application is pending,
- `REFERRAL_MISSING`: no reviewed referral program metadata exists,
- `REFERRAL_RESEARCH_REQUIRED`: operator must research or apply before any referral can be used,
- `NO_PROGRAM_FOUND`: operator found evidence that no program currently exists,
- `REFERRAL_EXPIRED`: stored referral expires before or at the evaluation time,
- `REFERRAL_PAUSED`: program/link is intentionally paused,
- `REFERRAL_REVERIFY`: program/link requires periodic re-verification.

Referral operation metadata:

- `official_url`,
- `referral_url`,
- `referral_code`,
- `referral_url_template`,
- `affiliate_program`,
- `program_type`,
- `commission_description`,
- `eligibility_notes`,
- `geographic_restrictions`,
- `referral_status`,
- `verification_status`,
- `evidence_url`,
- `evidence_reference`,
- `applied_at`,
- `verified_at`,
- `last_checked_at`,
- `expires_at`,
- `operator_notes`,
- `updated_at`.

Safe outbound URL rules:

- official/referral URLs must use HTTPS,
- URL schemes such as `javascript:` and `data:` are invalid,
- localhost, loopback, private-network, link-local, and reserved IP destinations are invalid,
- active referral URL hosts must match the reviewed official-domain relationship,
- active template-based referral URLs must include a referral code and a `{code}` placeholder,
- invalid or missing referral metadata must fall back to the reviewed official URL and must not create an arbitrary redirect.

Referral task types:

- `FIND_REFERRAL_PROGRAM`,
- `APPLY_TO_PROGRAM`,
- `VERIFY_REFERRAL_LINK`,
- `RECHECK_PENDING_APPLICATION`,
- `REVERIFY_PROGRAM`,
- `REPLACE_EXPIRED_LINK`.

Only one open task may exist for the same opportunity and task type. Re-running the stored-metadata health check must update the existing open task rather than creating duplicates.

Manual revenue attribution remains explicit:

- partner/operator-entered records default to `PENDING`,
- only `VERIFIED` records may contribute to commercial analytics,
- a verified revenue record requires settlement or evidence reference,
- click counts do not imply revenue and unverified revenue must not count as verified revenue.

Operator console requirements:

- credentials come only from `GAMEFI_OPERATOR_USERNAME` and `GAMEFI_OPERATOR_PASSWORD`,
- there is no default password and no public writable route,
- Basic Auth responses do not require cookie-backed CSRF handling,
- operator pages are `noindex,nofollow`, excluded from sitemap, and disallowed by robots,
- operator routes are excluded from the public OpenAPI schema.

### G16 search and acquisition data contract

G16 public discovery data is additive. It must not modify strategy snapshots, risk/confidence scores, ROI outputs, adapter results, organic rankings, sponsored placement order, or monetization attribution logic.

Search-rendered public pages are generated from existing read models and catalog data:

- `StrategySummary`,
- `StrategySnapshotPayload`,
- `RankingItem`,
- `OpportunitySummary`,
- `OpportunityDetail`,
- `GameDetail`,
- outbound destination payloads,
- sponsored placement payloads where an existing page already renders commercial surfaces.

Display formatting may convert exact API Decimal strings into human-readable text at the HTML/UI boundary. The exact API values remain authoritative and must remain available via API responses and title attributes where useful. Formatting must never feed back into the ROI engine, snapshot persistence, scoring, or ranking.

Canonical public URL records contain:

- canonical path,
- absolute URL derived from `GAMEFI_PUBLIC_BASE_URL`,
- last modified timestamp/date derived from stored snapshot or catalog review evidence,
- change frequency,
- priority.

The canonical inventory must exclude:

- `/api`,
- `/go`,
- assets,
- admin/internal/debug/test paths,
- arbitrary query permutations,
- unreviewed arbitrary URLs.

Query-string pages render `noindex,follow` and canonicalize to the clean path unless explicitly modeled as curated landing pages under a stable slug.

Structured data is limited to truthful schema types that match the page:

- `Organization`,
- `WebSite`,
- `WebPage`,
- `BreadcrumbList`.

Do not use `Product`, `Review`, `Offer`, `FAQ`, `HowTo`, aggregate ratings, or review snippets unless future gates add evidence and review processes that satisfy those schemas.

`InboundLandingEvent` records:

- `event_id`,
- `landing_path`,
- optional `referrer_domain`,
- optional `utm_source`,
- optional `utm_medium`,
- optional `utm_campaign`,
- normalized `channel`,
- optional coarse session id,
- `occurred_at`,
- `created_at`.

Allowed normalized acquisition channels:

- `google`,
- `bing`,
- `chatgpt`,
- `perplexity`,
- `x`,
- `reddit`,
- `direct`,
- `referral`,
- `other`.

Inbound acquisition records are not conversion records and are not affiliate attribution. They may be used for acquisition reporting only. They must not include fingerprinting, raw IP storage, cookies, private wallet/user identifiers, or invasive personal tracking.

IndexNow submissions:

- require `GAMEFI_INDEXNOW_KEY`,
- expose only the protocol-required `{key}.txt` verification file at the public root,
- submit only canonical public URLs belonging to `GAMEFI_PUBLIC_BASE_URL`,
- reject `/api`, `/go`, query URLs, and wrong-host URLs before any outbound notification,
- use the official IndexNow batch endpoint,
- use timeouts and bounded retries,
- redact the key from logs/errors,
- are manual/operator-triggered and must not run on normal page requests.

## 10. Provenance

Every snapshot must be reproducible enough to answer:

> Why did the platform publish this value at this time?

Therefore retain:
- model version,
- strategy version,
- input observations/config versions,
- relevant assumptions.

## 11. Units

Never pass naked numbers across module boundaries.

Examples:
- `0.0021 RON`
- `40 MRON/hour`
- `18.22 USD`
- `12 hours`

Implementation may use typed models rather than literal unit objects, but the semantic contract must remain explicit.

## 12. Freshness

Each metric/source may have different freshness requirements.

Examples:
- token price: minutes,
- liquidity/pool state: minutes,
- game rule config: hours/days,
- subscription price: days,
- season end: until event change.

Freshness policy belongs to source/config definition, not arbitrary frontend logic.

## 13. Data Feasibility Check

Before implementing a new opportunity adapter, record whether the following can be obtained reliably enough:

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

For `DEPIN_NODE` or `POINTS` opportunities, also record:

- node/device/account requirements,
- uptime, bandwidth, compute, storage, or data-signal measurement rules,
- points identity and whether points are transferable,
- points-to-token/USDC/claim conversion evidence, if any,
- whether points have no monetary value under official terms,
- dashboard/API machine-readability and whether automated collection is permitted,
- device/network operating costs and user-borne resource costs,
- jurisdiction, KYC, sanctions, or eligibility restrictions,
- native referral reward rules separated from GameFi ROI commercial referral metadata.

Result:
- `GO`
- `PARTIAL`
- `PARKED`
- `REJECTED`

An opportunity may proceed with `PARTIAL` only when missing data can be modeled transparently and confidence reflects the limitation. A points-only opportunity with no realizable value route may not publish financial ROI; it may only publish non-financial production metrics and warnings until value evidence exists.

## 14. Live / Derived / Config presentation

For user-facing trust, metrics should be traceable to:
- `LIVE`: directly current observation,
- `DERIVED`: calculated from observations,
- `CONFIG`: rule/assumption.

This is presentation metadata; underlying source provenance remains more detailed.

## 15. Error handling

Connector/adapters return structured errors.

Do not:
- swallow exceptions and return zero,
- substitute yesterday's value without stale status,
- infer contract identity from ticker symbol only.

## 16. Contract freeze process

G4: observe requirements from economy type 1.
G5: adapt for economy type 2 without contaminating core.
G6: validate against economy type 3.
G7: Adapter Contract v1 is frozen.

## 17. Adapter versioning rules

Adapter Contract v1 is identified by:

```text
adapter-contract-v1
```

Backward-compatible changes allowed within v1:

- adding optional warning codes,
- adding optional derived metrics,
- adding optional uncertainty ranges,
- adding new source connectors,
- adding new game-specific or opportunity-specific strategy definitions and adapters that produce `AdapterResultV1`.

Breaking changes require Adapter Contract v2:

- removing or renaming `AdapterResultV1` fields,
- changing `StrategyEconomicsInput` semantics,
- changing LIVE / CONFIG / DERIVED meanings,
- requiring the ROI engine to know game ids, opportunity ids, opportunity types, or adapter types,
- changing required behavior for missing/stale observations,
- making low/base/high range output mandatory for deterministic strategies.

Existing adapters must keep their strategy ids and strategy versions stable unless the modeled game strategy itself changes.

## 18. Adding a future adapter

A future game, DePIN/node, or points opportunity adapter must be added without modifying the ROI core.

Required process:

1. Perform and document the Data Feasibility Check for the opportunity type.
2. Add shared provider access under `sources/`; do not put provider URLs or HTTP/RPC logic in the adapter.
3. Add an explicit versioned strategy definition under `strategies/`.
4. Implement opportunity-specific economic interpretation under `adapters/`.
5. Return `AdapterResultV1` with `StrategyEconomicsInput`, classifications, derived values, warnings, and uncertainty ranges where applicable.
6. Use shared adapter-contract helpers for config/derived/live observations and freshness checks.
7. Add a deterministic golden fixture with manually verified ROI.
8. Add contract-conformance coverage for the new adapter.
9. Add a separate live probe if live sources are used.
10. Stop and document an architectural gap if the economy cannot be represented as generic capital, reward, cost, timing, realizable value, and optional uncertainty metadata.

Do not modify `engine/` for game-specific, node-specific, or points-program-specific mechanics. A core change is allowed only for a genuinely generic financial capability that is documented before implementation.
