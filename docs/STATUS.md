# GameFi ROI — Project Status

Updated: 2026-09-24
Project version: 0.1

2026-09-09 distribution hardening: autonomous worker execution is restricted to the quality-gated Short handoff, the one-public-Short daily cap is process-locked, and an atomic worker heartbeat is emitted for operator health checks. The local Task Scheduler runner anchors execution at the repository root; re-registration still requires Windows task-registration permission.

V2 finish-pass operational truth is maintained in `docs/MASTER_CONTROL.md`; this document remains the authoritative gate board and currently has no numbered gate active.

2026-09-10 product-hardening pass: the public-beta label removal, opportunity-diversified homepage model view, repeated-strategy grouping, and distribution hardening were deployed as `cbf28b0` and passed controlled public-route verification. Snapshot refresh was manually triggered after deploy and completed successfully; provider/data-contract limitations remain explicitly surfaced.

## Current state

**PROJECT STATUS: V1 COMPLETE — OPERATIONS / GROWTH MODE**

2026-09-26 live growth recheck: commits `822b6a1` and `6cd2812` are deployed and verified on `https://gamcryp.com/`; the homepage and full catalog distinguish fresh strategies from prior models without current data. Search/type filters preserve all 51 catalog records. One manual recalculation for the 16:00–20:00 UTC window (GitHub Actions run `36255076672`) completed at 16:20 UTC with 7 new snapshots; production was `ok`, 7/7 eligible strategies fresh, 8/15 total strategies stale or structurally unrefreshable, zero unresolved failures, and only two opportunities with current results. A core Farmers World capital bug was found: 3- and 10-Axe strategies used one NFT floor listing as the entire basket cost. Commit `7c84f01` now queries the required number of distinct cheapest listings and fails closed on insufficient depth. It is deployed to Render as `dep-darvmal9fdbs73b960g0`. The first follow-up workflow run `36257831828` reused the existing cadence-window snapshots (`auto_refreshed=0`). Workflow commit `e06ef7e` added an explicit 60-minute window choice for manual recovery dispatches; scheduled cadence remains 240 minutes. Manual run `36258122383` then produced 7 new snapshots, zero failures, and live `/api/v1/ops/status` returned 7/7 eligible fresh. Public strategy page `/strategies/farmers-world-axe-wood-production-10x` now shows $0.0343 capital, 0.14% modeled 30-day ROI, and 20,757-day break-even; the previous 1.69% / 1,778-day values appear only as historical comparison. Eight of 15 total strategies remain stale or structurally unrefreshable, and only two opportunities have current results. Refresh policy continues to exclude three quarantined DFK strategies (RPC source/balance not validated), Storj (no approved live economics loader; October payout denomination changes to USDC), and four partial DePIN models (required economics absent). Consented browser identity now joins its `/go` redirect event in PostHog; unconsented traffic remains anonymous. See `docs/GROWTH_OPERATING_PLAN.md` for acquisition evidence and priorities.

G12 is complete and frozen in the G12 baseline Git commit.

G13 is complete for the accepted public beta deployment. The repository contains both free-beta and paid-production Render blueprints. A 2026-09-24 Render dashboard check found the active Blueprint still points to root `render.yaml` (Free web, no Render Cron); the live web service is Free, while the PostgreSQL database is now Available on plan `0.1c-256mb`. The last attempted Blueprint sync failed because the beta file would downgrade that database to Free. `render.production.yaml` is not active. GitHub Actions remains the only verified production refresh scheduler; see `docs/MASTER_CONTROL.md` for current operational truth.

G14 is complete in the repository. It adds the backward-compatible Opportunity catalog, referral/outbound foundation, and public-beta UI readability pass. Render auto-deploy remains off from G13, so the current public URL must be manually deployed to serve the G14 routes and UI.

G14 post-deployment UI acceptance follow-up: the first deployed G14 UI still looked too much like an internal analytics/debug surface on the public Home/ROI Finder. A corrective G14 fix was added before any G15 monetization work to make the public beta user-readable: responsive strategy cards replace ranking tables, Decimal API strings remain authoritative but are formatted for display, tiny/scientific values are readable, confidence/risk/freshness interpretation is explicit, and opportunity cards show unavailable ROI for non-financial candidates instead of zero.

G14 post-deployment brand/UI refinement: before G15 monetization work, the public beta received a GamCryp visual pass based on the supplied visual references. This is presentation-only: backend logic, ROI calculations, ranking logic, adapters, API contracts, referral logic, and opportunity modeling remain unchanged. The live structure stays card-based while the visual language moves to dark navy surfaces with restrained cyan/blue/violet accents and semantic risk/confidence colors preserved.

G15 is complete in the repository. It adds a monetization foundation on top of the G14 referral layer: privacy-minimal `/go/...` click persistence, referral lifecycle metadata, verified/manual revenue attribution foundations, sponsored placement metadata, commercial analytics metrics, disclosure documentation, and a tighter conversion-oriented public UI. ROI, Risk, Confidence, historical snapshots, validation, and organic ranking order remain analytically isolated from affiliate/sponsor/commercial data.

G16 is complete in the repository. It adds server-visible public HTML, page-specific metadata, canonical URL inventory, sitemap, robots policy, operator-triggered IndexNow support, and privacy-minimal inbound acquisition attribution. ROI calculations, adapters, risk/confidence methodology, historical snapshots, monetization attribution, sponsored placement separation, and organic ranking logic remain unchanged.

Post-G16 production scheduler fix: the GitHub Actions beta recalculation workflow now exports `GAMEFI_PUBLIC_BASE_URL` as a non-secret production env value, with a GitHub repository variable override for future custom domains. This fixes the production settings validation regression introduced by G16 without changing ROI, adapters, scoring, ranking, API contracts, or monetization logic.

G17 is complete in the repository. It adds referral operations coverage states, a single-operator protected console, safe referral metadata editing, work queue generation, stored-metadata health checks, and manual verified revenue entry. Referral, sponsor, click, and revenue data remain outside ROI, Risk, Confidence, strategy snapshots, validation, and organic ranking order.

