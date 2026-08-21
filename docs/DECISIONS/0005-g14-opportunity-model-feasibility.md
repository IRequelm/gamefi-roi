# Decision 0005: G14 Opportunity Model Feasibility

Status: Planned for G14; not implemented during G13
Date: 2026-08-22

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

## Candidate feasibility notes

These are initial feasibility notes for G14 planning, not adapter approvals.

| Candidate | Type | Evidence summary | Machine-readable status | Initial feasibility |
|---|---|---|---|---|
| Grass | `DEPIN_NODE` + `POINTS` | Official Grass docs describe Uptime Points, Network Points, a fixed daily Network Points pool, referral percentages, and Stage 2 reward mechanics. Grass terms state points/rewards are discretionary and points have no monetary value. | Official docs and dashboard exist; no reviewed public API for user/node earnings was found in this scan. Automated collection and account/dashboard use need legal/ToS review. | `PARTIAL` for opportunity metadata and points-production explanation; `PARKED` for financial ROI adapter until official/authorized machine-readable data and realizable value evidence exist. |
| Teneo | `DEPIN_NODE` + `POINTS` | Official docs describe Community Node points, heartbeat rewards, data-signal points, beta status, and no-financial-product framing. Official site and release notes describe Beacon, fragments, boost cycles, referral percentages, and seasons. | Public docs exist; dashboard/account data appears user-authenticated. No reviewed public API for earnings/referrals was found in this scan. | `PARTIAL` for points-production modeling; `PARKED` for financial ROI adapter until value realization and authorized data access are available. |
| ARO | `DEPIN_NODE` + `POINTS` | Official ARO docs describe Testnet S2, Jade points, daily emissions split between ARO Lite and standard nodes, referral percentages, referee boost, and future $ARO drop relevance. | Official docs/dashboard/explorer exist; no reviewed public API for individual earnings or exact share calculation was found in this scan. | `PARTIAL` for opportunity metadata and points-production explanation; `PARKED` for financial ROI adapter until individual reward formula, data access, and realizable value are sourceable. |

Source references reviewed:

- Grass Points: https://grass-foundation.gitbook.io/grass-docs/how-to-guide/grass-points
- Grass Terms and Conditions: https://www.grass.io/terms-and-conditions/
- Grass Stage 2 rewards explanation: https://www.grass.io/learn/how-your-stage-2-rewards-allocation-works/
- Teneo Rewards and Tokenomics: https://teneo.gitbook.io/teneo-docs/rewards-and-tokenomics
- Teneo Community Node: https://teneo-protocol.ai/community-node
- Teneo Terms of Service: https://legal.teneo.pro/terms
- ARO Testnet S2: https://docs.aro.network/campaign-hub/testnet-s2/
- ARO Referral Program: https://docs.aro.network/campaign-hub/referral-program/
- ARO Dashboard docs: https://docs.aro.network/node-operator-guide/become-operator/aro-dashboard/

## Feasibility conclusion

The model expansion is feasible, but the first non-game candidates are not yet clear GO candidates for financial ROI adapters.

Reasons:

- The existing ROI engine can model generic capital, reward value, costs, break-even, ROI, exit-adjusted P&L, and uncertainty when a realizable reward value exists.
- Points-only programs often lack transferable value, deterministic conversion, or executable exit routes.
- User/account dashboards may require authenticated access, and automated collection must be reviewed against terms and permissions.
- Many DePIN/points rewards depend on hidden variables such as geography, demand, bandwidth quality, uptime quality, future airdrop policy, or discretionary eligibility.

Therefore G14 should first implement the Opportunity catalog and referral/outbound foundation. A non-game ROI adapter should be a separate scoped decision after the expanded Data Feasibility Check produces a GO result.

## Rework risks avoided

- Do not rename existing GameFi adapters merely to match the new taxonomy.
- Do not overload `game_id` as the only canonical identity for non-game opportunities.
- Do not add opportunity-type branches to the ROI engine.
- Do not treat native referral rewards as GameFi ROI commercial referral metadata.
- Do not let affiliate/sponsor status influence ROI, Risk, Confidence, history snapshots, validation, or organic rankings.
- Do not publish financial ROI for points-only opportunities with unavailable value realization.
