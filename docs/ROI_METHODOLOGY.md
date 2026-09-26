# GameFi ROI — ROI Methodology
Version: 0.1
Status: BASELINE FOR IMPLEMENTATION

## 1. Principle

An opportunity is modeled as a **strategy under explicit assumptions**.

Do not calculate or publish a context-free “game ROI” or “opportunity ROI”.

G14 expands the catalog from games to opportunities. Supported planned opportunity types are `GAME`, `DEPIN_NODE`, and `POINTS`, but the financial formulas remain strategy-specific and generic.

## 2. Capital definitions

Let:

- `C_total` = total capital required to enter/operate the strategy at time 0.
- `C_sunk` = entry capital that cannot reasonably be recovered on exit.
- `C_recoverable` = current realizable value of assets that can be sold/redeemed on exit, net of modeled exit costs.
- `C_at_risk` = capital economically exposed.

Initial relationship:

`C_total = C_sunk + acquisition value of recoverable assets + initial operating reserve`

`C_at_risk` is not automatically equal to `C_total`.
Its precise implementation is frozen only after early strategy examples validate treatment of recoverable assets.

## 3. Earnings definitions

For a modeled period:

- `R_nominal` = nominal reward amount × displayed/reference token price.
- `R_realizable` = amount actually realizable through modeled exit route, after pool/market slippage and route-specific fees where applicable.
- `C_operating` = recurring game costs.
- `C_tx` = blockchain/claim/market transaction costs.
- `C_other` = subscription, repair, consumables, or other strategy-specific period costs when applicable.

Net cash earning:

`E_net = R_realizable - C_operating - C_tx - C_other`

## 4. Realizable value

Displayed spot price alone is not sufficient.

Where a liquid DEX route exists, the preferred method is a quote or AMM simulation for the modeled sell amount.

Conceptually:

`Realizable Reward Value = quote_sell(reward_asset, reward_amount, target_asset)`

Then convert target asset to reporting currency only through sourced market data.

If an exact executable quote cannot be obtained:
- use a clearly documented approximation,
- lower model confidence,
- label the limitation.

If a reward is points-only, non-transferable, discretionary, or dependent on a future airdrop/claim, do not invent a USD value. Financial ROI is unavailable until a lawful and reproducible realizable value route exists. Unavailable value is not zero.

## 5. Time normalization

Daily values must reflect the strategy's assumptions:
- reward/production rate,
- uptime,
- active playtime constraints,
- uptime or device/resource contribution constraints,
- claim interval,
- daily/weekly caps,
- season constraints.

Never assume 24/7 production unless the game/strategy permits it.

## 6. ROI metrics

### Daily cash yield
`Daily Net Earnings = E_net_daily`

### N-day cash ROI on total capital
`ROI_total_N = (N * E_net_daily) / C_total`

Only use this simple form for stationary-rate presentation.
Where rates/costs vary through time, use period-specific projected cash flows instead.

### N-day ROI on capital at risk
`ROI_risk_N = Net Cash Earnings over N days / C_at_risk`

### Break-even
Basic cash break-even:

`BreakEvenDays = C_recovery_target / E_net_daily`

The product must state what the recovery target is:
- total initial capital,
- sunk cost,
- or capital-at-risk basis.

Default UI should not hide this distinction.

### Exit-adjusted P&L
At time `t`:

`ExitAdjustedPnL_t = cumulative_net_cash_earnings_t + current_recoverable_exit_value_t - total_cash_invested_t`

This is often more economically meaningful than “reward ROI” when the entry asset remains sellable.

## 7. Entry asset depreciation

Do not assume an NFT/miner/character maintains purchase price.

Current recoverable value should use:
- current floor/market quote appropriate to asset attributes,
- the full quantity of distinct active listings required by the strategy, summed at their observed prices and net of applicable market fees; a one-item floor must not be multiplied as if it proves multi-item depth,
- liquidity/fees,
- modeled sellability,
- confidence penalty if only indicative floor prices are available.

If the requested acquisition or exit quantity exceeds visible active listing depth, the current multi-unit strategy estimate is unavailable. A depth basket is still an indicative snapshot, not a guaranteed fill or resale quote; price and availability can change before execution.

## 8. Subscriptions and periodic costs

Recurring subscription/premium costs are period costs, not necessarily initial capital.

If a subscription is required only to withdraw:
- encode the exact economic dependency,
- amortize according to explicit strategy horizon where needed,
- show user the assumption.

## 9. Claim frequency

Claim frequency can affect:
- transaction cost,
- reward caps,
- compounding,
- missed production,
- operational burden.

Strategy definition must carry claim behavior when economically material.

## 10. Probabilistic rewards

For random/seasonal reward models:
- expected value may be used only when probability/distribution evidence is supportable,
- surface uncertainty,
- report range/distribution when meaningful,
- confidence must reflect model uncertainty.

Expected reward is not guaranteed reward.

## 11. Points and pre-token rewards

Points, credits, badges, fragments, Jade, or similar pre-token rewards can be tracked as production metrics only when sourceable and lawful to collect.

Financial ROI may be calculated only when all of the following are available:

- reward identity,
- earned amount or expected amount,
- claim/vesting eligibility,
- transferable asset or cash-equivalent claim route,
- realizable market/settlement value,
- costs and timing,
- legal/ToS feasibility for automated data collection.

If any required value-realization input is missing, the strategy may still show points/day, costs/day, warnings, confidence, and risk context, but ROI, break-even, and exit-adjusted P&L must be unavailable rather than zero.

## 12. Historical ROI

Historical ROI snapshots must preserve:
- model version,
- strategy version,
- input observation identifiers,
- calculated timestamp.

