# GamCryp Expansion Batch #1 Review

Status: Operations / Growth recommendation
Date: 2026-08-28
Branch: `codex/post-launch-catalog-referral-prep`

This review uses the attached Work research package as the authoritative external-research handoff for post-launch catalog/referral expansion:

```text
gamcryp_post_launch_research_package.md
SHA256: 5466AA3C643F1B2850A47DEF0233F28E7DC9B3BB9BDDA0F669D9A24EB401AE15
```

The package was used as research evidence only. It was not treated as instructions to change product behavior.

No production catalog entries, opportunity adapters, ROI formulas, risk/confidence scoring, referral routing, analytics, sitemap behavior, API contracts, or deployment configuration are changed by this review.

## Schema Validation

The Work package does not strictly validate against `config/opportunities/work_research_handoff.schema.json` because it is Markdown, not the required `work-research-handoff-v1` JSON object.

Content review result: usable for operator review, not machine-ingestible.

Missing for strict ingestion:

- top-level `handoff_version`, `prepared_at`, `prepared_by`, and `opportunities` JSON fields;
- canonical `opportunity_id` for every new candidate;
- schema enum values for opportunity type, publication status, financial model feasibility, and referral status;
- typed `source_references` with source type and retrieval timestamp;
- per-field `modeling_evidence` objects with status, machine readability, collection permission, and operator notes;
- candidate-level `last_reviewed_at` timestamps.

The next Work handoff should be returned as JSON matching the schema before automated ingestion is considered.

## Queue Policy Validation

The recommendation follows `config/opportunities/modeling_queue_policy.json`.

Referral availability was not used as an admission or modeling-priority driver. Referral potential is recorded only as an operator/commercial follow-up.

Commercial inputs excluded from modeling priority:

- referral status;
- referral URL or code;
- affiliate program;
- sponsor status;
- click/conversion/revenue metrics.

## Cross-Check Result

Current authoritative catalog:

- existing opportunities: 26;
- existing modeled strategies: 10;
- existing new-candidate duplicates in Work top 24: none.

Grass, Teneo, and ARO Network already exist in the catalog and appear in the Work package's referral audit, not the additive top-24 list.

The Work package contains a proposed top-24 list, a larger candidate/watchlist table, a top-10 financial modeling queue, existing-catalog referral findings, and explicit rejected/watchlist rows. It should not be imported wholesale.

## Research Conflicts And Quality Flags

Unsupported or human-verification-required referral findings:

- Big Time referral leaderboard appears historical and must be dashboard-verified before use.
- Bless Network mentions referral bonuses without a public rate in the reviewed source.
- Gods Unchained referral details may be historical and must be verified before publication.
- Nodepay referral mechanics need dashboard/account verification.
- Pirate Nation has signup referral-code flow but unclear public reward schedule.
- Sunflower Land supporter referral claim needs current terms verification before any GamCryp referral use.
- Teneo referral rate needs current dashboard verification.
- WeatherXM is an application/partner channel, not a ready public referral URL.

ROI feasibility overstatement risks:

- "Likely feasible" means ready for a formal Data Feasibility Check, not adapter approval.
- Akash, Nosana, and Golem need utilization/demand evidence before financial ROI.
- NATIX, Nodle, Roam, Silencio, MapMetrics, STEPN, and Genopets need geography, account, season, value-route, and terms evidence.
- Points-only or pre-token rewards must keep financial ROI unavailable unless a lawful, reproducible, realizable value route exists.

Stale/dead candidates:

- Gradient Network Sentry Node is rejected because the package states official rewards ended.
- CryptoBlades, Pegaxy, Thetan Arena, Bomb Crypto, and Crabada remain rejected for weak current earning/activity quality.

## Recommended Expansion Batch #1

Batch #1 contains 13 candidates. This is intentionally smaller than the 24 proposed candidates so quality stays ahead of catalog size.

