# Decision 0005: G14 Opportunity Model Feasibility

Status: Implemented for G14
Date: 2026-08-23

## Context

G13 is active and remains unchanged. The user clarified that G14 must not be treated as only adding more games. G14 must evaluate and, if feasible, expand the current `Game` catalog model into a more general `Opportunity` model while preserving compatibility with the existing GameFi adapters.

The current product already treats `Strategy` as the primary modeled object, and history/risk/confidence/ROI outputs are keyed by strategy id and strategy version. The main game-specific coupling is in catalog/API/web naming around `game_id`, `games`, and `game_name`, not in the ROI engine itself.

## Decision

The `Game` to `Opportunity` expansion is feasible as a backward-compatible additive change.

G14 should introduce a canonical `Opportunity` catalog where:

- `GAME` covers existing GameFi games,
- `DEPIN_NODE` covers node, bandwidth, compute, storage, or resource-contribution networks,
- `POINTS` covers points/pre-token/reward-credit programs where financial value may be unavailable.

Existing GameFi records remain `GAME` opportunities. Existing strategy ids, strategy versions, adapter outputs, historical snapshots, and ROI engine semantics must remain stable.

Backward-compatible implementation rules for G14:

- Keep existing `game_id` values for DeFi Kingdoms, Farmers World, and Splinterlands.
- Keep `/api/v1/games` as a compatibility surface for GAME opportunities.
- Add canonical `opportunity_id`, `opportunity_type`, and `opportunity_name` fields before deprecating game-specific naming anywhere.
- Do not require the ROI engine to know game ids, opportunity ids, opportunity types, provider names, or adapter modules.
- Do not publish financial ROI for points-only opportunities unless a lawful, reproducible, realizable value route exists.
- Treat missing realizable value as unavailable, never as zero.
- Make the G14 referral/outbound foundation reference opportunities and strategies, not only games.

## G14 implementation result

G14 implements the Opportunity expansion as static catalog metadata rather than as new ROI adapters.

Code anchors:

- `backend/app/strategies/catalog.py` defines `OpportunityCatalogEntry`, `OutboundDestination`, and compatibility `GameCatalogEntry` records.
- `/api/v1/opportunities` and `/api/v1/opportunities/{opportunity_id}` expose the canonical catalog.
- `/api/v1/games` remains a GAME-only compatibility view for DeFi Kingdoms, Farmers World, and Splinterlands.
- `/go/{destination_slug}` resolves only active, verified, allowlisted outbound destinations and fails closed otherwise.

The first G14 catalog contains 10 reviewed opportunities total:

1. DeFi Kingdoms
2. Farmers World
3. Splinterlands
4. Grass
5. Teneo
6. ARO Network
7. Nodepay
8. DAWN
9. BlockMesh
10. Bless Network

No financial ROI adapter was added for non-game candidates in G14. Their opportunity pages may show feasibility, source, and outbound metadata, but ROI remains unavailable where value realization is not lawful, reproducible, and executable.

## Candidate feasibility notes

These are initial feasibility notes for G14 planning, not adapter approvals.

| Candidate | Type | Evidence summary | Machine-readable status | G14 feasibility |
|---|---|---|---|---|
| DeFi Kingdoms | `GAME` | Existing G4 adapter has sourceable cJEWEL/JEWEL economics, market value, exit penalty assumptions, and production snapshots. | Existing live adapter/probe path. | `GO`; unchanged GAME opportunity. |
| Farmers World | `GAME` | Existing G5 adapter has deterministic resource production, entry value, marketplace realization, costs, and snapshots. | Existing live adapter/probe path. | `GO`; unchanged GAME opportunity. |
| Splinterlands | `GAME` | Existing G6 adapter has SPS expected-value model, explicit uncertainty, costs, and snapshots. | Existing live adapter/probe path. | `GO`; unchanged GAME opportunity. |
| Grass | `DEPIN_NODE` | Official terms state Points have no monetary value and are not redeemable or transferable. Public docs describe points/reward participation, but value realization is not a public executable route. | Official docs/site exist; individual node data appears account/dashboard scoped. Automated collection needs permission review. | `PARTIAL` for opportunity metadata; financial ROI unavailable. |
| Teneo | `DEPIN_NODE` | Official docs describe heartbeat and data-signal points, with beta points reflecting participation rather than financial products. | Official docs exist; individual account/dashboard data is not a reviewed public API. | `PARTIAL` for opportunity metadata; financial ROI unavailable. |
| ARO Network | `DEPIN_NODE` | Official docs describe ARO node types, Testnet S2 Jade emissions, Badges, referral Jade, and possible future drops. | Official docs/dashboard exist; exact individual share, account data, and realizable value are not publicly reproducible. | `PARTIAL` for opportunity metadata; financial ROI unavailable. |
| Nodepay | `POINTS` | Official docs describe Signal/Node Points, cycle aggregation, eligibility checks, and possible conversion into Nodecoin. | Official docs exist; pool share, account eligibility, and automated account data are not sufficiently sourceable. | `PARTIAL`; financial ROI unavailable until conversion/value inputs are reproducible. |
| DAWN | `DEPIN_NODE` | Official terms state Rewards have no monetary value, may never convert to assets, and are not transferable or redeemable. | Official terms exist; no financial value route is lawful under current terms. | `REJECTED` for financial ROI; catalog-only candidate. |
| BlockMesh | `DEPIN_NODE` | Official FAQ says points track contributions and help determine token eligibility. | Official docs exist; exact formula, individual data access, and realizable value are insufficient. | `PARTIAL`; financial ROI unavailable. |
| Bless Network | `DEPIN_NODE` | Official docs describe browser/native node participation and rewards; public docs do not provide enough current individual earning/value data for ROI. | Official docs/site exist; reward formula and realizable value are insufficient. | `PARTIAL`; financial ROI unavailable. |

