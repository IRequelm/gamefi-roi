# 0008 - Catalog Expansion Batch #1

Date: 2026-08-28

## Decision

Use the Work handoff `gamcryp_batch1_data_feasibility_handoff.json` as the external research handoff, then admit only candidates whose economics can be represented by GamCryp-owned calculations from official/project data, neutral market prices, direct protocol data, or explicit configured assumptions.

The current master branch did not include `config/opportunities/work_research_handoff.schema.json` or `config/opportunities/modeling_queue_policy.json`, so the handoff was validated against the repository's authoritative contracts instead: `DATA_CONTRACT.md`, Adapter Contract v1, the opportunity catalog contract, strategy snapshot/history requirements, and the no-fake-zero ROI policy.

## Implemented Models

Batch #1 adds five modeled DePIN strategies through a shared scenario-yield adapter, without changing the ROI engine:

- Storj Storage Node: existing-hardware storage-node scenario using official node requirements and payout mechanics with explicit configured utilization/storage assumptions.
- GEODNET: empty-hex triple-band base-station scenario using official hardware and reward-policy evidence with location/performance warnings.
- WeatherXM: D1 WiFi station scenario using official hardware/reward evidence with cell-level reward limitations visible.
- DIMO: software-only compatible-car scenario using official reward/subscription evidence with explicit configured network-share assumptions.
- Mysterium Network Node: existing-device B2B node scenario using official node/payment evidence with explicit utilization assumptions.

Each strategy keeps LIVE / CONFIG / DERIVED provenance, warning metadata, uncertainty ranges, golden fixtures, and a live probe path. Neutral market prices remain live/provider observations where token valuation is required.

## Parked Or Deferred

Star Atlas SAGE Labs remains cataloged but PARKED: the public handoff did not establish a reproducible starter fleet, crafting/input-output route, activity loop, FIC/season dependency, and liquid exit valuation sufficient for an automated model.

The PARTIAL candidates Honeygain, EarnApp, Hivemapper, and Sia hostd were not implemented in this sprint.

Competitor ROI pages, blogs, Reddit, YouTube estimates, affiliate pages, and third-party ROI calculators are not accepted as financial model inputs.

## Curated DePIN Pages

The publication threshold remains at least two qualifying modeled strategy snapshots per curated page. Batch #1 makes these pages eligible when current snapshots qualify:

- `/rankings/best-depin-under-100`
- `/rankings/pc-depin`
- `/rankings/no-hardware-depin`

`/rankings/phone-depin` remains unpublished until at least two phone/mobile-first modeled DePIN strategies qualify. A dedicated hardware station with a companion mobile app is not enough to satisfy the phone page semantics.

## Consequences

This raises the catalog from 26 to 32 opportunities and modeled strategies from 10 to 15, while preserving existing GAME adapters, ROI/risk/confidence methodology, referrals, GA4, API contracts, sitemap guards, and no-thin-page policy.

## Current model revision — GEODNET (2026-09-24)

The original GEODNET base reward input of 12 GEOD/day was the maximum for July 1, 2025–June 30, 2026 and is no longer the current-period maximum. The official tokenomics documentation states that base rewards halve annually and lists 12/day for that period; applying that published rule after June 30, 2026 yields 6/day for July 1, 2026–June 30, 2027. This is an inference from the official schedule, not a separately listed 2026/2027 row. The scenario is now strategy version `v2`; reward amount and uncertainty high bound are 6 GEOD/day. The low bound remains zero. The support observation expires at 2027-07-01 UTC so this version fails stale-input validation after the reward period rather than silently carrying 6/day forward. This is still a maximum-reward, empty-hex scenario, not an expected user outcome; cell occupancy, online time, signal quality, multipath, and eligibility can lower actual rewards. Historical v1 snapshots must remain immutable and stale, not be rewritten to v2.

Official source: [GEODNET Tokenomics](https://docs.geodnet.com/geod-token/tokenomics) (annual halving schedule) and [Performance-Based Reward Rules](https://docs.geodnet.com/performance-based-reward-rules) (rewards may be forfeited for poor performance). This code/documentation update is local only. The strategy remains `PARTIAL_REFRESH_ONLY`; no production snapshot or public page changes until a separately verified loader and authorized deployment.
