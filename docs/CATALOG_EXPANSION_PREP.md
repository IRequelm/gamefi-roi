# GamCryp Catalog and Referral Expansion Preparation

Status: Operations / Growth preparation
Date: 2026-08-28
Branch: `codex/post-launch-catalog-referral-prep`

This document prepares GamCryp to move from 26 reviewed opportunities toward 50+ high-quality opportunities without weakening V1 production integrity.

This is not a deployment plan and not a new adapter implementation. It does not add unverified opportunities, change ROI calculations, change Risk or Confidence, alter snapshots, change organic ranking order, or modify referral redirect behavior.

## Production Protection

Verified before this work:

- production branch is `master`;
- `origin/master` was fetched and local `master` was fast-forwarded;
- AEO/GEO sprint is merged in `origin/master` through merge commit `b725bbe`;
- work is on `codex/post-launch-catalog-referral-prep`, not `master`;
- no production deployment is part of this task.

Protected surfaces:

- ROI engine, adapters, risk/confidence scoring, snapshots/history, API contracts, referral isolation, GA4, SEO/AEO/GEO, canonical URLs, sitemap, and existing opportunity/strategy URLs.

## Current Catalog Audit

The authoritative catalog is `backend/app/strategies/catalog.py`. It currently exposes 26 reviewed opportunities and 10 modeled strategies.

With an empty referral-operations database, every published opportunity has official outbound fallback coverage and no active GamCryp referral link. Operator-entered referral programs live in monetization storage and are not part of static catalog facts.

| Opportunity | Type | Status | Financial model | Strategies | Official destination | Referral destination | Referral coverage | Missing metadata | Freshness concern | Quality concern |
|---|---|---|---|---:|---|---|---|---|---|---|
| Aavegotchi | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | needs narrow adapter for production/current execution |
| Alien Worlds | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | tool/land production probabilities unresolved |
| ARO Network | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | Jade/value route and individual share unresolved |
| Axie Infinity | GAME | candidate | Unavailable, PARKED | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | season distribution, placement probability, and entry composition unresolved |
| Big Time | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | drop rates and Hourglass constraints need evidence |
| Bless Network | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | reward formula and realizable value insufficient |
| BlockMesh | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | exact formula and current realizable value absent |
| Datagram | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | conversion and account data unresolved |
| DAWN | DEPIN_NODE | candidate | Unavailable, REJECTED | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | official terms reject current monetary value/transferability/redemption |
| DeFi Kingdoms | GAME | active | Available, GO | 3 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | strategy freshness comes from live snapshots | long lock and emergency-exit risk remain visible |
| Farmers World | GAME | active | Available, GO | 3 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | strategy freshness comes from live snapshots | low liquidity and configured zero-cost assumptions remain visible |
| Galxe | POINTS | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | points/campaign rewards lack general realizable ROI route |
| Gods Unchained | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | reward EV and pack/card realization need a narrow model |
| Grass | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | points/account data and monetary redemption unavailable |
| Illuvium | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | player-performance distribution not reproducible enough |
| Kaisar Network | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | score, epoch total, and value route unresolved |
| Kaito Yaps | POINTS | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | Yaps are not an executable financial reward |
| Layer3 | POINTS | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | generalized quest reward EV and costs vary by campaign |
| Nexus | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | conversion and market value not current inputs |
| Nifty Island | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | account Blooms, caps, and eligibility are account-scoped |
| Nodepay | POINTS | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | pool share, eligibility, and account data insufficient |
| Pirate Nation | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | task EV, item costs, and sell route need adapter evidence |
| Pixels | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | individual task allocation and sell route need adapter evidence |
| Splinterlands | GAME | active | Available, GO | 4 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | strategy freshness comes from live snapshots | probabilistic EV assumptions remain visible |
| Teneo | DEPIN_NODE | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | beta points are not financial products and data is account-scoped |
| Wild Forest | GAME | candidate | Unavailable, PARTIAL | 0 | active verified fallback | none configured | REFERRAL_MISSING | none obvious | catalog review needs routine recheck | performance distribution and allocation are not model-ready |

Catalog totals:

- opportunities: 26;
- active modeled opportunities: 3;
- candidate/watchlist opportunities: 23;
- modeled strategies: 10;
- official destination fallback: 26 / 26;
- active configured referral URLs in static catalog: 0 / 26;
- empty-DB referral operations coverage: 26 / 26 as `REFERRAL_MISSING` tasks.

## Referral Coverage

Referral coverage percentage for active configured referral links is 0.00% in the repository/static baseline.

Operational coverage is 100.00% because every published opportunity has:

- an official reviewed HTTPS destination;
- a `/go/{destination_slug}` route through the allowlisted destination slug;
- official URL fallback when no active referral program exists;
- an operator task path for missing referral research.

Missing referral targets are all 26 current opportunities:

```text
aavegotchi
alien-worlds
aro-network
axie-infinity
big-time
bless
blockmesh
datagram
dawn
defi-kingdoms
farmers-world
galxe
gods-unchained
grass
illuvium
kaisar-network
kaito-yaps
layer3
nexus
nifty-island
nodepay
pirate-nation
pixels
splinterlands
teneo
wild-forest
```

Referral absence must never block publication of an otherwise useful reviewed opportunity.

Commercial relationships must never affect ROI, Risk, Confidence, strategy snapshots, validation results, or organic ranking order. Sponsored placements, referral program status, click metrics, conversion counts, and revenue are commercial/operations data only.