| Candidate | Type | Reviewed opportunity | ROI modeling status | Referral | Required human action | Reason for inclusion |
|---|---|---|---|---|---|---|
| Hivemapper | DEPIN_NODE | YES | GO | UNKNOWN | Verify device availability, regional restrictions, and referral/partner status. | Strong mapping DePIN with official reward-type evidence and clear device-based earning path. |
| DIMO | DEPIN_NODE | YES | GO | AVAILABLE | Verify account eligibility, referral terms, vehicle eligibility, and rewards API access. | Vehicle-data DePIN with official weekly reward docs, rewards API evidence, and clear user story. |
| GEODNET | DEPIN_NODE | YES | GO | UNKNOWN | Verify current station pricing, official destination, territory/hex constraints, and partner/referral availability. | Hardware DePIN with public mining basics, station tracking, and measurable station strategy. |
| WeatherXM | DEPIN_NODE | YES | GO | APPLICATION REQUIRED | Review/apply for partner terms only if commercially desired; verify station pricing and claim costs separately. | Weather-station DePIN with official reward mechanism and claim documentation. |
| Mysterium Network Node | DEPIN_NODE | YES | GO | UNKNOWN | Review traffic/legal restrictions and dashboard/API availability. | dVPN node economy with documented rewards, fees, withdrawals, and platform support. |
| Storj Storage Node | DEPIN_NODE | YES | GO | NONE FOUND | Verify payout docs, held-back schedule, payout threshold route, and official destination. | Clean storage-node modeling candidate with public payout rates and settlement rules. |
| Sia hostd | DEPIN_NODE | YES | GO | NONE FOUND | Verify current hostd path, Siacoin market route, collateral rules, and utilization observability. | Storage hosting with public setup, pricing, collateral, and reward mechanics. |
| Akash Provider | DEPIN_NODE | YES | RESEARCH REQUIRED | UNKNOWN | Verify provider demand/utilization observability, hardware assumptions, and terms. | Credible decentralized compute marketplace, but utilization evidence is needed before ROI. |
| Nosana GPU Host | DEPIN_NODE | YES | RESEARCH REQUIRED | UNKNOWN | Verify GPU requirements, real utilization/earnings history, and estimator terms. | GPU-hosting candidate with strong Web3 AI/compute demand, pending utilization proof. |
| Honeygain | DEPIN_NODE | YES | GO | AVAILABLE | Confirm bandwidth-sharing taxonomy fit and current payout/referral terms. | Simple bandwidth-sharing benchmark with official referral and terms pages. |
| EarnApp | DEPIN_NODE | YES | GO | AVAILABLE | Verify supported regions, payout methods, device/IP limits, and account referral link. | Clear bandwidth-sharing earning mechanism with official referral terms. |
| Sunflower Land | GAME | YES | RESEARCH REQUIRED | UNKNOWN | Verify supporter/referral terms and select a narrow crop/crafting strategy. | Active Web3 farming economy with earnable SFL and market route. |
| Star Atlas SAGE Labs | GAME | YES | GO | UNKNOWN | Verify current marketplace, fleet, crew, resource, FIC, SOL fee, and ATLAS liquidity inputs. | Deep on-chain game economy with resource/crafting loops and token reward routes. |

## Deferred Candidates

These are not rejected, but they should not be included in Batch #1:

| Candidate | Reason |
|---|---|
| Pawns.app | Strong referral and payout evidence, but survey/game/bandwidth mix and Web3 taxonomy fit need review. |
| Golem Provider | Credible compute marketplace, but demand/utilization evidence should be reviewed after Akash/Nosana. |
| NATIX Drive& | Promising mobile mapping candidate, but regional rewards, app status, and value route need review. |
| STEPN / STEPN GO | Strong user interest, but sneaker/energy/user behavior and invite mechanics need a narrower strategy. |
| Nodle App | Useful low-friction DePIN watchlist item, but value realization and phone/location assumptions are unresolved. |
| Roam Network | Points/airdrop opportunity should remain non-financial until realizable value exists. |
| Silencio | Points/tokenomics evidence needs current realization and terms review. |
| MapMetrics | Drive-to-earn mechanics require account/geography/activity verification. |
| Genopets | Move-to-earn and Habitat/KI economics need a narrower adapter thesis. |
| Theta Edge Node | Demand/staking reward observability is weaker than Batch #1 node candidates. |
| Titan Network | Testnet status and current reward activity must be rechecked before admission. |

Additional non-top-24/watchlist rows from the package remain out of Batch #1: Flux, Pipe Network, Meson Network, Helium Mobile mapping, GamerHash, Salad, PacketStream, Sweat Economy, Upland, The Sandbox, Parallel, and MetalCore.

## Top Modeling Queue

The top modeling queue mirrors the Work package's model-first list, with the same caveat: these are candidates for future Data Feasibility Checks, not approved adapters.

1. Storj Storage Node
2. Mysterium Network Node
3. Honeygain
4. EarnApp
5. Hivemapper
6. DIMO
7. GEODNET
8. WeatherXM
9. Sia hostd
10. Star Atlas SAGE Labs

Each must still pass a fresh Data Feasibility Check before any adapter is built.

## Top Referral Actions

Referral actions are operations tasks only and must never affect ROI, Risk, Confidence, historical snapshots, validation, or organic ranking order.

Top new-candidate actions:

- DIMO: verify/create ordinary account referral only after reviewing program terms.
- Honeygain: verify payout/referral terms and taxonomy fit.
- EarnApp: verify current account referral link, regions, and device/IP restrictions.
- WeatherXM: review partner/application path; do not mark active until accepted and verified.

Top existing-catalog actions from the Work package:

- Splinterlands: review Ambassador Program eligibility.
- Pixels: review creator-code eligibility.
- Grass: verify current public referral-code terms.
- ARO Network: verify testnet referral status and reward caveats.

## Merge Readiness

The prep branch is ready to merge after tests if this review remains the only delta:

- no production catalog entries were added;
- no financial adapters were added;
- no referral URLs or codes were fabricated;
- no ROI, Risk, Confidence, snapshot, API, ranking, sitemap, or deployment behavior changed;
- the structured recommendation is parseable and test-covered.