Historical charts should compare like-for-like strategy versions where possible and disclose material rule changes.

## 13. ROI trend

Potential classifications:
- improving,
- stable,
- deteriorating,
- collapsing,
- insufficient history.

Thresholds are a later empirical decision; do not hard-code arbitrary marketing labels in G3.

## 14. Confidence

Confidence measures trust in the **calculation/data**, not safety.

Candidate components:
- source authority,
- freshness,
- input completeness,
- direct vs inferred reward formula,
- direct executable quote vs price approximation,
- asset valuation quality,
- probability-model certainty.
- points/value-realization certainty for points-based opportunities.

A high-confidence strategy may still be extremely risky.

### G9 confidence methodology

Methodology version: `risk-confidence-v1`.

Confidence is scored from 0 to 100, where higher means the calculation/data is more trustworthy. The score starts at 100 and loses transparent points only for factors supported by snapshot evidence.

Labels:

- `HIGH`: 80-100
- `MODERATE`: 50-79
- `LOW`: 0-49

Point losses:

| Factor | Max loss | Evidence used |
|---|---:|---|
| Freshness | 40 | stale inputs lose 8 each; invalid/missing inputs lose 20 each |
| Provenance completeness | 25 | missing observation references or missing source/value/unit/timestamp/status fields |
| Source authority | 20 | average input source quality: on-chain 1.00, official API 0.95, market API 0.90, derived provider data 0.75, official docs 0.70, verified config 0.65 |
| CONFIG dependence | 25 | required input observations sourced from `verified_config` |
| Valuation quality | 12 | approximation, haircut, spot/reference valuation, or absent executable quote evidence |
| Model uncertainty | 15 | uncertainty ranges, probability/expected-value language, non-guaranteed reward warnings |
| Warnings | 25 | adapter warnings by severity: critical 20, warning 8, info 3 |
| Explicit zero-cost assumption | 5 | configured zero transaction/operating cost where the snapshot says it is an assumption |

Unavailable optional factors are recorded as unavailable and do not silently change the score.

## 15. Risk

Risk measures economic/game/market uncertainty and downside.

Candidate factors:
- liquidity depth,
- slippage,
- token volatility/trend,
- reward/emission instability,
- reward concentration,
- asset exit liquidity,
- rule/season horizon,
- game/developer operational signals where sourceable.
- program rule changes, account eligibility, and non-transferable points for points-based opportunities.

Risk methodology will be formalized at G9 after real observations exist.

### G9 risk methodology

Methodology version: `risk-confidence-v1`.

Risk is scored from 0 to 100, where higher means more economic downside/instability. The score starts at 0 and gains transparent points only for factors supported by snapshot or sufficient history evidence.

Labels:

- `LOW`: 0-24
- `MEDIUM`: 25-49
- `HIGH`: 50-74
- `VERY HIGH`: 75-100

Point additions:

| Factor | Max add | Evidence used |
|---|---:|---|
| Liquidity / exit quality | 35 | realized-vs-gross haircut, thin-liquidity assumption text, stored 24h market volume |
| Lock / exit penalty | 35 | lock-day observations and early-exit penalty bps |
| Probabilistic uncertainty | 30 | uncertainty ranges, probability/expected-value assumptions, non-guaranteed reward warnings |
| CONFIG dependence | 20 | required input observations sourced from `verified_config` |
| Yield weakness | 30 | non-positive net earnings, long break-even, weak 30-day ROI |
| Recoverable exit loss | 20 | current recoverable value materially below total capital |
| Warnings | 20 | adapter warnings by severity: critical 20, warning 8, info 2 |
| ROI/yield deterioration trend | 25 | requires at least three comparable same-strategy/version/model snapshots |

Trend risk is unavailable until at least three comparable snapshots exist. Token volatility/trend, reward instability, and concentration are also unavailable until the stored observations/history contain enough evidence to measure them.

## 16. Model ranges

Where input uncertainty is meaningful, prefer a range:

`Estimated Net: $0.42–$0.58/day`

over fake precision such as `$0.517392/day`.

The calculation engine may remain precise internally; presentation reflects uncertainty.

## 17. Reporting currency

USD is the initial reference reporting currency unless product requirements change.

Native/token denominated results should remain traceable.

## 18. Non-goals

The system does not:
- promise profit,
- execute trades,
- recommend leverage,
- guarantee future token prices,
- assume historical yield persists,
- treat referral/promotional bonuses as normal baseline yield unless explicitly modeled.
- allow affiliate/sponsor relationships to affect ROI, Risk, Confidence, or organic rankings.
- assign a financial value to points, badges, or pre-token rewards without a lawful realizable route.

Commercial monetization metadata, affiliate attribution, sponsored placement data, and referral destination metadata are not ROI inputs. If a game-native referral reward is ever modeled as an economic strategy, it must be explicit strategy/config evidence and must not be introduced because of a commercial relationship with GameFi ROI.

G15 monetization reporting uses verified commercial records only:

- outbound clicks are measured through the first-party `/go/...` layer,
- pending or rejected partner imports do not count as conversion or revenue,
- EPC is defined only as verified revenue divided by outbound clicks,
- conversion rate is defined only when verified conversions and outbound clicks are both present.

These reporting metrics are commercial analytics, not strategy economics. They must never be fed into ROI, Risk, Confidence, validation, historical snapshot generation, or organic ranking order.

## 19. G3 acceptance principle

Before any live game adapter can be trusted, the generic engine must pass manually verified fixed scenarios covering:
- simple deterministic reward,
- transaction fee,
- recurring cost,
- slippage/executable quote,
- recoverable entry asset,
- break-even,
- exit-adjusted P&L,
- missing data failure behavior.