G18 is complete. The current catalog has 51 opportunities and 15 modeled strategies; the historical G18 acceptance baseline remains 26 opportunities and 10 modeled strategies. At gate close, a scheduled recalculation had succeeded with 10 scored snapshots and no failures. Current runtime differs: the Render web service is Free, the database is `0.1c-256mb`, and the latest observed scheduled recalculation (#351) is over 40 minutes old while the public rankings show no current matches. No mandatory implementation gate is active. Future work should be classified as Operations, Growth, V1.x improvement, or V2 proposal. See `docs/MASTER_CONTROL.md` for current operational truth.

Post-checkpoint correction (2026-09-24): user-authorized manual run #352 completed successfully and direct browser verification then showed 7 current ranking cards (3 Farmers World, 4 Splinterlands). The run was degraded with 8/15 catalog strategies skipped; a single immediate success does not establish sustained cadence. A separate homepage content extraction still returned zero modeled strategies/no matches, so crawler/rendered-output consistency remains unresolved. See Master Control checkpoint 0v.

Follow-up (2026-09-24): the seven rankings disappeared again by 22:51 UTC (run #352 snapshots calculated 22:45:56 UTC) and no scheduled run had appeared as of 22:55 UTC. A local distribution-worker diagnostic was repaired to parse its ISO heartbeat and now accurately detects that the recorded worker PID is stopped. Correction from a later local state check: the YouTube Shorts automation subsequently uploaded `inventory-how_to_use_gamcryp-home` at 2026-09-24 01:56 Europe/Istanbul (video id `M6I1OZzOoyc`), then respected its one-publication-per-local-day cap; worker process 9184 was still running at 02:16. The X/distribution worker remains stopped and Task Scheduler registration remains unverified. See Master Control checkpoints 0w–0aa.

Post-G18 launch polish is an Operations/Growth patch, not a gate reopen. It cleans public-facing labels, opportunity-card explanations, CTA relationship text, footer contact links, and optional consent-gated GA4 readiness while preserving ROI formulas, adapters, scoring, snapshots, API contracts, referral routing, monetization separation, and organic ranking order.

2026-09-24 growth follow-up: local home/rankings stale-result fallback and `utm_content` capture remain undeployed. A renderer reliability fix now uses repository-root assets independently of the current working directory and reports failed-render audio mode accurately. Targeted backend tests pass 43/43 and frontend tests pass 57/57; the full backend suite completed without a failed-test summary, but Windows pytest temp cleanup still emits a sandbox `PermissionError`. `compileall`, dependency check, and `git diff --check` pass. This is not production acceptance: refresh cadence/data coverage, live measurement, X automation, deployment safety, and user acquisition performance remain unresolved. No numbered gate is active.

Latest operations check (2026-09-24 03:54 Europe/Istanbul): GitHub Actions still lists scheduled run #353 at 02:59 and only manual run #354 at 03:36; the five-minute cron expression has not sustained five-minute freshness. The scoped history-fallback/UTM release was locally tested and committed only in an isolated candidate checkout (`78a9a8c`); it is not pushed, deployed, or migrated. A paid Render Cron is already described in `render.production.yaml`, but adding/syncing that resource and configuring its production secrets require separate cost and credentials approval. Based on the observed 41-second execution every five minutes, its rough Cron-only runtime bill would be about $5.92/month including Render's $1 minimum, subject to actual runtime/configuration. See Master Control checkpoint 0b13.

Acquisition measurement recheck (2026-09-24): GA4 last-28-day aggregate output shows 62 sessions and 4 active users, including 22 explicitly operator/test-labelled sessions, 36 without manual source attribution, and four tagged X/t.co sessions. Repeated date-grain reads sum to 63 sessions and reach 2026-09-22; the 1-session aggregation mismatch is unexplained. There were 3 outbound clicks and 3 start clicks; two of each came from `codex_smoke`, and the rest were untagged. Search Console shows 127 impressions, zero clicks, with latest returned data dated 2026-09-19. This does not substantiate user acquisition, content conversion, or revenue; tracking release and clean post-deploy measurement remain prerequisites to marketing scale-up. See Master Control checkpoint 0b14.

Render state recheck (2026-09-24 04:04 Europe/Istanbul): the active `gamefi-roi` Blueprint currently manages only the web service and paid database (`0.1c-256mb`); it has no Cron. Its latest sync reports a problem, and root `render.yaml` still declares the database Free. Do not sync a Cron addition until the blueprint accurately preserves the existing database plan and the requested Cron spend/secret binding are approved. No Render state was changed. See Master Control checkpoint 0b15.

User-directed scheduler adjustment (2026-09-24): the user confirmed five-minute refreshes are unnecessary and requested a free, lower-frequency cadence. Commit `6f4ef3c` configures the local GitHub Actions workflow for four-hour runs, with six-hour source freshness and an eight-hour hard-stale guard. It has not been pushed/deployed; effective cadence and public ranking availability are not yet verified. No paid Render Cron was added. See Master Control checkpoint 0b16.

Resumed operations check (2026-09-24): remote GitHub `master` remains on the five-minute workflow; latest scheduled run #355 refreshed seven eligible strategies and left eight stale/skipped. Local stale-history and UTM changes pass targeted backend and frontend tests, but UTM migration `20260924_0012` is not deployed. A remote push was blocked by this session's GitHub-write approval/network restrictions; the four-hour cadence is not yet active. See Master Control checkpoint 0b17.

Latest local automation check (2026-09-24 12:10 Europe/Istanbul): YouTube Short worker PID 9184 is alive but at its one-publication daily cap; no matching Windows scheduled task was found. Distribution/X worker PID 33700 is stopped despite an old `ok` heartbeat, and its latest live discovery log reports X API HTTP 402 `credits depleted`. No worker or publication was started. The local four-hour workflow commit remains two commits ahead of remote and is not active in production; see Master Control checkpoint 0b18.

Production recheck (2026-09-24 12:11 Europe/Istanbul): scheduled run #356 completed successfully but refreshed only 7/15 strategies (8 skipped; 0 snapshot failures), and the public-page fetch from this inspection client returned 502, so user-visible freshness is unverified. Remote still uses five-minute scheduler/freshness settings; the local four-hour change is not live. See Master Control checkpoint 0b19.

Acquisition recheck (2026-09-24 12:22 Europe/Istanbul): GA4 `last_28d` remains 62 sessions/4 active users/38 engaged sessions; source categories reconcile, with 22 operator/test-tagged, 36 unclassified, and 4 X/t.co sessions. Search Console returned 127 impressions/0 clicks across dates through Sep 21. The latest public Short has 3 lifetime views so far and no matching GA4 `utm_content` session observed yet; it is too new for a performance judgment. GA4 already exposes session `utm_content`; only first-party/PostHog capture awaits the local migration/deployment. See Master Control checkpoint 0b20 and the updated Growth Operating Plan.

Live product-path recheck (2026-09-24 12:25 Europe/Istanbul): `/rankings` loaded but showed 0 matching modeled strategies and no last snapshot timestamp, 18 minutes after successful-but-degraded scheduled run #356 (7/15 refreshed). This confirms that the present five-minute production freshness rule is not being maintained; the local four-hour/six-hour change remains unpublished. No user-visible release or production state was changed. See Master Control checkpoint 0b21.

Latest public recheck at 2026-09-24 03:14 Europe/Istanbul: GitHub scheduled run #353 was green at 02:59, but live `/rankings` still showed 0 matching strategies and no snapshot timestamp. Run completion alone is not public freshness evidence; local UX/attribution fixes remain undeployed.

Run #353 log was subsequently inspected: it was degraded (7/15 refreshed, 8 skipped) with snapshots calculated at 03:00:25 Istanbul; the 03:14 empty page is consistent with the five-minute freshness expiry. Production migration head was `20260921_0011`; local inbound-attribution migration `20260924_0012` is not yet applied.

User-authorized one-off run #354 was dispatched at 03:36 Istanbul and completed successfully in 41 seconds at the workflow level, but was degraded: 7/15 strategies refreshed at 03:37:05 and 8 skipped (4 non-refreshable, 4 partial-refresh-only), with zero snapshot failures. Only the three Farmers World and four Splinterlands strategies received current snapshots. The other eight remain blocked by the documented DFK balance quarantine, missing Storj economics loader, or static DePIN economics. Recovery evidence still reports production migration head `20260921_0011`; no deploy or schema migration occurred. This is not evidence of a durable cadence or full catalog refresh.

Immediate public verification at 03:40 showed the 7 refreshed strategies on `/rankings` and a 2-result homepage sample; the snapshot timestamp was 00:37 UTC and still within the 5-minute freshness window. The best row was 0.23% modeled 30-day ROI, Risk 100/Very High, Confidence 39/Low, and modeled break-even 12,873 days; the other six rows were negative ROI. These results confirm serving, not sustained freshness or product-market fit.

Distribution recheck at 03:18 Europe/Istanbul: local Shorts worker PID 9184 is alive, heartbeat 02:59, daily cap 1/1, but no matching scheduled task was visible; X worker PID 33700 is stopped, automatic scheduling is disabled, and OAuth is expired. No post/upload/task change was performed.

2026-09-08 product hardening pass: public opportunity cards now expose one evidence-backed start/earn cue, ranking cards explain leading risk contributors, stale top results use neutral recorded-model language, catalog counts distinguish modeled strategies from guide-only opportunities, and public metadata canonicalizes to `https://gamcryp.com`. API summaries now carry catalog guidance so server-rendered and browser-rendered pages stay aligned. Distribution supports local X manual-ready mode. Shorts now require category-specific hooks, approved real product visuals, approved ElevenLabs narration, meaningful scene metadata, GamCryp evaluation placement, and post-render frame QA; music-only/silent fallback is blocked. Existing unpublished queue items remain blocked until re-rendered under this contract.

Explicit user-directed exception (2026-09-24): local policy `user-directed-gamcryp-youtube-explainers-v2` allows one public Short per Istanbul local day using original GamCryp music without TTS, but only for its allowlisted educational/site-explainer and active catalog-guide families, with automated creative/render QA and checksum enforcement. This exception does not authorize promotional/financial content outside that family list and does not change the daily cap. The 2026-09-24 `HOW_TO_USE_GAMCRYP` upload was verified to match this narrow mandate. See Master Control checkpoints 0aa–0ac.

## Gate board

| Gate | Name | Status |
|---|---|---|
| G0 | Freeze | COMPLETE |
| G1 | Skeleton | COMPLETE |
| G2 | Market Data | COMPLETE |
| G3 | ROI Core | COMPLETE |
| G4 | Adapter #1 | COMPLETE |
| G5 | Adapter #2 | COMPLETE |
| G6 | Adapter #3 | COMPLETE |
| G7 | Interface Freeze | COMPLETE |
| G8 | History | COMPLETE |
| G9 | Risk / Confidence | COMPLETE |
| G10 | API | COMPLETE |
| G11 | Web MVP | COMPLETE |
| G12 | Validation | COMPLETE |
| G13 | Production | COMPLETE |
| G14 | Scale / Opportunity + Referral Foundation | COMPLETE |
| G15 | Monetization | COMPLETE |
| G16 | Search / AI Discoverability + Traffic Acquisition | COMPLETE |
| G17 | Referral Operations + Operator Console | COMPLETE |
| G18 | V1 Completion + Coverage Expansion | COMPLETE |

## G0 objective

Transform the conversation/product idea into durable authoritative repository context so future work does not depend on chat memory.

## G0 deliverables

- [x] `AGENTS.md`
- [x] `docs/MASTER_SPEC.md`
- [x] `docs/ARCHITECTURE.md`
- [x] `docs/ROI_METHODOLOGY.md`
- [x] `docs/DATA_CONTRACT.md`
- [x] `docs/STATUS.md`
- [x] User/Codex review confirms no critical contradiction
- [x] Git repository created
- [x] Baseline commit/tag created

## G0 acceptance criteria

G0 may be marked COMPLETE only when:
1. the six authoritative files exist in the local project repo,
2. user accepts the baseline scope,
3. no unresolved critical product/architecture contradiction remains,
4. repository is initialized in Git,
5. baseline is committed,
6. `STATUS.md` is updated to `G0 COMPLETE` and `G1 ACTIVE`.

## G1 objective

Create a reproducible local development skeleton with no game-specific business logic.

## G1 acceptance criteria

- [x] reproducible Python environment,
- [x] backend package imports cleanly,
- [x] PostgreSQL-compatible persistence setup,
- [x] migrations initialized,
- [x] deterministic test runner works,
- [x] `.env.example`,
- [x] no secrets committed,
- [x] `doctor` command exists and validates minimum environment,
- [x] CI/local quality commands documented,
- [x] one command starts required local development services or clearly documented minimal commands do,
- [x] all G1 tests/doctor checks green,
- [x] baseline Git commit for G1.

## G2 objective

Establish shared market-data source infrastructure without game-specific adapter logic.

## G2 acceptance criteria

- [x] provider-neutral market-data contracts live in `sources/`, not `adapters`,
- [x] normalized `Observation` objects preserve Data Contract fields, decimal-safe values, UTC timestamps, source provenance, and freshness/status,
- [x] source HTTP helper enforces configured timeouts, bounded retries, and structured errors,
- [x] at least one market-data provider connector parses recorded fixtures deterministically behind the provider-neutral interface,
- [x] PostgreSQL-compatible persistence for raw observations exists with an Alembic migration,
- [x] doctor/import checks include market-source configuration and package health without requiring live provider calls,
- [x] deterministic tests cover source parsing, missing/stale handling, HTTP errors/retries, persistence, and doctor behavior,
- [x] G2 documentation explains local commands, provider configuration, dependency choices, and scope boundaries,
- [x] no game adapter logic, ROI formulas, strategy calculations, frontend business logic, live integration tests, or provider secrets are added,
- [x] all tests, doctor checks, dependency checks, compile checks, and whitespace checks pass,
- [x] baseline Git commit for G2.

## G3 objective

Implement the generic ROI calculation core using manually verified deterministic scenarios, without live game adapters.

## G3 planned acceptance criteria

- [x] generic ROI engine lives in `engine/` and contains no game-specific checks,
- [x] money and ratio calculations are deterministic and Decimal-safe with explicit currencies,
- [x] engine input contract distinguishes sunk cost, recoverable entry cost, current recoverable value, initial operating reserve, capital at risk, rewards, recurring costs, transaction costs, and other costs,
- [x] engine calculates total capital, recoverable capital, capital at risk, gross nominal earnings, realizable earnings, operating/transaction/other costs, net earnings, break-even, 7D/30D/90D ROI on total capital, 7D/30D/90D ROI on capital at risk, and exit-adjusted P&L,
- [x] break-even basis is explicit and supports total capital, sunk cost, and capital-at-risk recovery targets,
- [x] required missing inputs fail explicitly and are never treated as zero,
- [x] deterministic manually-verifiable fixtures cover simple reward, transaction fee, recurring cost, slippage/executable quote, recoverable entry asset, break-even, exit-adjusted P&L, zero/negative earnings behavior, and missing input failure behavior,
- [x] G3 documentation explains engine scope, formulas implemented, and boundaries,
- [x] no game adapter logic, market provider changes, risk/confidence scoring, optimization, frontend business logic, or live integration tests are added,
- [x] all tests, doctor checks, dependency checks, compile checks, and whitespace checks pass,
- [x] baseline Git commit for G3.

## G4 objective

Implement the first game adapter only after a Data Feasibility Check passes for the selected game.

## G4 acceptance criteria

- [x] Data Feasibility Candidate Scan evaluates at least five currently active GameFi games with materially measurable earning economies,
- [x] selected Adapter #1 candidate has a documented `GO` decision with evidence and unresolved assumptions,
- [x] parked mRON candidate is not implemented or forced into the architecture,
- [x] adapter implements exactly one versioned strategy definition for Adapter #1,
- [x] provider access and HTTP/RPC behavior live in shared `sources/` connectors, not in the game adapter,
- [x] adapter maps game-specific economics into the generic G3 ROI engine without game-specific ROI-core branches,
- [x] adapter preserves LIVE / DERIVED / CONFIG classification for live observations, derived values, and configured assumptions,
- [x] required missing or stale inputs fail explicitly and are never substituted with zero,
- [x] deterministic golden fixture contains manually verified expected ROI values independent of live APIs,
- [x] live integration/probe path exists separately from deterministic tests,
- [x] G4 documentation explains feasibility result, modeled strategy, source boundaries, commands, and dependency choices,
- [x] no optimization, risk/confidence scoring, history, frontend, G5 work, or unrelated game adapter is added,
- [x] all tests, doctor checks, dependency checks, compile checks, and live probe pass,
- [x] baseline Git commit for G4.

## G4 adapter decision

Adapter #1 is `dfk-crystalvale-jeweler-cjewel-max-lock` version `v1`.

See `docs/DECISIONS/0001-adapter-1-feasibility-scan.md`.

## G5 objective

Implement a second game adapter for a materially different economy from DeFi Kingdoms Jeweler, focused on resource production, resource inputs/outputs, conversion/crafting economics, player-market realizable value, operating/transaction costs, entry capital, and exit value.

## G5 acceptance criteria

- [x] Data Feasibility Candidate Scan evaluates at least five active resource-production/crafting/conversion/player-market games,
- [x] Craft World is included in the scan and is not forced when required production/crafting data is not reliably machine-readable,
- [x] selected Adapter #2 candidate has a documented `GO` decision with evidence and unresolved assumptions,
- [x] Adapter #2 represents a materially different economy from DFK Jeweler,
- [x] adapter implements exactly one versioned strategy definition for Adapter #2,
- [x] provider access and HTTP behavior live in shared `sources/` connectors, not in the game adapter,
- [x] adapter maps game-specific economics into the generic G3 ROI engine without game-specific ROI-core branches,
- [x] any new capability is generic and outside the ROI core unless a documented architectural gap requires stopping,
- [x] adapter preserves LIVE / DERIVED / CONFIG classification for live observations, derived values, and configured assumptions,
- [x] required missing or stale inputs fail explicitly and are never substituted with zero,
- [x] deterministic golden fixture contains manually verified expected ROI values independent of live APIs,
- [x] live integration/probe path exists separately from deterministic tests,
- [x] G5 documentation explains feasibility result, modeled strategy, source boundaries, commands, dependency choices, and assumptions,
- [x] no optimization, risk/confidence scoring, history, frontend, G6 work, or unrelated game adapter is added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and live probe pass,
- [x] baseline Git commit for G5.

## G5 adapter decision

Adapter #2 is `farmers-world-axe-wood-production` version `v1`.

See `docs/DECISIONS/0002-adapter-2-feasibility-scan.md`.

## G6 objective

Implement a third game adapter for a materially different economy from DeFi Kingdoms Jeweler and Farmers World, focused on seasonal, probabilistic, performance-dependent, leaderboard, combat, quest, or similar reward economics.

## G6 acceptance criteria

- [x] Data Feasibility Candidate Scan evaluates at least five active GameFi candidates in the target economy class,
- [x] selected Adapter #3 candidate has a documented `GO` decision with evidence and unresolved assumptions,
- [x] Adapter #3 represents a materially different economy from DFK Jeweler and Farmers World,
- [x] adapter implements exactly one versioned strategy definition for Adapter #3,
- [x] provider access and HTTP behavior live in shared `sources/` connectors, not in the game adapter,
- [x] adapter maps uncertainty/time-dependent game economics into the generic G3 ROI engine without game-specific ROI-core branches,
- [x] if rewards are probabilistic or performance-dependent, expected value is used only under explicit assumptions and uncertainty is exposed,
- [x] adapter preserves LIVE / DERIVED / CONFIG classification for live observations, derived values, and configured assumptions,
- [x] required missing or stale inputs fail explicitly and are never substituted with zero,
- [x] deterministic golden fixture contains manually verified expected ROI values independent of live APIs,
- [x] live integration/probe path exists separately from deterministic tests,
- [x] G6 documentation explains feasibility result, modeled strategy, source boundaries, commands, dependency choices, and assumptions,
- [x] no optimization, risk/confidence scoring, history, frontend, G7 work, or unrelated game adapter is added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and live probe pass,
- [x] baseline Git commit for G6.

## G6 adapter decision

Adapter #3 is `splinterlands-modern-ranked-sps-ev` version `v1`.

See `docs/DECISIONS/0003-adapter-3-feasibility-scan.md`.

## Decision backlog (not blockers)

- product/brand name,
- production hosting vendor,
- production market-data subscription/provider,
- final frontend framework,
- monetization pricing,
- legal/commercial launch review.

## G7 objective

Freeze Adapter Contract v1 by reviewing patterns from the first three materially different adapters and documenting the stable adapter/source/strategy boundaries for future gates.

## G7 acceptance criteria

- [x] DFK Jeweler, Farmers World, and Splinterlands adapters are compared for generic inputs, generic outputs, game-specific mechanics, duplicated patterns, and accidental engine assumptions,
- [x] Adapter Contract v1 is defined and supports all three completed adapters without game-name conditionals in the ROI core,
- [x] contract explicitly covers strategy identity/version, capital decomposition, recoverable assets/value, deterministic or expected reward flows, uncertainty ranges, recurring costs, transaction costs, timing assumptions, realizable exit value, required observations, LIVE / CONFIG / DERIVED provenance, and warnings/limitations,
- [x] necessary shared contract/helpers are implemented without aesthetic-only refactors,
- [x] existing golden fixture ROI outputs remain backward-equivalent,
- [x] contract-level tests prove all three adapters conform to Adapter Contract v1,
- [x] `docs/DATA_CONTRACT.md` is updated with frozen Adapter Contract v1 and versioning rules,
- [x] future Adapter #4 process is documented without requiring ROI-core modification,
- [x] no new game adapter, history, risk/confidence, API, frontend, optimization, or new product feature is added,
- [x] all tests, doctor checks, dependency checks, compile checks, and whitespace checks pass,
- [x] baseline Git commit for G7.

## G7 adapter contract decision

Adapter Contract v1 is `adapter-contract-v1`.

The code anchor is `backend/app/adapters/contract.py`. The authoritative documentation is `docs/DATA_CONTRACT.md`.

## G8 objective

Add historical strategy snapshot persistence and retrieval using the frozen Adapter Contract v1 outputs, without changing adapter economics.

## G8 acceptance criteria

- [x] successful `AdapterResultV1` + ROI engine outputs persist as historical strategy snapshots,
- [x] snapshots include strategy id/version, adapter contract version, model/engine version, calculated-at UTC timestamp, intended calculation window, capital metrics, earnings/cost metrics, ROI/break-even/exit-adjusted outputs, uncertainty range metadata, warnings, classification summary, input observation references, and freshness summary,
- [x] historical records preserve enough observations, assumptions, classifications, warnings, versions, timestamps, and Decimal-safe outputs to explain why a result was published at that time,
- [x] PostgreSQL-compatible history schema exists with an Alembic migration,
- [x] repository/query layer retrieves latest snapshot, time-range snapshots, ordered time series, and strategy/model version information,
- [x] scheduled recalculation runner exists for the modular monolith without distributed queues or microservices,
- [x] failed adapter/provider calculations are isolated, logged as failures, and do not create fake numeric snapshots,
- [x] stale or missing required inputs fail explicitly and are not substituted with zero,
- [x] repeated execution for the same strategy/version/model/contract/window is idempotent and does not create duplicate snapshots,
- [x] historical snapshots are retained across strategy/model version changes,
- [x] deterministic tests cover persistence, latest snapshot, ordered history, version changes, provenance, duplicate/idempotency behavior, failure isolation, stale input behavior, and uncertainty metadata,
- [x] local history/scheduler probe runs with the existing adapters,
- [x] no risk/confidence scoring, product API endpoints, frontend, optimization, or new game adapters are added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and the history probe pass,
- [x] baseline Git commit for G8.

## G8 history decision

Historical snapshot idempotency is keyed by `strategy_id`, `strategy_version`, `adapter_contract_version`, `model_version`, `intended_window_start`, and `intended_window_end`.

Successful calculations are stored in `strategy_snapshots`; failures are stored separately in `strategy_calculation_failures` without numeric ROI output.

See `docs/DATA_CONTRACT.md`.

## G9 objective

Implement independent, transparent confidence and risk scoring for historical strategy snapshots.

## G9 acceptance criteria

- [x] confidence and risk are implemented as independent concepts and are not merged into one score,
- [x] confidence scores measure calculation/data trust on a 0-100 scale where higher is more trustworthy,
- [x] risk scores measure economic downside/instability on a 0-100 scale where higher is more risky,
- [x] confidence labels are documented as LOW, MODERATE, and HIGH,
- [x] risk labels are documented as LOW, MEDIUM, HIGH, and VERY HIGH,
- [x] scoring thresholds and weights are documented in `docs/ROI_METHODOLOGY.md`,
- [x] score results are decomposable into factor-level point contributions with evidence and explanations,
- [x] factors without stored evidence are marked unavailable instead of guessed,
- [x] G8 history is used for trend risk only when at least three comparable snapshots exist,
- [x] confidence penalizes CONFIG-heavy strategies separately from engine correctness,
- [x] risk captures supported evidence for lock/exit penalties, thin liquidity/slippage, probabilistic uncertainty, weak yield, recoverable exit loss, and adapter warnings,
- [x] versioned scoring results are persisted in `strategy_snapshot_scores` linked to historical snapshots,
- [x] scoring methodology version is preserved as `risk-confidence-v1`,
- [x] deterministic tests cover high-confidence/low-risk, high-confidence/high-risk, low confidence, stale data, missing optional history, heavy CONFIG dependence, poor liquidity/slippage, lock/exit penalty, probabilistic uncertainty, score explanations/contributions, methodology versioning, and the three existing adapters,
- [x] local scoring probe runs against the existing DFK Jeweler, Farmers World, and Splinterlands adapters,
- [x] no API product endpoints, frontend, optimization, new adapters, portfolio features, or production deployment are added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, history probe, and scoring probe pass,
- [x] baseline Git commit for G9.

## G9 scoring decision

Scoring methodology version is `risk-confidence-v1`.

Scores are stored separately from snapshots in `strategy_snapshot_scores`, uniquely by `snapshot_id` and `methodology_version`.

Current deterministic probe scores:

| Strategy | Confidence | Risk |
|---|---:|---:|
| `dfk-crystalvale-jeweler-cjewel-max-lock` | 82 HIGH | 79 VERY HIGH |
| `farmers-world-axe-wood-production` | 77 MODERATE | 31 MEDIUM |
| `splinterlands-modern-ranked-sps-ev` | 39 LOW | 100 VERY HIGH |

## G10 objective

Expose existing strategy/history/risk-confidence data through a stable read-oriented product API.

## G10 acceptance criteria

- [x] API routes are versioned under `/api/v1`,
- [x] minimum endpoints exist for health, games, game detail, strategies, strategy detail, latest snapshot, history, and rankings,
- [x] rankings support only modeled filters: capital minimum/maximum, confidence minimum, risk maximum, game, chain, and economy type,
- [x] responses include strategy identity/version, game identity, capital, net daily earnings, break-even, ROI metrics, confidence score/label, risk score/label, warnings, freshness/last-calculated data, methodology/model versions, and uncertainty ranges where available,
- [x] Decimal-sensitive financial values are serialized as exact strings and are never converted through binary float internally,
- [x] list and history endpoints include `limit`/`offset` pagination,
- [x] ranking order and tie-break policy are deterministic and documented,
- [x] stale/partial behavior distinguishes unavailable values from zero and does not present failed calculations as valid snapshots,
- [x] response schemas and generated OpenAPI documentation cover the API surface,
- [x] deterministic tests cover normal strategy detail, ranking order, filters, pagination, history ordering, unavailable optional fields, stale data, invalid IDs, validation errors, Decimal serialization, risk/confidence inclusion, and API version path,
- [x] normal API requests read persisted results and do not trigger live provider/blockchain calls,
- [x] local API probe demonstrates stored sample/current strategy outputs,
- [x] authentication remains out of scope for the public read-only MVP,
- [x] no frontend, optimization, new game adapters, portfolio features, production deployment, or monetization features are added,
- [x] all tests, doctor checks, dependency checks, compile checks, whitespace checks, and API probe pass,
- [x] baseline Git commit for G10.

## G10 API decision

API contract version is `api-v1`.

Routes are implemented in `backend/app/api/v1/routes.py`, response schemas in `backend/app/api/v1/schemas.py`, and the read service in `backend/app/api/v1/service.py`.

Normal API requests read persisted `strategy_snapshots` and `strategy_snapshot_scores` records only. They do not call adapters, source providers, blockchain RPCs, or scheduled recalculation jobs.

Ranking tie-break policy:

```text
roi_total_30d desc
confidence_score desc
risk_score asc
calculated_at desc
strategy_id asc
```

JSON financial serialization uses exact decimal strings. Unavailable optional values are `null` with explicit status/reason metadata, and unavailable risk/confidence scores return `available=false`.

## G11 objective

Build the minimal public web interface for the existing read-only API.

## G11 acceptance criteria

- [x] frontend consumes `/api/v1` only and does not duplicate ROI/risk/confidence business logic,
- [x] minimum pages exist for Home / ROI Finder, Rankings, Game Detail, Strategy Detail, and Methodology,
- [x] ROI Finder supports API-modeled filters for capital budget, maximum risk, minimum confidence, game, and economy type,
- [x] Rankings show game, strategy, capital, net/day, 30D ROI, break-even, confidence score/label, risk score/label, last calculated/freshness, and warnings indicator,
- [x] Strategy Detail shows exact strategy/version, capital breakdown, gross/realizable/net earnings, costs, break-even, ROI metrics, exit-adjusted P&L, uncertainty ranges where present, confidence/risk contributors, LIVE / CONFIG / DERIVED explanation, warnings, freshness, and methodology/model versions,
- [x] History view shows an ordered table where at least two snapshots exist and an explicit insufficient-history state otherwise,
- [x] Methodology page explains strategy-specific ROI, realizable earnings, slippage, total vs at-risk capital, confidence vs risk, LIVE / CONFIG / DERIVED, and no guaranteed returns,
- [x] UX is responsive, fast-loading, typography-forward, restrained, and trust/data clarity oriented,
- [x] stale and low-confidence states are visibly called out,
- [x] frontend treats Decimal-sensitive API values as exact strings and does not introduce binary-float financial calculations,
- [x] error/loading/empty states cover API unavailable, no matching rankings, strategy not found, stale data, missing optional fields, and insufficient history,
- [x] frontend tests cover rankings rendering, filters/query behavior, strategy detail, risk/confidence display, unavailable/null handling, stale warnings, error state, and history/no-history state,
- [x] local backend + frontend workflow and web smoke probe are documented,
- [x] no production deployment, auth, portfolio, alerts, monetization, optimization, new adapters, AI chat, native mobile work, or branding/domain optimization is added,
- [x] all backend tests, frontend tests, doctor checks, dependency checks, compile checks, whitespace checks, API probe, and web probe pass,
- [x] baseline Git commit for G11.

## G11 web decision

Frontend stack is dependency-free static HTML/CSS/JavaScript served by the FastAPI modular monolith.

Routes:

```text
/
/rankings
/games/{game_id}
/strategies/{strategy_id}
/methodology
```

The frontend route shell is `frontend/index.html`; browser logic is `frontend/assets/app.js`; styling is `frontend/assets/styles.css`; serving lives in `backend/app/web/routes.py`.

The web client only calls `/api/v1`. It renders API-provided strings and metadata, including the classification summary added to snapshot payloads for LIVE / CONFIG / DERIVED display.

## G12 objective

Validate the entire MVP end-to-end against source data and independently reproducible calculations before production work begins.

## G12 acceptance criteria

- [x] DFK Jeweler, Farmers World, and Splinterlands strategies are validated independently,
- [x] entry capital source, reward formula, LIVE inputs, CONFIG assumptions, DERIVED outputs, exit path, slippage treatment, costs, recoverable capital, net/day, break-even, 30D ROI, exit-adjusted P&L, confidence, and risk are reviewed for each strategy,
- [x] each strategy is recomputed with an independent Decimal-safe validation module that does not call the ROI engine implementation,
- [x] source fixture/probe values are compared through adapter inputs, engine outputs, persisted snapshots, API responses, and web display behavior,
- [x] deterministic validation uses exact Decimal equality and live probes are documented as point-in-time freshness/provenance checks,
- [x] weak assumptions for DFK gas/lock behavior, Farmers World zero WAX cost and liquidity, and Splinterlands expected-value assumptions are classified for public beta,
- [x] stale and missing required data behavior is validated and does not produce fake zero-valued ROI,
- [x] risk/confidence explanations are validated against stored evidence,
- [x] history ordering, snapshot versions, provenance references, no-overwrite behavior, and methodology/model version preservation are validated,
- [x] API/web financial display consistency is validated; a G12 web ratio formatting drift was fixed so ROI ratios render exact API strings,
- [x] adversarial edge cases cover zero liquidity, extreme slippage, token price collapse, missing entry price, stale provider data, negative net earnings, zero/negative denominator, recoverable value collapse, tiny-capital high ROI, and unavailable optional history,
- [x] validation report is recorded in `docs/VALIDATION_REPORT.md` with per-strategy result, assumption matrix, manual-vs-engine comparison, public-beta blockers, required warnings, limitations, strategy recommendations, and overall recommendation,
- [x] no production deployment, new adapters, monetization, portfolio, alerts, auth, AI, optimization, or major UI redesign is added,
- [x] full pytest suite, frontend tests, doctor, compileall, pip check, API probe, web probe, validation probe, live adapter probes, and `git diff --check` pass,
- [x] baseline Git commit for G12.

## G12 validation decision

Overall recommendation is CONDITIONAL PASS with no public-beta-blocking correctness issues.

G12 found and fixed one correctness issue: the web UI converted API ROI ratio strings into percentages. The web client now renders ratio metrics as exact API strings and regression tests enforce that the frontend does not parse or recompute financial metrics.

Validation artifacts:

- Independent validation module: `backend/app/validation/e2e.py`
- Validation tests: `backend/tests/test_g12_validation.py`
- Validation report: `docs/VALIDATION_REPORT.md`

Per-strategy validation status:

| Strategy | G12 result |
|---|---|
| DFK Jeweler | CONDITIONAL PASS |
| Farmers World | CONDITIONAL PASS |
| Splinterlands | CONDITIONAL PASS |

Conditional status means the calculations are reproducible and product surfaces are consistent, while public beta must continue to show assumptions, warnings, freshness, confidence/risk explanations, and LIVE / CONFIG / DERIVED classifications.

## G13 objective

Deploy the validated MVP as a reliable public beta with production PostgreSQL, scheduled recalculation, monitoring, backups, HTTPS, and production-safe external provider configuration.

## G13 acceptance criteria

- [x] short production-platform decision review compares Render and Railway using current official documentation,
- [x] simplest managed production architecture is selected and documented,
- [x] repository contains reproducible deployment configuration without committed secrets,
- [x] production settings reject SQLite and unsafe provider defaults,
- [x] production database connection uses PostgreSQL with conservative SQLAlchemy pooling,
- [x] Alembic migration command is configured for production deploys,
- [x] scheduled recalculation command exists for live adapter snapshots and persisted risk/confidence scoring,
- [x] scheduler preserves G8 idempotency and failure isolation,
- [x] provider source calls retain bounded retries and provider-failure logging,
- [x] production freshness thresholds and hard-stale policy are documented,
- [x] HTTP security headers and safe CORS policy are configured,
- [x] operations status endpoint exposes database, scheduler, stale-strategy, provider-failure, and calculation-failure status without live provider calls,
- [x] production runbook documents architecture, provider configuration, environment variables, deploy, migrations, scheduler, backups/restore, monitoring, incident recovery, rollback, and secret rotation,
- [x] production PostgreSQL database exists on the selected platform,
- [x] all Alembic migrations have run against production/staging PostgreSQL,
- [x] production provider secrets are configured through platform secret management,
- [x] HTTPS public web/API URL is reachable outside the local machine,
- [x] scheduled recalculation has run in production and created a new valid snapshot,
- [x] history retains an older production snapshot after the scheduler run,
- [x] public-beta database limitation is explicitly accepted: Free Render Postgres expires, has no production-grade backup/PITR, and requires paid upgrade for backup/restore-grade production,
- [x] production validation verifies `/api/v1/health`, rankings, all five web pages, all three strategies, risk/confidence display, stale/warning behavior, API/web exact-value consistency, scheduler behavior, history retention, and provider-failure isolation,
- [x] local pre-deploy verification passes after final production changes: pytest, frontend tests, G12 validation, doctor, compileall, pip check, API probe, web probe, and `git diff --check`,
- [x] baseline Git commit for G13.

## G13 production decision

Selected platform: Render.

Decision record: `docs/DECISIONS/0004-production-platform.md`.

Runbook: `docs/PRODUCTION_RUNBOOK.md`.

Low-cost beta deployment configuration:

- default Blueprint `render.yaml` uses Free Web Service and Free Render Postgres where supported,
- paid production upgrade Blueprint `render.production.yaml` preserves paid web + paid Postgres + Render Cron,
- beta scheduled recalculation uses GitHub Actions workflow `.github/workflows/render-beta-recalculation.yml`,
- Free Render Postgres expires after 30 days and has no Render-managed backups/PITR/logical backups,
- Free Web Service may cold start after inactivity.

Final public-beta production validation status:

- public beta URL is reachable at `https://gamefi-roi-web.onrender.com`,
- GitHub Actions beta recalculation reaches Render Postgres and has completed consecutive successful runs,
- DFK Jeweler, Farmers World, and Splinterlands all have valid fresh latest production snapshots and appear in `/api/v1/rankings`,
- immediate duplicate-window recalculation did not create duplicate snapshots for the same intended window,
- Farmers World and Splinterlands retain multiple historical snapshots across different calculation windows,
- public `/api/v1/ops/status` reports database health, scheduler last-success state, all three latest strategy snapshots, and zero stale strategies,
- historical provider failures remain visible as old failure counts, but they are not blocking current publication because all current latest snapshots are fresh,
- public web routes and API responses are reachable over HTTPS, and the deployed web renderer displays exact API Decimal strings without frontend financial recomputation,
- Free Render Postgres expiry/no-backup/no-PITR and Free Web Service cold starts are accepted public-beta limitations; `render.production.yaml` remains the paid upgrade path for production-grade backups, Render Cron, and always-on behavior.

## Post-G13 UI/UX backlog

Do not implement these during G13. Record them for the first appropriate post-production UI gate:

- human-readable money formatting,
- human-readable ROI percentage formatting,
- ranking cards instead of the current wide raw table,
- responsive layout cleanup,
- game/opportunity logos,
- clearer risk/confidence presentation,
- Play/Start CTA integration with the upcoming referral foundation.

## G14 objective

Scale the public beta foundation after G13 production is complete by expanding the current Game catalog into a backward-compatible Opportunity model and adding the first referral/outbound foundation without implementing affiliate attribution/reporting or sponsored placements.

G14 is not merely "add more games." It must make the model capable of representing:

- `GAME` opportunities,
- `DEPIN_NODE` opportunities,
- `POINTS` opportunities.

Existing GameFi adapters, strategy ids, strategy versions, historical snapshots, API behavior, and web routes must remain backward compatible.

The first non-game feasibility candidates are Grass, Teneo, and ARO. These candidates are not approved ROI adapters by default; they must pass the expanded Data Feasibility Check before any financial ROI is published.

G14 must include:

- a documented backward-compatible feasibility plan for expanding `Game` to canonical `Opportunity`,
- canonical opportunity identity fields and opportunity type rules,
- compatibility behavior for existing `game_id` fields and `/api/v1/games`,
- structured opportunity/game/strategy outbound destination metadata,
- structured referral/affiliate metadata where a destination has a commercial relationship,
- a first-party `/go/...` redirect layer for outbound opportunity/game links,
- explicit user-facing disclosure metadata for affiliate/referral links,
- redirect safety controls that prevent open redirects and unreviewed destinations,
- tests proving outbound/referral metadata never affects ROI, Risk, Confidence, or organic rankings.

G14 must not implement G15 monetization analytics, sponsored placement inventory, paid ranking, portfolio features, auth, alerts, optimization, or new game/opportunity adapters unless separately scoped.

G14 must not assign financial value to points-only opportunities unless a lawful, reproducible, realizable value route exists. Points-only outputs must show ROI unavailable rather than zero.

## G14 acceptance criteria

- [x] `Game` to `Opportunity` backward-compatibility feasibility is documented and approved before code changes,
- [x] canonical `Opportunity` model supports `GAME`, `DEPIN_NODE`, and `POINTS`,
- [x] existing DeFi Kingdoms, Farmers World, and Splinterlands adapter outputs remain backward-equivalent,
- [x] existing `game_id` values and `/api/v1/games` behavior remain compatible for current clients,
- [x] new opportunity metadata does not require ROI core changes or game/opportunity type branches in the ROI engine,
- [x] Grass, Teneo, and ARO have recorded candidate feasibility notes before any adapter work,
- [x] outbound destination metadata exists for modeled opportunities/games/strategies with stable ids/slugs, destination type, target URL, status, ownership/commercial relationship, disclosure text, source/provenance, review timestamp, and allowed use,
- [x] referral/affiliate metadata is structured separately from ROI/risk/confidence model inputs,
- [x] first-party `/go/{destination_slug}` redirect route resolves only allowlisted active destinations,
- [x] redirect route fails closed for missing, disabled, malformed, or unreviewed destinations,
- [x] web/API can expose outbound destination metadata needed for links and disclosure without exposing secrets,
- [x] affiliate/referral status is clearly disclosed where links are shown,
- [x] tests prove affiliate/sponsor/referral metadata cannot change ROI, Risk, Confidence, history snapshots, or organic ranking order,
- [x] no affiliate attribution/reporting, sponsored placement ranking, commercial analytics, or paid promotion surfaces are implemented,
- [x] documentation explains how future commercial relationships are represented without contaminating economic calculations,
- [x] documentation explains that native referral/points rewards are separate from GameFi ROI commercial referral metadata,
- [x] all required tests, doctor checks, probes, and whitespace checks pass,
- [x] baseline Git commit for G14.

## G14 opportunity/referral decision

G14 adds a canonical static `Opportunity` catalog and keeps the existing `Game` catalog as a GAME-only compatibility view.

Implemented opportunity types:

- `GAME`,
- `DEPIN_NODE`,
- `POINTS`.

Initial 10 opportunity records:

| Opportunity | Type | Feasibility | Financial ROI |
|---|---|---|---|
| DeFi Kingdoms | `GAME` | `GO` | available through existing DFK Jeweler strategy |
| Farmers World | `GAME` | `GO` | available through existing Axe Wood Production strategy |
| Splinterlands | `GAME` | `GO` | available through existing Modern Ranked SPS EV strategy |
| Grass | `DEPIN_NODE` | `PARTIAL` | unavailable; points/value route not reproducible |
| Teneo | `DEPIN_NODE` | `PARTIAL` | unavailable; beta points/account data not reproducible |
| ARO Network | `DEPIN_NODE` | `PARTIAL` | unavailable; Jade/future-drop value not reproducible |
| Nodepay | `POINTS` | `PARTIAL` | unavailable; conversion/share data not reproducible |
| DAWN | `DEPIN_NODE` | `REJECTED` for financial ROI | unavailable; terms state no monetary value |
| BlockMesh | `DEPIN_NODE` | `PARTIAL` | unavailable; token eligibility/value not reproducible |
| Bless Network | `DEPIN_NODE` | `PARTIAL` | unavailable; reward/value data not reproducible |

API additions:

```text
GET /api/v1/opportunities
GET /api/v1/opportunities/{opportunity_id}
```

Web additions:

```text
/opportunities
/opportunities/{opportunity_id}
/go/{destination_slug}
```

The UI now formats money, ROI percentages, and break-even values for readability while preserving exact API Decimal strings as source values. The frontend still does not recalculate ROI, Risk, Confidence, or rankings.

Post-deployment UI acceptance fix:

- Home/ROI Finder and Rankings use responsive strategy cards instead of a wide ranking table.
- Cards show game/opportunity, strategy, capital, net/day, 30D ROI, break-even, confidence, risk, freshness/last updated, warnings, View Strategy, and Start/Play CTA when available.
- Display formatting handles long Decimal strings, scientific notation, tiny positive/negative currency values, positive/negative ROI percentages, and large break-even day counts.
- Strategy cards show interpretation badges such as positive return, negative return, low-confidence warning, very-high-risk warning, stale-data warning, and ROI unavailable.
- Opportunity cards use the same visual system for `GAME`, `DEPIN_NODE`, and `POINTS`; non-financial candidates expose ROI as unavailable, reward type, opportunity type, Start/Open CTA, and the reason financial ROI is unavailable.
- Strategy detail keeps API values authoritative but formats capital, earnings, ROI, break-even, history rows, confidence/risk, LIVE/CONFIG/DERIVED, warnings, and freshness for human scanning.
- Frontend regression tests cover exact API value retention, human-readable formatting, negative ROI, tiny values, unavailable ROI, long strategy names, no table-based ranking markup, responsive card structure, risk/confidence labels, and CTA behavior.

Post-deployment GamCryp brand/UI refinement:

- Header uses the GamCryp text lockup with "Web3 Opportunity Intelligence" as the product descriptor.
- The official logo asset is stored at `frontend/assets/brand/gamcryp-logo.png` and is loaded directly in the header without redrawing, cropping, or modifying the source image.
- The warm beige visual system was replaced with a deep navy/midnight base, dark elevated cards, restrained cyan/electric-blue/violet accents, and subtle ambient/grid texture.
- The ranking card structure, opportunity watchlist, Start/Open CTAs, risk/confidence labels, and unavailable ROI states remain the same product surfaces with updated brand styling only.
- Affiliate/sponsor/referral metadata remains excluded from ROI, Risk, Confidence, history snapshots, validation, and organic ranking order.

Outbound/referral metadata is implemented as reviewed product metadata. Current destinations use official URL fallback and have no configured affiliate relationship. `/go/{destination_slug}` accepts no arbitrary target parameter, redirects only active verified destinations, and logs only a minimal aggregate event without cookies or per-user attribution.

Affiliate/sponsor/referral metadata is excluded from ROI inputs, risk/confidence scoring, historical snapshots, validation, and organic ranking order. G15 is the first gate where attribution/reporting, sponsored placements, and commercial analytics may be implemented.

Public beta note: `https://gamefi-roi-web.onrender.com/api/v1/health` was reachable and healthy during G14 verification. Because `render.yaml` keeps `autoDeployTrigger: off`, the current public deployment will not serve the new G14 routes until the G14 commit is manually deployed on Render.

## G15 objective

Implement monetization features on top of the G14 referral foundation while preserving product integrity.

G15 may include:

- affiliate attribution and reporting,
- outbound/referral click and conversion reporting where lawfully sourceable,
- sponsored placement inventory and rendering,
- commercial analytics for partner performance,
- disclosure and audit tooling for monetized surfaces.

Affiliate/sponsor relationships must never affect ROI, Risk, Confidence, strategy snapshots, validation results, or organic rankings. Sponsored placements must be separate, explicitly labeled surfaces with deterministic separation from organic results.

## G15 acceptance criteria

- [x] affiliate attribution/reporting is implemented only from `/go/...` outbound events and approved partner data,
- [x] commercial analytics are stored separately from strategy snapshots, ROI outputs, risk/confidence scores, and organic ranking inputs,
- [x] sponsored placement data model exists with explicit labeling, campaign status, placement surface, disclosure text, and audit trail,
- [x] sponsored placements cannot alter organic ranking order or analytical metrics,
- [x] API/web responses distinguish organic ranking results from sponsored placements,
- [x] tests prove changing affiliate/sponsor/commercial metadata does not change ROI, Risk, Confidence, or organic rankings,
- [x] legal/compliance review requirements for disclosures, tracking, and partner data usage are documented before public monetized launch,
- [x] reporting clearly separates clicks, conversions, revenue, and partner campaign metrics from user-facing economic strategy metrics,
- [x] all required tests, doctor checks, probes, and whitespace checks pass,
- [x] baseline Git commit for G15.

## G15 monetization implementation notes

G15 adds:

- `outbound_click_events` for privacy-minimal first-party redirect click events,
- `referral_programs` for lifecycle status and verification metadata,
- `revenue_attributions` for verified/manual partner import foundations,
- `sponsored_placements` for labeled commercial placement metadata,
- commercial metrics where CTR, EPC, revenue, and conversion rate are unavailable unless their denominators and verified inputs exist,
- API response separation where organic `/api/v1/rankings.items` remains analytical and sponsored placements are exposed separately in `sponsored_placements`,
- public disclosure copy and conversion-focused UI refinements.

Referral lifecycle statuses are `NONE`, `DISCOVERED`, `APPLICATION_REQUIRED`, `PENDING`, `VERIFIED`, `ACTIVE`, `PAUSED`, `REJECTED`, and `EXPIRED`.

Affiliate/sponsor relationships must never affect ROI, Risk, Confidence, historical snapshots, validation, or organic rankings.

## G16 objective

Increase discoverability and acquisition for the public beta without changing analytical outputs.

G16 may include:

- search-engine metadata and content structure,
- AI/search discoverability improvements,
- shareable opportunity/strategy pages,
- traffic acquisition measurement that respects the G15 privacy and integrity boundary.

G16 must not change ROI calculations, adapters, risk/confidence methodology, organic ranking logic, or monetization attribution logic unless a backward-compatible bug fix is explicitly required.

## G16 acceptance criteria

- [x] canonical public pages render meaningful server-visible HTML before JavaScript enhancement,
- [x] canonical URL generation uses `GAMEFI_PUBLIC_BASE_URL` and does not hard-code Render in SEO logic,
- [x] public pages include page-specific title, meta description, canonical URL, robots directive, Open Graph, Twitter metadata, and truthful JSON-LD,
- [x] JSON-LD is limited to appropriate `Organization`, `WebSite`, `WebPage`, and `BreadcrumbList` schema types,
- [x] `/sitemap.xml` includes absolute canonical public URLs only and excludes `/api`, `/go`, assets, query permutations, and internal/debug/test routes,
- [x] `/robots.txt` allows public content, disallows `/api`, `/go`, query traps, and internal/debug/test routes, and does not block Googlebot, Bingbot, OAI-SearchBot, or PerplexityBot,
- [x] `/go/{destination_slug}` redirects remain first-party outbound redirects with noindex/nofollow behavior and do not become search landing pages,
- [x] query-string ranking/filter pages render `noindex,follow`; only curated landing pages are indexable,
- [x] IndexNow support is operator-triggered, validates canonical host/path eligibility, exposes the key verification file only when configured, uses timeouts/retries, and redacts keys from errors,
- [x] inbound acquisition attribution stores only privacy-minimal landing/referrer/UTM/channel/coarse-session metadata,
- [x] inbound acquisition, referral, affiliate, sponsor, and commercial data cannot affect ROI, Risk, Confidence, historical snapshots, or organic ranking order,
- [x] docs include search discovery runbook, operator checklist, data contract, architecture notes, and an accepted search/AI policy decision,
- [x] deterministic tests cover crawlable HTML, metadata, canonicals, robots, sitemap XML, JSON-LD parseability, links, noindex behavior, unavailable ROI, IndexNow validation/failure isolation, inbound attribution, and ranking integrity,
- [x] backend tests, frontend tests, doctor, compileall, pip check, API probe, web probe, and `git diff --check` pass,
- [x] baseline Git commit for G16.

## G16 search/discovery implementation notes

G16 adds:

- `app.web.seo` for server-rendered public pages and metadata,
- `app.search.canonical` for canonical inventory and curated landing-page definitions,
- `app.search.indexnow` and `app.search.indexnow_cli` for manual IndexNow submission,
- `/robots.txt`, `/sitemap.xml`, and optional `/{GAMEFI_INDEXNOW_KEY}.txt`,
- `inbound_landing_events` storage and migration for privacy-minimal acquisition attribution,
- `docs/SEARCH_DISCOVERY_RUNBOOK.md`,
- `docs/SEARCH_DISCOVERY_OPERATOR_CHECKLIST.md`,
- `docs/DECISIONS/0007-search-ai-discoverability-policy.md`.

G16 does not start monetization expansion beyond G15, new adapters, optimization, portfolio features, auth, alerts, AI chat, or production deployment changes.

## G17 objective

Build the operator workflow required to manage referral/affiliate coverage across the existing Opportunity catalog without contaminating analytical outputs.

G17 adds:

- explicit referral coverage states,
- a protected single-operator console,
- safe referral/outbound metadata editing,
- referral work queue tasks,
- metadata-only referral health checks,
- manual verified revenue/conversion entry,
- runbook coverage for day-to-day referral operations.

G17 must not change ROI calculations, adapter economics, risk/confidence scoring, historical strategy snapshots, organic ranking order, search/discovery attribution, public sponsored placement rules, portfolio features, auth for public users, AI, optimization, or new opportunity adapters.

## G17 acceptance criteria

- [x] coverage states exist for `REFERRAL_ACTIVE`, `REFERRAL_PENDING`, `REFERRAL_MISSING`, `REFERRAL_RESEARCH_REQUIRED`, `NO_PROGRAM_FOUND`, `REFERRAL_EXPIRED`, `REFERRAL_PAUSED`, and `REFERRAL_REVERIFY`,
- [x] referral lifecycle metadata supports official URL, referral URL, referral code/template, program name/type, commission/reward description, eligibility, geographic restrictions, status, evidence URL/reference, applied/verified/last-checked/expires timestamps, and operator notes,
- [x] referral URLs are validated for HTTPS, reviewed host/domain relationship, and unsafe schemes/private/local destinations before they can become active,
- [x] `/go/{destination_slug}` uses the reviewed active referral URL when valid and falls back to the official URL when the referral URL is missing, invalid, paused, expired, or unverified,
- [x] referral operations never create arbitrary open redirects and `/go` still fails closed for unknown destinations,
- [x] task queue types exist for `FIND_REFERRAL_PROGRAM`, `APPLY_TO_PROGRAM`, `VERIFY_REFERRAL_LINK`, `RECHECK_PENDING_APPLICATION`, `REVERIFY_PROGRAM`, and `REPLACE_EXPIRED_LINK`,
- [x] referral health checks create/update open tasks without duplicates and are based only on stored metadata,
- [x] a protected operator console exists for referral coverage, work queue review, safe metadata editing, health checks, and manual verified revenue entry,
- [x] operator auth is configured only through environment secrets, has no default password, and returns fail-closed when credentials are absent,
- [x] operator pages are noindex/nofollow, omitted from sitemap, disallowed by robots, and excluded from public OpenAPI schemas,
- [x] manual revenue attribution remains partner/operator-entered; pending/unverified revenue is retained but never counted as verified revenue,
- [x] affiliate/referral/sponsor/revenue data cannot affect ROI, Risk, Confidence, strategy snapshots, validation outputs, or organic ranking order,
- [x] database schema and Alembic migration exist for the referral operations fields and task queue,
- [x] documentation explains referral operations, environment variables, alert/workflow handling, and commercial integrity boundaries,
- [x] backend tests, frontend tests, doctor, compileall, pip check, probes, and `git diff --check` pass,
- [x] baseline Git commit for G17.

## G17 referral operations implementation notes

G17 adds:

- `app.monetization.referral_operations` for coverage state calculation, safety validation, work queue task generation, `/go` referral overlay helpers, and manual revenue validation,
- `app.operator.routes` for the Basic Auth protected single-operator HTML console,
- migration `20260823_0007_referral_operations` for expanded `referral_programs`, expanded `revenue_attributions`, and new `referral_tasks`,
- operator environment variables `GAMEFI_OPERATOR_USERNAME`, `GAMEFI_OPERATOR_PASSWORD`, `GAMEFI_REFERRAL_REVERIFY_DAYS`, and `GAMEFI_REFERRAL_PENDING_RECHECK_DAYS`,
- `docs/REFERRAL_OPERATIONS_RUNBOOK.md`.

Operator console routes:

```text
/operator/referrals
/operator/referrals/{opportunity_id}
/operator/referrals/health
/operator/revenue
```

Commercial integrity remains unchanged: referral relationships, verified revenue, click metrics, sponsor data, and operator task status never feed ROI, Risk, Confidence, snapshots, validation, or organic rankings. G18 is complete and the project is in V1 operations/growth mode.

## G18 objective

Move GamCryp from feature-complete public beta to operational V1 with sufficient opportunity coverage, modeled strategy coverage, referral operations readiness, production checks, and final UX/QA.

G18 must not start V2 work, customer subscriptions/billing, major architectural rewrites, or paid-feature expansion. Future work after G18 should be classified as Operations, Growth, V1.x improvement, or V2 proposal.

## G18 acceptance criteria

- [x] at least 25 high-quality published opportunities exist across `GAME`, `DEPIN_NODE`, and `POINTS`,
- [x] at least 10 modeled strategies have reproducible financial calculations and retain backward-compatible behavior for DFK, Farmers World, and Splinterlands,
- [x] every published opportunity has canonical identity, opportunity type, official destination, publication status, reward type, feasibility result, referral coverage state, evidence/source metadata, and a search/index page,
- [x] every modeled strategy has adapter contract compliance, golden fixture coverage, live probe support, ROI, Risk, Confidence, snapshot/history, API integration, public web integration, and an indexable detail page,
- [x] opportunities without lawful/reproducible valuation expose ROI as unavailable, never zero,
- [x] referral absence does not block publication,
- [x] missing referrals are visible in the operator queue and official URL fallback works for every published opportunity,
- [x] referral, sponsor, click, revenue, and operator-task data cannot affect ROI, Risk, Confidence, strategy snapshots, validation, or organic ranking order,
- [x] public web is readable, responsive, GamCryp-branded, and does not expose backend-looking raw financial values,
- [x] search/AI crawl and index foundations cover the expanded catalog while `/go`, API, operator, internal, and query-trap routes remain excluded as intended,
- [x] production scheduled recalculation is stable and all modeled strategies have valid latest-state handling or explicit documented provider failures,
- [x] operator console is protected and usable for referral coverage, work queue review, metadata maintenance, health checks, and manual verified revenue entry,
- [x] `/go/{destination_slug}` remains fail-closed for unknown destinations and never permits arbitrary open redirects,
- [x] Render Free beta limitations and paid production upgrade path remain explicitly documented,
- [x] `docs/V1_COMPLETION_REPORT.md` exists and includes product summary, architecture summary, opportunity/strategy inventory, referral coverage, search status, production status, limitations, security/privacy notes, operator workflow, manual actions, KPI baseline, and non-V1 scope,
- [x] backend tests, frontend tests, compileall, pip check, doctor, API probe, web probe, operator smoke, search/sitemap/robots checks, scheduled recalculation probe, referral integrity checks, live/public verification where safe, and `git diff --check` pass,
- [x] baseline Git commit for G18.

## G18 implementation notes

G18 expands the catalog to 26 public opportunities and 10 modeled strategies while preserving the analytical integrity boundary. The canonical catalog remains the source for public opportunity identity and outbound destinations; modeled strategies remain strategy-specific and continue to pass the G7 Adapter Contract v1 and G3 ROI methodology.

Production verification passed after deployment of the final G18 readiness checkpoint: the latest GitHub Actions recalculation returned `status: ok`, `score_count: 10`, 10 snapshot ids, and no failure ids; the public API/web surface shows 26 opportunities and 10 modeled strategies; old snapshots aged into stale correctly; successful recalculation returned latest snapshots to fresh and `/api/v1/ops/status` stale strategy count to 0.

The project is now `V1 COMPLETE — OPERATIONS / GROWTH MODE`. Do not create another mandatory implementation gate automatically.

Latest local health recheck (2026-09-25 21:39 Europe/Istanbul): doctor passed with PostgreSQL connectivity and local migration head `20260924_0012`; backend tests reached 100% without failed tests and frontend tests passed 57/57 (pytest emitted Windows sandbox cleanup warnings). The local growth report remains `DEGRADED` / `INCOMPLETE`: zero local acquisition/click/verified-revenue records, 44 referral gaps, and a stale distribution heartbeat for a stopped process. These local counts are not production data. The production ops endpoint could not be reached from this environment. GitHub remote `master` remains `b179e98` with five-minute refresh settings; local commits `b3efbbd` and `6f4ef3c` remain ahead and unpushed after HTTPS connectivity failed. No production or distribution action was performed.

Live status superseding the 2026-09-25 check (2026-09-26 Europe/Istanbul): `master` now includes deployed release `de3b779` plus its documentation checkpoint. Render deployment succeeded and the additive inbound-UTM migration ran. Production `/api/v1/ops/status` reports healthy app/database, 240-minute cadence, and 7 fresh eligible strategies; latest one-time GitHub recalculation was successful but degraded (7 refreshed of 15; 8 not current). Current growth measurement is incomplete: production aggregate counts are events/clicks, not unique visitors or verified revenue, and no platform performance records are persisted. Distribution publication was not triggered by this release.

Growth recheck (2026-09-26): last-28-day GA4 = 58 sessions / 4 active users (25 sessions explicitly test/manual; direct remainder is unclassified), Search Console = 162 returned page impressions / 0 clicks, YouTube = 215 views / 60 engaged views / 0 subscribers gained. Discovery scheduled task is succeeding. Distribution task/process is stopped; X remains disabled. YouTube Shorts worker is alive and has used its one-success daily publication cap. The unsupported device/time-fit homepage claim was removed in `822b6a1`; its homepage freshness wording and the follow-up catalog freshness correction (`6cd2812`) are live. V1 remains in OPERATIONS / GROWTH MODE and the acquisition goal is not complete.

Freshness-label follow-up (2026-09-26): commit `6cd2812` is live in Render deployment `dep-darvcmbbc2fs738n36i0` (19:45 Europe/Istanbul). Public `/opportunities` now labels DeFi Kingdoms, DIMO, Storj, GEODNET, Mysterium, and WeatherXM prior snapshots as “No current estimate” and explains stale/unavailable data are excluded from current rankings; Farmers World and Splinterlands show “Fresh strategy available.” Frontend tests passed 63/63; the targeted backend stale-catalog regression passed. The live verification confirms honest status labels, not broader model coverage or acquisition lift. V1 remains in OPERATIONS / GROWTH MODE; no numbered gate is active.
