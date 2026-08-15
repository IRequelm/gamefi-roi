# Decision 0003: Adapter #3 Feasibility Scan

Date: 2026-08-15
Gate: G6 - Adapter #3

## Decision

Adapter #3 is `splinterlands-modern-ranked-sps-ev` version `v1`.

Decision classification: `GO`.

The selected strategy models Splinterlands Modern Ranked combat rewards as an expected-value strategy. It is materially different from:

- DFK Jeweler lock/reward economics,
- Farmers World deterministic resource production.

The modeled economy is performance-dependent combat: configured battles/day and win-probability range produce expected wins, expected SPS rewards, realizable reward value, operating cost, break-even, ROI, and exit-adjusted P&L through the generic ROI engine.

## Feasibility Scan

| Rank | Candidate | Economy Type | Result | Feasibility Summary |
|---:|---|---|---|---|
| 1 | Splinterlands Modern Ranked | PvP combat, performance-dependent ranked rewards | GO | Official docs define SPS rewards for ranked wins, R-Shares variables, Spellbook requirement, starter-card penalty, energy constraints, and reward pools. Official API exposes settings, season, leaderboard, and battle-result endpoint metadata. SPS price is available from market APIs. Future player win rate and representative SPS per win remain configured strategy assumptions. |
| 2 | Nine Chronicles Arena / World Boss | Seasonal combat, ranking/contribution rewards | PARTIAL | Mimir GraphQL and open-source sheets expose many rule tables, and docs explain Arena/World Boss seasons, tickets, entry costs, ranking/contribution rewards, and WNCG exit. Current reward valuation often depends on game items, rankings, and services outside the core chain state; more investigation is needed before a clean automated model. |
| 3 | Gods Unchained Daily Play & Earn / Sealed | Card combat, daily fragments, probabilistic performance | PARTIAL | Official docs provide the fragment formula and ranking/deck modifiers. Final GODS rewards depend on daily community fragments and daily pool values that change until day close; current pool/community data was not verified as a stable public machine-readable source. |
| 4 | Sorare Football Arena / Competitions | Fantasy sports leaderboard rewards | PARTIAL | Official GraphQL API exists and prize pools are documented, but current prize-pool visibility often requires account context, performance depends on external sports projections, and rewards/cash terms require tighter legal review. |
| 5 | Axie Infinity Origins | Seasonal PvP leaderboard | PARKED | Active Origins S18 has a leaderboard prize pool, but current rewards are bAXS, a non-transferable token backed 1:1 by AXS with conversion fees tied to Axie Score. This does not provide a clean realizable exit route for baseline ROI. |
| 6 | Pirate Nation | Quest/leaderboard competitions | PARKED | Leaderboard and competition mechanics are documented, but current docs indicate recent event rewards may be non-token/in-game items, some tables are image-based, and $PIRATE withdrawal terms are not stable enough for automated ROI. |

## Splinterlands Evidence

- Official Ranked Battle Rewards docs state that Modern/Wild Ranked wins reward Glint, Rating Points, and staked SPS; SPS/Glint are calculated from R-Shares, and rewards depend on variables such as staked SPS multiplier, league, win streak, cards, guild, and format: https://docs.splinterlands.com/rewards/ranked-battle-rewards
- Official Earning SPS docs state that upgraded accounts with a Summoner's Spellbook can earn SPS for Ranked Battle wins and that Modern/Wild reward pools operate independently: https://docs.splinterlands.com/splintershards-sps/earning-dec
- Splinterlands support documents R-Shares and cites the Battle Result API for viewing battle rewards: https://support.splinterlands.com/hc/en-us/articles/6614462185620-How-are-Rewards-Rshares-Calculated
- Splinterlands support documents ranked SPS reward pools, including 900,000 SPS/Season for Modern and Wild after the 2025 overhaul: https://support.splinterlands.com/hc/en-us/articles/9665791951764-SPS-Reward-Pools
- Official API Swagger lists `/settings`, `/season`, `/battle/result`, `/players/leaderboard`, and market/rental endpoints: https://api.splinterlands.com/doc/
- Rental contract docs describe daily and season rentals plus minimum terms/cost constraints: https://support.splinterlands.com/hc/en-us/articles/4719654546708-How-Do-Splinterlands-Rental-Contracts-Work

Live probes on 2026-08-15:

