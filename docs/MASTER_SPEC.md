# GameFi ROI — Master Specification
Version: 0.1
Status: FROZEN FOR G0
Date: 2026-08-15

## 1. Product thesis

GameFi ROI is a data and analytics product that estimates the real, strategy-specific economic return of blockchain games and adjacent on-chain/off-chain reward opportunities using live market/on-chain/official data where available.

The product is **not primarily a game directory**.

Its core question is:

> Given my capital, available playtime, device/platform constraints, and risk tolerance, which modeled strategy is economically most attractive right now, under transparent assumptions?

The website is one client of the underlying data/ROI platform.

## 2. Core user problem

Existing GameFi discovery products can answer:
- what games exist,
- token prices,
- user/wallet activity,
- broad game descriptions.

The target product should answer:
- what capital is required,
- what the player must actually do,
- what costs are incurred,
- what rewards are realistically sellable for,
- expected net earnings,
- break-even,
- strategy-specific ROI,
- how ROI has changed over time,
- how reliable the calculation is,
- how risky/sustainable the opportunity appears.

## 3. Primary object: Strategy

A game does not have one universal ROI.

ROI depends on configuration and behavior.

G14 expands the catalog model from `Game` to a backward-compatible `Opportunity` supertype.

An `Opportunity` is a modeled economic context that can contain one or more strategies. Initial opportunity types:

- `GAME`: blockchain game, GameFi, or play-to-earn economy.
- `DEPIN_NODE`: node/bandwidth/compute/storage/resource-contribution network.
- `POINTS`: points or pre-token reward program where financial value may be unavailable until a lawful realizable claim or market route exists.

Existing GameFi entries remain `GAME` opportunities. Existing `game_id` fields and `/api/v1/games` behavior must remain backward compatible while new code may introduce canonical `opportunity_id` and `opportunity_type` fields.

A `Strategy` may include:
- opportunity/game,
- entry asset/NFT/token configuration,
- required account/subscription state,
- capital required,
- production/reward assumptions,
- playtime/uptime,
- claim frequency,
- operating costs,
- exit route,
- liquidation/slippage assumption,
- model version.

Examples:
- “mRON: 2 Yellow miners, 12h claim interval”
- “Craft World: $25 capital, production path X, Pro account assumption”
- “Game X: free-to-play seasonal reward strategy”
- “Grass: desktop node, 24h uptime, points-only no-financial-ROI strategy”
- “Teneo: Community Node heartbeat/data-signal points strategy”
- “ARO: Testnet S2 node Jade points strategy”

## 4. Product outputs

At minimum, a strategy may expose:

### Capital
- total capital
- sunk cost
- recoverable capital
- capital at risk

### Earnings
- gross nominal earnings
- realizable earnings
- operating costs
- transaction/claim costs
- net earnings per hour/day/month

### Return
- break-even days
- 7D / 30D / 90D ROI
- exit-adjusted P&L
- capital efficiency
- earnings per active minute where meaningful

### Market quality
- token/liquidity context
- slippage at modeled exit size
- ROI trend
- yield stability

### Trust
- last updated
- data freshness
- source lineage
- confidence score
- risk score/label

## 5. Product positioning

Desired positioning:

> “Live GameFi ROI and strategy intelligence”

Useful mental model:
- PlayToEarn: discovery/content
- CoinMarketCap/CoinGecko: market data
- DappRadar: on-chain dapp activity
- GameFi ROI: strategy-specific economic outcome layer

## 6. Target users

Primary:
- players deciding what to play for economic return,
- low-to-medium capital GameFi users,
- idle/resource/P2E users,
- users comparing opportunities across chains/games.
- users comparing DePIN/node/points opportunities where rewards and costs can be modeled transparently.

Secondary:
- content creators,
- guilds/communities,
- game studios,
- analysts,
- third-party products consuming a future API.

## 7. MVP scope

The technical MVP proves that one normalized engine can model at least **three materially different game-economy types**.

MVP must include:
- automated/structured data acquisition,
- source provenance,
- strategy definitions,
- realizable-value calculation,
- costs,
- ROI,
- risk,
- confidence,
- historical snapshots,
- API,
- minimal web UI.

The first three games are **not permanently fixed at G0**.
Candidate games must pass Data Feasibility Check before implementation.

Initial intended classes:
1. deterministic miner/production economy,
2. resource/crafting/market economy,
3. a materially different reward economy (seasonal/staking/combat/etc.).

Post-MVP scaling may include non-game opportunities only when the model distinguishes financial ROI from non-financial points production. Grass, Teneo, and ARO are the first non-game feasibility candidates for G14 planning, not approved ROI adapters.

## 8. Out of scope for initial MVP

Do not implement in early gates:
- user portfolio tracking,
- paid subscriptions,
- affiliate attribution/reporting before G15,
- sponsored placements before G15,
- Telegram/Discord bots,
- developer self-service onboarding,
- mobile native apps,
- B2B commercial API,
- AI recommendation chat,
- hundreds of games,
- full scraping infrastructure,
- custom blockchain indexer unless proven necessary,
- custom token/wallet,
- smart contracts,
- automated trading/execution,
- custody,
- guaranteed-return claims.

These remain backlog/future product areas.

## 9. Data principles

Preferred source order:
1. authoritative on-chain state / contracts,
2. official game/developer API,
3. reputable market API/indexer,
4. official docs/config,
5. modeled/manual verified config as last resort.

The system must distinguish live, derived, and configured data.

No hidden assumptions.

## 10. Monetization hypothesis (post-validation)

Potential monetization:
1. first-party outbound/referral links,
2. affiliate attribution/reporting,
3. clearly marked sponsored placement,
4. premium alerts/history/portfolio/tools,
5. B2B/API access,
6. developer integrations.

Roadmap:
- G14 introduces the Opportunity catalog foundation and referral foundation: backward-compatible `Game` to `Opportunity` model expansion, structured outbound/referral metadata, and a first-party `/go/...` redirect layer.
- G15 introduces monetization: affiliate attribution/reporting, sponsored placements, and commercial analytics.

Affiliate/sponsor relationships must never affect ROI, Risk, Confidence, strategy snapshots, validation results, or organic rankings. Sponsored placements must be clearly labeled and separated from organic ranking order and analytical metrics.

## 11. Validation philosophy

Game play is for model validation, not primary data acquisition.

The project should scale through:
- reusable source connectors,
- opportunity adapters,
- standardized strategy contracts,
- economic-model templates where evidence supports them.

## 12. Success criteria

### Technical proof
- three different economy types work through the same core system,
- new games or adjacent opportunities can be added through adapters without modifying core ROI math for opportunity-specific quirks,
- deterministic test fixtures match manual calculations,
- stale/missing data is safely surfaced,
- historical snapshots are retained.

### Product proof after web launch
To be defined after the technical MVP produces real data.

## 13. Non-negotiables

- no fake precision,
- no guaranteed return language,
- no single “game ROI” without strategy context,
- no manual game-playing process as the scaling model,
- no dependency on one DEX/data provider in architecture,
- no giant monolithic script,
- no UI-first development before the engine proves value.

## 14. Working project name

Repository/project working name: `gamefi-roi`

Brand/domain name is deliberately deferred.
