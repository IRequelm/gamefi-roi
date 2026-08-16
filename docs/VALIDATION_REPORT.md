# G12 Validation Report

Validation date: 2026-08-16

Gate: G12 - Validation

Scope: validate the MVP end-to-end for the three existing strategies without adding adapters, production deployment, auth, portfolio, alerts, monetization, AI, optimization, or major UI redesign.

## Recommendation

Overall result: CONDITIONAL PASS.

No public-beta-blocking correctness issue remains after the G12 fix that changed the web UI to render API ROI ratio strings exactly instead of converting them to percentages.

The MVP can advance to G13 with visible caveats:

- DFK Jeweler: CONDITIONAL PASS.
- Farmers World: CONDITIONAL PASS.
- Splinterlands: CONDITIONAL PASS.

Conditional status means calculations are internally reproducible and product surfaces agree, but strategy assumptions remain weak enough that public beta must continue to show warnings, confidence/risk explanations, freshness, and LIVE / CONFIG / DERIVED provenance.

## Validation Tolerances

Deterministic fixture checks use exact Decimal equality. Manual validation, adapter output, ROI engine output, persisted snapshot payloads, API JSON strings, and rendered web financial strings must match exactly where they use the same input set.

Live probes are point-in-time checks. Live values are not compared to golden fixture values because provider refresh time, market price, gas, and liquidity move. A live probe passes when required observations are retrieved lawfully through the configured source connectors, are fresh at calculation time, preserve provenance, and produce explicit numeric outputs or explicit unavailable states without zero substitution.

## Independent Validation Method

The independent validator lives in `backend/app/validation/e2e.py`. It does not import or call the ROI engine calculator. It recomputes:

- DFK cJEWEL share and reward projection.
- Farmers World daily resource production and input costs.
- Splinterlands expected wins, SPS, realization haircut, and low/base/high ranges.
- Generic total capital, recoverable capital, capital at risk, net/day, break-even, ROI, and exit-adjusted P&L.

The validator is exercised by `backend/tests/test_g12_validation.py` and can be run directly with:

```powershell
.\.venv\Scripts\python -m app.validation.e2e
```

## Product Snapshot Results

These are the deterministic stored sample outputs used by the API and web probes.

| Strategy | Capital | Recoverable | Net/day | Break-even days | 30D ROI | Exit P&L | Confidence | Risk |
|---|---:|---:|---:|---:|---:|---:|---|---|
| DFK Jeweler | 250.00 USD | 125.00 USD | 0.4885 USD | 511.7707267144319344933469806 | 0.05862 | -125.00 USD | 82 HIGH | 79 VERY HIGH |
| Farmers World | 1.80 USD | 1.70 USD | 0.0504 USD | 35.71428571428571428571428571 | 0.84 | -0.10 USD | 77 MODERATE | 31 MEDIUM |
| Splinterlands | 10.00 USD | 0 USD | 0.01722500 USD | 580.5515239477503628447024673 | 0.051675 | -10.00 USD | 39 LOW | 100 VERY HIGH |

## Source And Assumption Matrix