- `https://api.splinterlands.com/settings` returned `starter_pack_price=10`, `sps_price=0.0033603`, `config_version=208`, `season.id=189`, `season.ends=2026-08-31T14:00:00.000Z`, and energy settings.
- `https://api.splinterlands.com/season?id=189` returned season id and season end.
- `https://api.splinterlands.com/players/leaderboard?season=188&leaderboard=modern` returned prior-season public player rankings with battles, wins, rating, league, and reward claim transaction fields.
- Raw `/battle/history` and `/battle/history2` calls without authenticated user context returned access-token errors; `last_season_rewards` timed out. These are not used in the baseline live probe.

## Modeled Strategy

Strategy: `Splinterlands Modern Ranked SPS Expected Value`, version `v1`.

Assumptions:

- Player has a Summoner's Spellbook; cost comes from official Splinterlands settings.
- Player plays Modern Ranked using real owned/rented cards, not starter-only cards.
- Player completes 20 ranked battles/day.
- Expected win probability is configured at 55%, with an explicit uncertainty range of 45%-65%.
- Representative SPS reward per win is configured at 0.25 SPS from observed ranked-win evidence. This is a strategy input, not a live guarantee.
- SPS/USD is live from CoinGecko using asset id `splinterlands`.
- Realizable reward value applies a configured 100 bps realization haircut to the live SPS reference price.
- Daily real-card rental operating cost is configured at $0.01/day.
- Transaction cost is configured at $0/day because baseline reward realization is modeled off-platform; future adapters may add chain-specific withdrawal/unstake costs if required by the modeled route.

## LIVE / CONFIG / DERIVED

LIVE:

- Summoner's Spellbook/starter pack price from Splinterlands `/settings`.
- Current season id/end and energy parameters from Splinterlands `/settings`.
- Season endpoint probe from Splinterlands `/season?id=...`.
- SPS/USD reference price from CoinGecko.

CONFIG:

- Battles per day.
- Win probability and low/high range.
- Representative SPS reward per win.
- Realization haircut.
- Daily rental operating cost.
- Transaction cost assumption.

DERIVED:

- Sustainable energy/day.
- Expected wins/day and low/high.
- Expected SPS/day and low/high.
- Gross nominal daily reward value.
- Realizable daily reward value and low/high.
- Low/high net earnings/day.
- G3 ROI engine outputs.

## Manual Golden Fixture

Inputs:

- Spellbook cost: $10.00.
- Battles/day: 20.
- Win probability: 0.55, low 0.45, high 0.65.
- SPS/win: 0.25.
- SPS price: $0.01.
- Realization haircut: 100 bps.
- Rental cost/day: $0.01.
- Transaction cost/day: $0.

Manual expected:

- Expected wins/day = 20 * 0.55 = 11.
- Expected SPS/day = 11 * 0.25 = 2.75 SPS.
- Gross nominal value/day = 2.75 * $0.01 = $0.0275.
- Realizable value/day = $0.0275 * 0.99 = $0.027225.
- Net earnings/day = $0.027225 - $0.01 = $0.017225.
- Break-even = $10 / $0.017225 = 580.5515239477503628447024673 days.
- 30D ROI on total capital = 30 * $0.017225 / $10 = 0.051675.
- Exit-adjusted P&L at t0 = $0 + $0 - $10 = -$10.

The golden fixture in `backend/tests/fixtures/splinterlands_modern_ranked_golden.json` verifies these values against the adapter and G3 engine.

## Source Boundary

- Splinterlands provider HTTP access lives in `backend/app/sources/splinterlands.py`.
- CoinGecko HTTP access remains in `backend/app/sources/coingecko.py`.
- Splinterlands game economics live in `backend/app/adapters/splinterlands.py`.
- The versioned strategy definition lives in `backend/app/strategies/splinterlands.py`.
- The generic ROI engine was not modified.

## Unresolved Assumptions

- Representative SPS per win is configured in v1 because unauthenticated battle-history discovery was not reliable in the investigation window. The official battle-result endpoint remains a viable verifier when a recent battle id is available.
- Reward-per-win volatility, player skill uncertainty, market slippage/liquidity depth, unstaking timing, and route-specific execution costs should affect future confidence/risk scoring, but G9 owns that methodology.
- The 100 bps realization haircut is a transparent baseline approximation, not an executable quote.

## Legal / ToS Notes

The adapter uses public official API endpoints and reputable market API data. It does not automate login, bypass authentication, scrape private account pages, or access wallet keys. Endpoints that required authenticated user context were excluded from baseline automation.
