# GameFi ROI — ROI Methodology
Version: 0.1
Status: BASELINE FOR IMPLEMENTATION

## 1. Principle

A GameFi opportunity is modeled as a **strategy under explicit assumptions**.

Do not calculate or publish a context-free “game ROI”.

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

## 5. Time normalization

Daily values must reflect the strategy's assumptions:
- reward/production rate,
- uptime,
- active playtime constraints,
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
- liquidity/fees,
- modeled sellability,
- confidence penalty if only indicative floor prices are available.

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

## 11. Historical ROI

Historical ROI snapshots must preserve:
- model version,
- strategy version,
- input observation identifiers,
- calculated timestamp.

Historical charts should compare like-for-like strategy versions where possible and disclose material rule changes.

## 12. ROI trend

Potential classifications:
- improving,
- stable,
- deteriorating,
- collapsing,
- insufficient history.

Thresholds are a later empirical decision; do not hard-code arbitrary marketing labels in G3.

## 13. Confidence

Confidence measures trust in the **calculation/data**, not safety.

Candidate components:
- source authority,
- freshness,
- input completeness,
- direct vs inferred reward formula,
- direct executable quote vs price approximation,
- asset valuation quality,
- probability-model certainty.

A high-confidence strategy may still be extremely risky.

## 14. Risk

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

Risk methodology will be formalized at G9 after real observations exist.

## 15. Model ranges

Where input uncertainty is meaningful, prefer a range:

`Estimated Net: $0.42–$0.58/day`

over fake precision such as `$0.517392/day`.

The calculation engine may remain precise internally; presentation reflects uncertainty.

## 16. Reporting currency

USD is the initial reference reporting currency unless product requirements change.

Native/token denominated results should remain traceable.

## 17. Non-goals

The system does not:
- promise profit,
- execute trades,
- recommend leverage,
- guarantee future token prices,
- assume historical yield persists,
- treat referral/promotional bonuses as normal baseline yield unless explicitly modeled.

## 18. G3 acceptance principle

Before any live game adapter can be trusted, the generic engine must pass manually verified fixed scenarios covering:
- simple deterministic reward,
- transaction fee,
- recurring cost,
- slippage/executable quote,
- recoverable entry asset,
- break-even,
- exit-adjusted P&L,
- missing data failure behavior.
