# Decision 0001: Adapter #1 Data Feasibility Scan

Date: 2026-08-15
Gate: G4 - Adapter #1
Decision: GO with DeFi Kingdoms Crystalvale Jeweler 2.0, not mRON Miner.

## Context

mRON Miner remains PARKED because the reward and exit economics could not be sourced reliably enough for a live automated model.

Adapter #1 must use a candidate whose strategy economics can be sourced from public on-chain data, official APIs/docs, or reputable market APIs without adding game-specific branches to the ROI core.

## Ranked Candidate Scan

| Rank | Candidate | Reward Formula / Rate | Token | Entry Pricing | Exit / Liquidity / Slippage | Costs / Caps / Seasons | Machine Readable / Change Detection | Legal / ToS Feasibility | Result |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | DeFi Kingdoms - Crystalvale Jeweler cJEWEL max lock | Official lock formula and fee distribution; contract exposes `getYesterdayAPRData`, `dailyRewards`, and `dailyBalances`. | JEWEL, native DFK Chain gas token / wJEWEL route. | JEWEL opportunity cost from wJEWEL-USDC pool or market API. | DFK wJEWEL-USDC pair has on-chain reserves; constant-product quote supports slippage-aware reward and exit values. | Gas price observable by RPC; claim gas units are configured; 7-1095 day lock and 50% emergency withdrawal penalty are documented. | Contract reads and DEX reserves are machine-readable; docs/contracts identify change points. | Public chain data and official developer docs are usable for analytics; DFK assets remain subject to DFK ToS and need production legal review. | GO |
| 2 | Aavegotchi - Alchemical channeling / Gotchiverse farming | Public formulas exist for channeling and farming concepts, but current Base/Polygon migration state and gameplay eligibility complicate automated entry modeling. | FUD, FOMO, ALPHA, KEK, GHST. | Official Baazaar/subgraphs provide NFT/listing data; chain migration creates ambiguity. | DEX routes exist historically; Base liquidity for Alchemica has been evolving. | Daily channeling, kinship burn, parcel/installation constraints. | Subgraphs are machine-readable but some docs mark Gotchiverse subgraph WIP. | Public subgraphs/docs likely usable, but marketplace and game data terms require review. | PARTIAL |
| 3 | Alien Worlds - Mining | Open-source contracts and WAX tables expose mining mechanics, but expected rewards depend on probabilistic mining, tools, land, and anti-bot proof-of-work flow. | TLM. | AtomicAssets/market APIs can source tool and land prices. | TLM has market routes; WAX/BNB liquidity can be sourced from market APIs. | WAX resource costs and mining cooldowns observable; caps depend on pool state. | WAX RPC and Alien Worlds APIs are machine-readable. | Analytics over public data is plausible, but ToS language around TLM value and automation needs review. | PARTIAL |
| 4 | Splinterlands - Ranked rewards | RShare and reward formulas are documented, but output depends heavily on player skill, deck state, match outcomes, and season pool denominators. | GLINT, SPS. | Card/rental market APIs exist. | SPS/DEC market exits available through external venues. | Season rules and reward pools change; claim/transaction costs depend on Hive/Splinterlands flow. | Official APIs are machine-readable. | API use likely feasible with rate/terms review; automated modeling would require explicit player assumptions. | PARTIAL |
| 5 | Gods Unchained - Daily Play and Earn | Fragments formula is documented, but daily pool denominator and gameplay modifiers are off-chain and season/config sensitive. | GODS. | Immutable marketplace APIs provide card/listing prices. | Immutable/market APIs provide token/listing data. | Daily caps and first-games rules documented; live pool state less clear. | Marketplace APIs are machine-readable; reward config less reliable. | Official APIs likely feasible; game reward config needs terms and stability review. | PARTIAL |
| 6 | Sunflower Land - FLOWER/resource economy | Economy docs and open repository exist, but exchange rates and rewards are dynamic/off-chain and chapter-specific. | FLOWER. | NFT/resource market data is fragmented. | Token route exists on Base; resource exits depend on game systems. | Chapter resources expire; burn/reward cycling changes. | Some code/config is public, but current production economics are not cleanly exposed as stable APIs. | Repository has licensing constraints; automated collection needs review. | PARKED |
| 7 | STEPN - GST earning | Whitepaper gives formula shape and caps, but key system values, SMAC validity, movement behavior, and anti-cheat constraints are not independently machine-readable. | GST, GMT. | Sneaker marketplace pricing may be available, but automated source terms are unclear. | Token market routes exist. | Daily energy/GST caps documented. | Required live personal/game state is not sufficiently machine-readable for a generic adapter. | Automation and anti-cheat constraints make modeling risky. | PARKED |