| Strategy | Entry Capital Source | Reward Formula | LIVE Inputs | CONFIG Assumptions | DERIVED Outputs | Exit / Slippage | Costs | Beta Classification |
|---|---|---|---|---|---|---|---|---|
| DFK Jeweler | JEWEL entry value from DFK AMM-derived USD valuation. | `locked_jewel * lock_days / max_lock_days`, then user cJEWEL share times yesterday reward JEWEL. | Yesterday cJEWEL balance and yesterday reward JEWEL. | 1,000 JEWEL, 1,095-day max lock, emergency withdrawal penalty, claim interval, gas units. | Entry value, emergency exit value, JEWEL reference price, realizable reward value, claim transaction cost. | DFK AMM quote path with emergency-exit recoverable value and slippage-aware reward realization. | Claim transaction cost from gas price and configured gas units; no recurring operating cost. | Acceptable only with visible lock/exit/gas warnings. Not a correctness blocker. |
| Farmers World | AtomicAssets floor value times WAX/USD in live path; deterministic probe uses configured derived source values. | `tool_count * cycles_per_day * FWW per cycle`, with FWF/FWG inputs per cycle. | Live probe reads Alcor markets, AtomicAssets floor, WAX price. Deterministic stored sample has CONFIG and DERIVED adapter inputs only. | Tool count, cycle cadence, FWW output, FWF/FWG inputs, explicit WAX transaction/resource cost assumption. | Entry/exit USD value, FWW realizable value, FWF/FWG operating cost, transaction cost. | Alcor quote/market source with low-volume liquidity evidence. | FWF/FWG input costs; WAX resource/transaction cost is explicitly zero in the sample. | Acceptable only with visible zero-cost and liquidity warnings. Not a correctness blocker. |
| Splinterlands | Official starter pack price for spellbook cost. | Expected value: `battles/day * win probability * SPS/win`, then SPS price and realization haircut. | Official Splinterlands settings, season, energy values, and SPS reference market price. | Battles/day, win probability low/base/high, SPS per win, realization haircut, rental cost, zero transaction cost. | Expected wins/day, expected SPS/day, realizable reward ranges, net earnings ranges, sustainable energy. | SPS reference price with configured realization haircut; no executable swap quote yet. | Card rental cost and explicit zero transaction cost. | Acceptable only with visible expected-value and config-heavy warnings. Not a correctness blocker. |

## Manual Vs Engine

Golden fixtures are manually recomputed by the independent validator and then compared to adapter and engine output.

| Strategy | Manual Fixture Result | Adapter/Engine Comparison |
|---|---|---|
| DFK Jeweler | total capital 200.00, net/day 0.980, break-even 204.0816326530612244897959184, 30D ROI 0.147, exit P&L -100.50 | Exact Decimal match. |
| Farmers World | total capital 10.00, net/day 0.73, break-even 13.69863013698630136986301370, 30D ROI 2.19, exit P&L -0.50 | Exact Decimal match. |
| Splinterlands | total capital 10.00, net/day 0.01722500, break-even 580.5515239477503628447024673, 30D ROI 0.051675, exit P&L -10.00 | Exact Decimal match. |

## Pipeline Validation

Validated path:

`source fixture/probe -> adapter inputs -> ROI engine outputs -> persisted snapshot -> API response -> web display`

Results:

- Source fixtures match independent manual calculations exactly.
- Adapter outputs match independent manual calculations exactly.
- ROI engine outputs match independent manual calculations exactly.
- Persisted snapshots preserve strategy id/version, adapter contract version, model version, calculated UTC time, capital metrics, earnings/cost metrics, ROI outputs, warnings, classifications, input observation references, freshness, and assumptions.
- API latest/history/ranking payloads preserve persisted Decimal strings.
- Web rendering now displays financial ratio values exactly as API strings and does not parse or convert them with binary float helpers.
- History ordering, versions, and no-overwrite behavior are preserved.
- Stale and missing required inputs fail explicitly and do not create valid ROI snapshots.

## Risk And Confidence Evidence

Persisted score methodology: `risk-confidence-v1`.

Top stored score contributors:

| Strategy | Confidence Contributors | Risk Contributors | Unavailable Factors |
|---|---|---|---|
| DFK Jeweler | source authority -5, config dependence -8, zero-cost assumption -5 | liquidity/exit quality +4, lock/exit penalty +35, config dependence +6, yield weakness +24, recoverable exit loss +10 | ROI deterioration trend requires at least three same-version snapshots. |
| Farmers World | source authority -6, config dependence -12, zero-cost assumption -5 | liquidity/exit quality +22, config dependence +9 | ROI deterioration trend requires at least three same-version snapshots. |
| Splinterlands | source authority -5, config dependence -14, valuation quality -12, model uncertainty -14, warnings -11, zero-cost assumption -5 | liquidity/exit quality +10, probabilistic uncertainty +30, config dependence +11, yield weakness +24, recoverable exit loss +20, warnings +10 | ROI deterioration trend requires at least three same-version snapshots. |

The explanations are consistent with stored snapshot evidence and do not merge confidence with risk.

## Weak Assumption Classification