Source references reviewed:

- Grass Points: https://grass-foundation.gitbook.io/grass-docs/how-to-guide/grass-points
- Grass Terms and Conditions: https://www.grass.io/terms-and-conditions/
- Grass Stage 2 rewards explanation: https://www.grass.io/learn/how-your-stage-2-rewards-allocation-works/
- Teneo Rewards and Tokenomics: https://teneo.gitbook.io/teneo-docs/rewards-and-tokenomics
- Teneo Community Node: https://teneo-protocol.ai/community-node
- Teneo Terms of Service: https://legal.teneo.pro/terms
- Nodepay Rewards System: https://docs.nodepay.ai/user-participation-and-rewards/rewards-system
- Nodepay Nodecoin Utility: https://docs.nodepay.ai/nodecoin-usdnc/utility-of-usdnc
- ARO Testnet S2: https://docs.aro.network/campaign-hub/testnet-s2/
- ARO Referral Program: https://docs.aro.network/campaign-hub/referral-program/
- ARO Dashboard docs: https://docs.aro.network/node-operator-guide/become-operator/aro-dashboard/
- DAWN Terms and Conditions: https://www.dawninternet.com/terms
- BlockMesh FAQ: https://block-mesh.github.io/docs/faq/faq.html
- Bless Run a Node Introduction: https://docs.bless.network/run-a-node/introduction
- Bless About: https://bless.network/about

## Feasibility conclusion

The model expansion is feasible, but the first non-game candidates are not yet clear GO candidates for financial ROI adapters.

Reasons:

- The existing ROI engine can model generic capital, reward value, costs, break-even, ROI, exit-adjusted P&L, and uncertainty when a realizable reward value exists.
- Points-only programs often lack transferable value, deterministic conversion, or executable exit routes.
- User/account dashboards may require authenticated access, and automated collection must be reviewed against terms and permissions.
- Many DePIN/points rewards depend on hidden variables such as geography, demand, bandwidth quality, uptime quality, future airdrop policy, or discretionary eligibility.

Therefore G14 implements the Opportunity catalog and referral/outbound foundation. A non-game ROI adapter remains a separate scoped decision after the expanded Data Feasibility Check produces a GO result.

## Referral/outbound foundation

G14 outbound metadata is structured around reviewed destinations:

- stable `destination_id` and `destination_slug`,
- `opportunity_id`, `opportunity_type`, optional compatibility `game_id`, and optional `strategy_id`,
- destination type and label,
- `official_url`, optional `referral_url`, optional `referral_code`, optional `affiliate_program`,
- status, commercial relationship, affiliate boolean, disclosure text, source reference, review timestamp, verification status, allowed surfaces.

The API exposes safe product metadata and a first-party `redirect_url` shaped as `/go/{destination_slug}`. Web links use that first-party redirect.

Click tracking in G14 is limited to a minimal server log event with destination/opportunity/commercial relationship fields. It does not set cookies, fingerprint users, store per-user click records, implement conversion attribution, or report affiliate revenue. Those are G15 concerns and must remain separated from snapshots, scores, and rankings.

Commercial relationships are explicitly excluded from:

- ROI engine inputs,
- adapter observations,
- risk/confidence scoring,
- historical snapshots,
- organic ranking order,
- validation results.

## Rework risks avoided

- Do not rename existing GameFi adapters merely to match the new taxonomy.
- Do not overload `game_id` as the only canonical identity for non-game opportunities.
- Do not add opportunity-type branches to the ROI engine.
- Do not treat native referral rewards as GameFi ROI commercial referral metadata.
- Do not let affiliate/sponsor status influence ROI, Risk, Confidence, history snapshots, validation, or organic rankings.
- Do not publish financial ROI for points-only opportunities with unavailable value realization.