## Catalog Expansion Mechanism

Use the existing static catalog path for reviewed opportunity records until a future reviewed ingestion workflow is approved:

1. Work returns a structured research package using `config/opportunities/work_research_handoff.schema.json`.
2. Operator/human review checks source quality, publication status, referral evidence, terms feasibility, and whether ROI must remain unavailable.
3. Approved candidates are transcribed into `OpportunityCatalogEntry` records in `backend/app/strategies/catalog.py`.
4. Each approved public opportunity must get exactly one reviewed official outbound destination in `OUTBOUND_DESTINATIONS`.
5. Do not add a financial strategy unless the Data Feasibility Check is `GO` and adapter-contract work is explicitly approved.
6. Run V1 catalog, referral, API, web, sitemap, and ranking integrity tests before merge.

This preserves the distinction between:

- reviewed opportunity: useful public catalog/watchlist record;
- financially modeled strategy: adapter-backed result with ROI, Risk, Confidence, history, API, and web integration.

Opportunities without lawful/reproducible value realization must show ROI as unavailable, never zero.

## Admission Checklist

Every new public opportunity candidate must include:

- active official project status;
- currently accessible opportunity state;
- understandable earning or reward mechanism;
- at least one official source;
- `GAME`, `DEPIN_NODE`, or `POINTS` category;
- reward type;
- required hardware/platform;
- capital requirement if known, or explicit unknown status;
- time/effort characteristics if known, or explicit unknown status;
- withdrawal/reward status;
- financial model feasibility: `GO`, `PARTIAL`, `PARKED`, or `REJECTED`;
- referral availability status;
- major risk notes;
- last reviewed UTC timestamp.

Do not lower quality to reach 50 opportunities. A smaller high-quality catalog is preferable to low-evidence listings.

## Work Handoff Contract

Work should return one JSON package matching:

```text
config/opportunities/work_research_handoff.schema.json
```

An example shape is available at:

```text
config/opportunities/work_research_handoff.example.json
```

Work must not calculate ROI. Financial calculations remain inside GamCryp's trusted adapter, ROI engine, scoring, and snapshot architecture.

For each candidate, Work must provide:

- canonical slug and public name;
- opportunity type;
- publication recommendation;
- official project status and accessibility;
- official URL and official source references;
- short human description;
- platforms, chains, and economy types;
- reward asset or points type;
- earning mechanism summary;
- hardware/platform requirement;
- capital requirement summary;
- time/effort profile;
- withdrawal or reward status;
- value realization status;
- financial model feasibility decision;
- risk notes;
- Data Feasibility Check evidence for reward formula, entry requirement, entry price, reward identity, exit route, market/quote route, liquidity/slippage, costs, claim/transaction costs, caps/timing, update detection, history/snapshot feasibility, and terms/collection feasibility;
- referral program evidence and application status.

## Modeling Queue

Use `config/opportunities/modeling_queue_policy.json` to rank future modeling candidates for internal planning.

The queue should prefer candidates where:

- entry cost is reproducible;
- earning rate is reproducible;
- reward value is realizable;
- withdrawal/market route is verifiable;
- recurring, operating, and transaction costs can be modeled without fake zeroes;
- caps, seasons, timing, and rule changes are observable;
- required data is machine-readable or lawfully reviewable.

The modeling queue must not use referral, affiliate, sponsor, click, conversion, revenue, or EPC inputs.

Priority labels:

- `MODEL_NEXT`: strong candidate for a Data Feasibility Check and adapter work;
- `RESEARCH_MORE`: useful catalog candidate, but not adapter-ready;
- `WATCHLIST_ONLY`: public opportunity may be useful, but financial ROI must remain unavailable.

## Test Plan For Future Catalog Batches

Before any catalog expansion merge:

- parse Work handoff JSON and reject malformed rows;
- compare the new catalog count and opportunity type distribution;
- assert every public opportunity has official HTTPS destination fallback;
- assert `/go` succeeds for known destinations and fails closed for unknown destinations;
- assert unavailable ROI is not rendered as `$0` or `0%`;
- assert existing 10 modeled strategy ROI outputs and organic ranking order are unchanged unless an explicitly approved model/version change exists;
- assert referral/commercial metadata changes do not alter ROI, Risk, Confidence, snapshots, or organic rankings;
- run backend tests, frontend tests, doctor, API probe, web probe, search/sitemap/robots checks, and `git diff --check`.

## Risks And Open Questions

- The current static catalog mechanism is safe and reviewable, but it will become cumbersome beyond roughly 50-100 entries.
- Production referral program records may exist in the operator database and are not visible in the repository; do not treat the static 0% active referral count as a production revenue report.
- Several points/DePIN candidates are useful discovery records but remain non-financial until value realization is lawful and reproducible.
- Terms/ToS feasibility must be reviewed per candidate before automated collection.
- Native program referral rewards must remain separate from GamCryp commercial referral metadata.

## Work Package Review

The first attached Work research handoff was reviewed in:

```text
docs/CATALOG_EXPANSION_BATCH_1_REVIEW.md
config/opportunities/expansion_batch_1_recommendation.json
```

The package was usable as an operator research memo, but it was Markdown and does not strictly validate against `config/opportunities/work_research_handoff.schema.json`. Future Work handoffs should use the schema JSON format before automated catalog ingestion is considered.