| Assumption | Classification |
|---|---|
| DFK 1,000 JEWEL strategy size and 1,095-day lock | Acceptable for public beta as a named strategy definition. |
| DFK emergency withdrawal penalty and long lock | Acceptable only with visible risk warning. |
| DFK claim gas units/configured transaction-cost model | Acceptable only with visible warning and provenance. |
| Farmers World tool/cycle/output/input production constants | Acceptable only with visible CONFIG warning. |
| Farmers World zero WAX transaction/resource-cost assumption | Acceptable only with visible warning. |
| Farmers World low-liquidity Alcor markets | Acceptable only with visible risk warning. |
| Splinterlands battles/day and win probability | Acceptable only with visible expected-value warning. |
| Splinterlands configured SPS per win | Acceptable only with visible CONFIG warning. |
| Splinterlands card rental and realization haircut assumptions | Acceptable only with visible CONFIG warning. |
| Splinterlands zero transaction-cost assumption | Acceptable only with visible warning. |

No CONFIG assumption is classified as a public-beta blocker because each one is explicit, versioned, surfaced through strategy/detail methodology, and penalized by confidence/risk scoring.

## Live Probe Results

Live probes were run separately from deterministic tests using public/source connector paths.

| Probe | Result | Notable Output |
|---|---|---|
| DFK Jeweler | PASS | Fresh DFK-chain and AMM-derived observations. Live total capital 5.569988107815870261419280582 USD, net/day 0.0002525122556813468288323803622 USD, 30D ROI 0.001360033006140634903282496548. |
| Farmers World | PASS | Fresh Alcor, AtomicAssets, and CoinGecko observations. Live total capital 0.0012689742176701278470145 USD, net/day 1.88982354220622887352350551E-8 USD, 30D ROI 0.0004467758720132228729488873480. Liquidity volumes remain very low. |
| Splinterlands | PASS | Fresh official settings/season data and SPS market price. Live total capital 10 USD, net/day -0.000994408849378599692500 USD, 30D ROI -0.002983226548135799077500. Current live expected value is negative under the configured assumptions. |

## Stale, Missing, And Edge Cases

Validated adversarial cases:

- Zero liquidity: valid zero realizable value yields no break-even and zero ROI, not missing data.
- Extreme slippage: realizable value and exit loss are explicit.
- Token price collapse: negative net earnings produces negative ROI and no break-even.
- Entry asset price missing: adapter fails explicitly.
- Stale provider data: adapter fails explicitly.
- Negative net earnings: no break-even is reported.
- Zero denominator: ROI is unavailable, not zero.
- Negative denominator: validation rejects it.
- Recoverable asset value collapse: exit-adjusted P&L captures loss.
- Tiny capital with high ROI: high ratio remains explicit and finite.
- Optional history unavailable: trend-risk factor is marked unavailable until enough observations exist.

## API And Web Consistency

G12 found one correctness issue: the web client converted API ROI ratio strings like `0.05862` into `5.862%`. That violated the G12 rule that every displayed financial metric must equal the API value exactly and that the frontend must not recompute financial metrics.

Fix applied:

- `frontend/assets/app.js` now renders ratio metrics as exact API strings.
- `frontend/tests/app.test.mjs` asserts rankings and strategy detail render `0.05862`, not `5.862%`.
- `backend/tests/test_g12_validation.py` asserts the web source has no `parseFloat`, `Number(`, or `decimalStringToPercent` financial conversion path.

## Public-Beta Blockers

None after the web ratio-display fix.

## Required UI Warnings

The public beta UI must continue to display:

- Stale or missing data status.
- Low confidence state.
- Strategy warnings from adapters.
- Confidence/risk contributors.
- LIVE / CONFIG / DERIVED classification.

DFK lock/exit penalty, Farmers low liquidity and zero-cost assumptions, and Splinterlands expected-value uncertainty must remain visible through the risk/confidence panels, warning panels where present, and methodology page.

## Unresolved Limitations

- Live providers have no uptime guarantee; probes can fail due network, provider, or rate-limit conditions outside deterministic acceptance tests.
- Farmers World deterministic product samples use derived adapter inputs, while the live probe shows the raw upstream market observations. Production-grade audit trails should persist raw upstream observations alongside derived adapter inputs.
- Splinterlands expected value is not player-specific and does not use per-account battle history.
- No strategy currently has enough same-version history for ROI deterioration trend scoring.
- This validation does not imply guaranteed returns, investment advice, or executable trading instructions.
