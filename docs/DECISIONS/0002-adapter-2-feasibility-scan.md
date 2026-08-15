# Decision 0002: Adapter #2 Data Feasibility Scan

Date: 2026-08-15
Gate: G5 - Adapter #2
Decision: GO with Farmers World Axe wood-production strategy.

## Context

Adapter #2 must represent a materially different economy from DeFi Kingdoms Jeweler. The target class is resource production, crafting, conversion, and player-market or exchange economics.

The chosen adapter must not require game-specific changes to the ROI core. If a candidate cannot provide reliable machine-readable entry, production, input cost, reward realization, and exit data, it should be parked rather than forced.

## Ranked Candidate Scan

| Rank | Candidate | Reward Formula / Rate | Reward / Resource Token Identity | Entry Asset Pricing | Exit Route | Liquidity / Slippage | Costs / Caps / Seasons | Machine Readable / Change Detection | Legal / ToS Feasibility | Result |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | Farmers World - Axe wood production | Official Farmers World docs identify tool-based resource extraction, energy, durability, and token recovery mechanics. Exact Axe per-cycle values are older verified config, corroborated by Farmers World Medium-era materials and public tool tables. | FWW, FWF, FWG issued by `farmerstoken` on WAX. | AtomicAssets/AtomicMarket public sales endpoint exposes lowest listed Axe template price; NeftyBlocks confirms `farmersworld/tools/203881` Axe metadata. | FWW, FWF, and FWG trade against WAX on Alcor; Axe NFT can be listed on WAX marketplaces. | Alcor ticker API exposes base/target AMM liquidity, bid/ask, frozen flag, fees, and recent volume for FWW/WAX, FWF/WAX, and FWG/WAX. | Strategy explicitly configures 12 one-hour cycles/day, 5 FWW output/cycle, 2 FWF energy/cycle, 1 FWG repair/cycle, and zero modeled WAX transaction/resource cost. No current season cap found for this baseline Axe loop. | Market and NFT prices are machine-readable. Production constants are verified config, so rules need manual docs/config review on adapter version updates. | Public docs and public market APIs are feasible for analytics. Production launch still needs legal review of API rate limits and Farmers World/marketplace terms. | GO |
| 2 | Craft World | Official VOYA litepaper explains Collect -> Craft -> Trade -> Build and resource/market economy, but current production rates, recipe economics, Pro withdrawal effects, and factory constraints were not found as stable machine-readable config. | Dyno Coin plus 25+ resource ERC-20s on Ronin. | Some token/resource prices are visible through GeckoTerminal pools; entry/subscription requirements include Pro Account for withdrawal. | Resources trade through DEX pools paired with Dyno Coin. | GeckoTerminal shows pools and liquidity for COIN/resource markets, but executable route assumptions need more work. | Claim/withdrawal/account constraints and current recipe rates are not reliably API-readable from official sources. | Markets are machine-readable; production rules are not clearly machine-readable. | Public docs and DEX data are feasible, but client/game data collection terms need review. | PARTIAL |
| 3 | Aavegotchi Gotchiverse farming/crafting | Public docs and wiki provide alchemica resources, channeling, recipes, harvesters, rates, capacities, and crafting mechanics. Current Base-era canonical data and subgraph status need deeper validation. | FUD, FOMO, ALPHA, KEK, GHST. | Baazaar/subgraphs and chain contracts can price parcels, installations, and Gotchis, but entry state is multi-asset. | Alchemica/GHST DEX routes exist, with current chain migration complexity. | Pool liquidity can be sourced, but exact current route selection is non-trivial. | Channeling cooldowns, harvester capacities, construction/refund rules, and parcel attributes make a first G5 strategy broad. | Subgraphs are machine-readable, but docs mark some schemas as WIP/historical. | Public docs/subgraphs likely feasible with terms review. | PARTIAL |
| 4 | Sunflower Land | Crop/resource grow times and recipe loops are documented; crop profits are dynamic and docs direct users to in-game prices. | SFL/FLOWER and in-game resource SFTs. | Asset/resource pricing is fragmented across in-game systems and markets. | Token exit exists, but resource realization depends on game systems and chapter rules. | Token liquidity can be sourced, resource exits are less standardized. | Hoard limits, dynamic controls, chapter-specific resources, and changing in-game prices are material. | Some code/config is public, but the repository carries licensing constraints and live economy state is not cleanly exposed. | Automated collection and code reuse need legal/licensing review. | PARKED |
| 5 | Prospectors | Public FAQ/wiki describes resource gathering, jobs, tool crafting, markets, and PGL/gold conversion. | PGL/gold plus raw/processed resource economy on WAX/EOS. | Tool/market prices are in-game/chain-visible but tied to worker location and job availability. | In-game market and PGL conversion provide exits. | Some WAX/EOS market data is sourceable; in-game market liquidity needs deeper source work. | Worker travel distance, tool state, jobs, locations, and production buildings create many player-state dependencies. | Game pages are public, but a stable official read API for all required live state is unclear. | Public data plausible; automation and in-game market terms require review. | PARTIAL |
| 6 | Pixels | Official docs describe resource generation, resource types, farming, cooking, crafting, and token economics. | PIXEL plus in-game resources. | Land/resources/tokens have markets, but resource economics are game-controlled. | Token exits exist; resource value realization is game-loop dependent. | Token market data is sourceable; resource-level liquidity is not sufficiently exposed. | Team-adjusted variables, attention requirements, progression, and recipe unlocks are material. | Docs state generation variables can be adjusted by the team; current values were not found as stable public API config. | Public docs are usable; live game-economy data collection needs terms review. | PARTIAL |
| 7 | Alien Worlds mining/shining | Mining formulas and cooldown mechanics are public, but rewards are probabilistic and anti-bot/mining submission flow is gameplay-sensitive. | TLM plus NFTs on WAX/BNB. | AtomicAssets can price tools and land. | TLM exits via WAX/BNB markets; NFTs trade on WAX marketplaces. | Market data can be sourced, but expected reward probability depends on pool/land/tool state. | Mining attempts, land multipliers, tool charge times, and resource limits are material; not a clean crafting/conversion economy. | Contracts and docs are machine-readable in part. | Public data feasible; automated gameplay assumptions are sensitive. | PARTIAL |