## Selected Strategy

`dfk-crystalvale-jeweler-cjewel-max-lock` version `v1`

Modeled economics:
- Lock `1000 JEWEL` for `1095 days` in DeFi Kingdoms Crystalvale Jeweler 2.0.
- cJEWEL received = `JEWEL locked * lock_days / 1095`.
- Daily JEWEL reward = `yesterday_reward_jewel * cJEWEL_received / yesterday_cjewel_balance`.
- Claim interval = 1 day.
- Claim gas units = configured estimate of `180000`.
- Entry value = JEWEL opportunity cost using DFK wJEWEL-USDC pool state.
- Current recoverable value = emergency withdrawal value after 50% penalty, quoted through wJEWEL-USDC.
- Reward realizable value = JEWEL daily reward quoted through wJEWEL-USDC.
- Capital at risk = total entry value while JEWEL remains locked.

## LIVE / DERIVED / CONFIG Classification

LIVE:
- DFK Chain id.
- DFK Chain gas price.
- Jeweler yesterday cJEWEL balance.
- Jeweler yesterday JEWEL reward.
- wJEWEL-USDC pair reserves.

DERIVED:
- JEWEL reference price from pool reserves.
- Reward JEWEL/day from strategy share and live reward pool.
- Reward realizable USD quote.
- Emergency-exit recoverable USD quote.
- Claim transaction cost in USD.
- ROI engine outputs.

CONFIG:
- Strategy id/version.
- Locked JEWEL amount.
- Lock days and maximum lock days.
- Claim interval.
- Claim gas-unit estimate.
- Emergency withdrawal penalty.
- DEX fee basis points.

## Evidence

- DeFi Kingdoms Jeweler docs: https://docs.defikingdoms.com/how-defi-kingdoms-works/the-jeweler
- DeFi Kingdoms Jeweler 2.0 developer docs: https://devs.defikingdoms.com/contracts/jeweler-2.0.md
- DFK Chain RPC/docs: https://devs.defikingdoms.com/dfk-chain/getting-started
- DFK ecosystem token docs: https://devs.defikingdoms.com/tokens/ecosystem-token
- DFK bridged token docs: https://devs.defikingdoms.com/dfk-chain/bridged-tokens
- DFK Gardens docs, including completed CRYSTAL emissions and LP fee-sharing context: https://docs.defikingdoms.com/how-defi-kingdoms-works/the-gardens/ice-gardens
- Aavegotchi subgraph docs: https://docs.aavegotchi.com/developers/subgraphs/general
- Alien Worlds API docs: https://alien-worlds.github.io/alienworlds-api/
- Splinterlands API docs: https://api.splinterlands.com/doc/
- Gods Unchained reward support: https://support.godsunchained.com/hc/en-us/articles/360061884154-How-do-I-earn-rewards
- Sunflower Land tokenomics: https://docs.sunflower-land.com/project/economy-tokenomics
- STEPN whitepaper: https://whitepaper.stepn.com/

## Consequences

This is a staking/fee-distribution game-economy adapter, not a miner adapter. It validates the architecture against a current, on-chain, strategy-specific earning model while preserving the generic ROI engine boundary.

G5 should choose a materially different economy type, preferably a resource/crafting or play-performance economy, rather than another staking-like model.