## Selected Strategy

`farmers-world-axe-wood-production` version `v1`

Modeled economics:
- Own 1 Farmers World Axe NFT, `farmersworld/tools` template `203881`.
- Operate 12 one-hour wood-mining cycles per day.
- Per cycle, produce `5 FWW`, consume `2 FWF` for energy, and consume `1 FWG` for repair.
- Entry capital is the live lowest active AtomicAssets WAX listing for the Axe template, converted to USD by live WAX/USD.
- Exit value is the same live floor net of AtomicAssets collection marketplace fee, converted to USD.
- Reward value sells modeled daily FWW output through Alcor FWW/WAX AMM reserves, then converts WAX to USD.
- Operating costs buy modeled daily FWF and FWG input amounts through Alcor exact-output AMM simulation, then convert WAX to USD.
- WAX transaction/resource cost is configured as `0 WAX/day` for this baseline because normal WAX resource usage is not a per-transaction gas fee. This is explicit config, not an implicit zero.
- Capital at risk is modeled as full Axe entry value because NFT exit liquidity is thin and price recoverability is uncertain.

## LIVE / DERIVED / CONFIG Classification

LIVE:
- Alcor FWW/WAX, FWF/WAX, and FWG/WAX ticker, bid/ask, AMM liquidity, fee, frozen status, and volume observations.
- AtomicAssets Axe template floor listing and collection market fee.
- CoinGecko WAX/USD price.

DERIVED:
- Axe entry value in USD.
- Axe exit value in USD after marketplace fee.
- FWW reference price in USD.
- Daily FWW realizable value in USD.
- Daily FWF and FWG operating costs in USD.
- Daily WAX transaction/resource cost converted to USD.
- Daily production/input totals.
- ROI engine outputs.

CONFIG:
- Strategy id/version.
- Tool count.
- Cycles per day.
- Cycle length.
- FWW output per cycle.
- FWF input per cycle.
- FWG input per cycle.
- Zero WAX transaction/resource cost assumption.

## Manual Golden Fixture

Fixture assumptions:
- Entry value: `10.00 USD`
- Exit value: `9.50 USD`
- FWW reference price: `0.02 USD`
- Daily production: `1 tool * 12 cycles * 5 FWW = 60 FWW`
- Daily inputs: `24 FWF` and `12 FWG`
- Realizable FWW value after modeled execution: `1.17 USD`
- Operating cost: `0.24 + 0.18 = 0.42 USD`
- Transaction/resource cost: `0.02 USD`

Manual expected outputs:
- Gross nominal earnings/day: `60 * 0.02 = 1.20 USD`
- Net earnings/day: `1.17 - 0.42 - 0.02 = 0.73 USD`
- Total capital: `10.00 USD`
- Recoverable capital: `9.50 USD`
- Capital at risk: `10.00 USD`
- Break-even on total capital: `10 / 0.73 = 13.69863013698630136986301370 days`
- 7D / 30D / 90D ROI on total capital: `0.511`, `2.19`, `6.57`
- 7D / 30D / 90D ROI on capital at risk: `0.511`, `2.19`, `6.57`
- Exit-adjusted P&L at t0: `0 + 9.50 - 10.00 = -0.50 USD`

## Evidence

- Farmers World FAQ: https://farmersworld.io/faqs
- Farmers World Medium FAQ: https://farmersworld.medium.com/frequently-asked-questions-in-farmers-world-80eceedd9f5c
- Farmers World tools/resources source mirror of official Medium article: https://github-wiki-see.page/m/shakhruz/angelfarmers-ui/wiki/FW-Tools-and-resources
- Farmers World energy/durability article: https://farmersworld.medium.com/generating-tools-and-important-indexes-energy-and-durability-584781fda106
- NeftyBlocks Axe template: https://neftyblocks.com/templates/farmersworld/203881
- Alcor API documentation: https://api.alcor.exchange/
- Alcor Markets API documentation: https://docs.alcor.exchange/developers-api/api/markets-api
- WAX AtomicAssets API documentation: https://docs.wax.io/apis/atomic-api.htm
- CoinGecko simple price API documentation: https://docs.coingecko.com/reference/simple-price
- VOYA Craft World litepaper: https://voya-games.gitbook.io/voya-games-litepaper/craft-world
- VOYA supply and demand markets: https://voya-games.gitbook.io/voya-games-litepaper/implementing-a-player-owned-economy/supply-and-demand-driven-markets
- Aavegotchi Gotchiverse subgraph docs: https://docs.gotchiverse.io/developers/subgraph
- Aavegotchi alchemica docs: https://docs.aavegotchi.com/own/tokens/gotchus-alchemica
- Sunflower Land planting/harvesting docs: https://docs.sunflower-land.com/player-guides/planting-and-harvesting
- Prospectors FAQ: https://prospectors.io/faqs
- Pixels resource generation docs: https://docs.pixels.xyz/economics/resource-generation
- Alien Worlds getting-started docs: https://support.alienworlds.io/help-center/articles/game/guides/getting-started-in-alien-worlds

## Consequences

Farmers World validates the core against a resource production and market-conversion economy without modifying generic ROI formulas. The adapter uses configured production rules, live NFT entry/exit pricing, live DEX liquidity for reward realization and operating costs, and an opt-in live probe.

The largest unresolved model assumption is that the Axe production constants remain current. This is acceptable for G5 because the values are explicit CONFIG, the adapter version is pinned, and market-facing values are live. A future gate should add automated rule-change monitoring if Farmers World remains a production-supported adapter.
