# GameFi ROI — Project Status

Updated: 2026-09-28
Project version: 0.1

2026-09-28 pre-deploy completion: Farmers World is now excluded from current rankings, opportunity strategy summaries, current latest endpoints, sitemap strategy pages, and new numerical distribution drafts while its historical snapshot API remains available. The public catalog summary states in plain language that the model is parked; Alcor/CoinGecko provider details stay in internal operational notes. The current canonical Content Pack marks the prior numeric Farmers World draft RED/NOT_REFRESHABLE and both social queues block it. The homepage and opportunity catalog retain the 52-opportunity guide inventory. API, refresh policy, source-validation, canonical SEO, UI, and publishing regressions were updated. Full `backend/tests` passed on 2026-09-28; `git diff --check`, Python compilation, and frontend syntax checks are being completed before release. Web/Cron deploy and live refresh verification are pending. No X/YouTube post or Render credential change was made.

2026-09-27 production follow-up: web commit `7143e1c` deployed as Render web deployment `dep-dasma3o473hc738v6big` and is Live. Read-after-deploy confirms the Splinterlands strategy page shows the caveat that SPS staking/delegation capital and rental costs are excluded, with a link to official staking guidance. Render Cron was inspected read-only: the latest scheduled run failed with exit status 1 after a CoinGecko `401` on three Farmers World strategies; it wrote four new snapshots, skipped eight, and left no newly reused snapshots. The live page's 18:47 UTC snapshot aligns with this run but does not mean Cron succeeded. Earlier hourly runs shown in the dashboard also failed. Per user instruction, no Render environment values or credentials were changed. `node --check frontend/assets/app.js`, Python compilation for the touched modules, and `git diff --check` passed; tests were not run. See `docs/GROWTH_OPERATING_PLAN.md` for implications and next actions.

2026-09-27 product-ops correction (implementation pending deployment): after a permitted public WAX RPC and official Gate public-market API feasibility check, all Farmers World Axe variants are classified `NOT_REFRESHABLE`, the opportunity is `PARKED`/`unknown`, and current rankings exclude parked/rejected opportunities. This stops serving a questionable stale value as a current ranked result and removes the failing Alcor/CoinGecko path from future scheduled production runs. Existing history is preserved. Changed source and regression expectations are not yet deployed; no tests have been run for this change. Render API credentials/settings remain untouched.

2026-09-27 pre-deploy verification: the historical Farmers World numeric X draft is now RED/NOT_REFRESHABLE, removed from the human-approval list, and explicitly blocked in the handoff and publisher queues. No X post was published. Focused regression suites `test_snapshot_refresh.py`, `test_api_v1.py`, `test_distribution_content_pack.py`, and `test_x_publisher.py` passed together. Python compilation and `git diff --check` passed. Web/Cron deployment and live recalculation verification remain pending; no Render credential or setting was changed.

2026-09-27 growth/product-economics review: the live Splinterlands estimate depends on a fixed configured SPS-per-win input, while current official guidance says ranked awards depend on rating, bonuses, staked SPS, and the season pool. Updated warning and user-facing starting-capital/source copy to disclose that SPS stake/delegation capital and rental costs are excluded; ROI math is unchanged. Official references and static checks are recorded in `docs/GROWTH_OPERATING_PLAN.md`. Review of current Alcor Terms of Use found a restriction on accessing its website to build a similar or competing website; the Farmers World refresh adapter currently calls the Alcor API. No further Alcor API read, refresh, or environment change was made. This needs a permitted-source path before scaling or claiming stronger model coverage. No tests run.

2026-09-27 18:35 UTC Search Console follow-up: resubmitted sitemap remains accepted, while the UI still shows its previous read/count pending processing. Kaito URL inspection says the page is already indexed; a priority recrawl was accepted after the guide update. Timpi inspection says “Discovered – currently not indexed”; Search Console accepted its priority crawl request after the live test flow. Neither request proves that Google has crawled or indexed the pages yet. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 18:31 UTC Kaito Yaps guide release: commit `1d01fdf` is Live on Render as `dep-daslvhu0tbcc7380ulqg`. The live route returns 200, `index,follow`, and its self-canonical; rendered guide says wallet is optional, explains Kaito's anonymized partner wallet-list sharing, and warns never to share private keys. `sitemap.xml` includes the route; Google Search Console accepted resubmission of the changed sitemap, but still shows the prior 20 discovered pages/27 Sep read, so crawl processing is unverified. Post-deploy ops is `ok`, database `ok`, 7/7 eligible fresh, zero unresolved failures, and eight policy-skipped stale. No financial value or ROI was assigned. No Render key/settings changed; automated tests were not run.

2026-09-27 18:23 UTC growth checkpoint: public ops at 18:15 UTC is `ok` / database `ok`, 7/7 eligible snapshots fresh, zero unresolved failures, eight policy-skipped strategies stale. The latest snapshot run was scheduled GitHub workflow `36338223640` at 17:47 UTC: three Farmers World snapshots written, four Splinterlands reused, eight skipped. This does not verify Render Cron. Fresh 28-day connected analytics show 58 GA4 sessions (33 tagged QA/operator, 23 unattributed Direct, two X/social), four active users, and zero YouTube-attributed sessions. Search Console's returned query sample has 17 impressions / zero clicks. YouTube's ten returned video rows total 198 views, 54 engaged views, 26 watched minutes, and zero gained subscribers. Added sourced Kaito Yaps wallet privacy guidance and search eligibility; Render API key/settings remain untouched. Automated tests were not run.

2026-09-27 18:05 UTC Farmers World cash-out copy fix: commit `247cb77` deployed to Render as `dep-daslkvjbc2fs73fqf9mg`. Public opportunity and strategy pages return 200; the plain-language section now says WAX/USD is a reference conversion rather than an executable sell quote, and the prior generic realizable-value claim is absent. Ops remains `ok`, database `ok`, 7/7 refresh-eligible snapshots fresh, zero unresolved failures; eight strategies remain policy-skipped and stale. No calculation, Render setting, or provider credential changed. `python -m py_compile backend/app/web/seo.py` and `git diff --check` pass; automated tests were not run.
2026-09-27 17:58 UTC acquisition recheck: fresh connected 28-day reads show 58 GA4 sessions, of which 33 are known QA, 23 are unattributed direct, two are X-tagged, and none are attributed to YouTube. Returned Search Console page rows have zero clicks; 11 YouTube video rows total 198 views / 54 comparable engaged views and zero gained subscribers. These do not verify qualified human acquisition. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 18:10 UTC Acurast YouTube path update: read current public metadata before editing. Updated Acurast Setup Short `nw04V-8NAtI` to route viewers to its related long-form video, which links to the tagged Acurast evidence page; updated companion `ve5GT3A6jj8` to put the tagged link and explicit “ROI not measurable” evidence limitation in the opening description. YouTube Data API read-after-write confirms both descriptions, both videos remain public, and the exact GamCryp Acurast page returns 200 with the unavailable status. The long-form content-pack JSON now matches the live description. Baseline remains small (Acurast Short 60 views / 14 comparable engaged views / 24 watched minutes; zero subscribers) and new acquisition has not been measured yet. No video visibility, footage, title, tag, or thumbnail changed.

2026-09-27 17:48 UTC Farmers World display trust fix: commit `051f0f8` is Live on Render as `dep-dasld23bc2fs73fpe2ig`. Live strategy and opportunity HTML both return 200 and include the notice that CoinGecko WAX/USD is a reference conversion rather than an executable USD sell quote. Post-deploy ops is `ok`, database `ok`, 7/7 eligible snapshots inside freshness policy, zero unresolved failures; eight policy-skipped strategies remain stale and the last observed scheduled refresh remains 16:47 UTC. Render's API key and service settings were not accessed or changed. No tests were run; syntax/compile and whitespace checks passed.

2026-09-27 homepage search snippet and acquisition diagnosis: commit `0e261be` is Live on Render as `dep-daskvhl9fdbs73dtvgug`. The homepage title now describes the GameFi/DePIN ROI finder and the description names costs, modeled earnings, risk, and evidence freshness. Chrome verified the live title and rendered page. Current 28-day connected reports show 58 GA4 sessions, 33 known QA sessions, zero Google Search Console clicks on the sampled pages, and 198 YouTube views with zero subscribers gained; none establish qualified human acquisition. The primary constraint remains very limited useful current economics: two opportunities have current results and all positive daily estimates are below $0.01. The CoinGecko API key was not accessed or modified. No automated tests were run; Python compilation and `git diff --check` passed.

2026-09-27 17:26 UTC YouTube CTA audit: fresh GA4/Search Console/YouTube reads confirm the prior acquisition diagnosis. Most sampled recent YouTube descriptions direct viewers to the generic channel-profile link; the Acurast Short with the most views in the 28-day sample (60 views, 14 engaged views, 24 watched minutes) lacks a direct tagged link, while its long-form companion already has one and has no views yet. Added the measurable next experiment to `docs/GROWTH_OPERATING_PLAN.md`; no public channel metadata was changed in this check.

2026-09-27 17:28 UTC distribution access check: the connected vidIQ account currently returns no authorized YouTube channels; its write endpoint therefore cannot update video descriptions yet. X has no connected analytics connector. No new channel permissions were granted and no public post or video metadata was changed.

2026-09-09 distribution hardening: autonomous worker execution is restricted to the quality-gated Short handoff, the one-public-Short daily cap is process-locked, and an atomic worker heartbeat is emitted for operator health checks. The local Task Scheduler runner anchors execution at the repository root; re-registration still requires Windows task-registration permission.

V2 finish-pass operational truth is maintained in `docs/MASTER_CONTROL.md`; this document remains the authoritative gate board and currently has no numbered gate active.

2026-09-10 product-hardening pass: the public-beta label removal, opportunity-diversified homepage model view, repeated-strategy grouping, and distribution hardening were deployed as `cbf28b0` and passed controlled public-route verification. Snapshot refresh was manually triggered after deploy and completed successfully; provider/data-contract limitations remain explicitly surfaced.

## Current state

**PROJECT STATUS: V1 COMPLETE — OPERATIONS / GROWTH MODE**

2026-09-27 homepage earnings-context improvement: commit `3e427a3` deploy `dep-daskodrbc2fs73fmqumg` is Live. The homepage derives a low-earnings note from currently loaded fresh USD strategy rows using decimal-safe comparisons. Chrome verified 7 fresh USD-valued models, with four positive estimates all below $0.01/day. `node --check frontend/assets/app.js` and `git diff --check` passed; automated tests were not run. No numbered gate is active. Render provider credentials/settings remain untouched at the user's instruction.

2026-09-27 setup-fit finder: commit `3a13bae` deploy `dep-daskqsvpn0mc738ruia0` is Live. Homepage ROI filters now include device/setup type, matched against catalog platform tags; no-match wording distinguishes empty current models from setup mismatch. Chrome verified selector and options in public DOM. JavaScript syntax and whitespace checks pass; automated tests were not run, and no production filter submission was made to avoid test analytics traffic. Render provider settings remain untouched.

2026-09-27 16:10 UTC product-path update: Render deployment `dep-dasjvefpn0mc738ofspg` built commit `256c255` and reached Live. Chrome verified the Opportunities catalog's five setup filters; mobile returns 9/52 and clearing returns 52/52. First screen/catalog review and fresh GA4/Search Console reads are recorded in `docs/GROWTH_OPERATING_PLAN.md`. Current diagnosis remains weak economic utility plus minimal search reach: only seven fresh strategy rows across two opportunities, 44 ROI-unavailable opportunities, four GA4 users in the latest 28-day view (not verified as human), and eight Search Console queries with 15 impressions / zero clicks. A scenario/evidence copy mismatch found on the Splinterlands detail page was corrected and deployed below. The user declined changing the Render CoinGecko key; the key and Render environment settings were not opened or modified. Remaining priorities are trustworthy useful economics, permitted fresh data, and qualified acquisition measurement.

2026-09-27 16:18 UTC scenario-copy trust fix shipped: commit `101ca0a`, Render deployment `dep-dask2gp7lnhs739hvf70` Live. Chrome confirms the Splinterlands page now shows a model-specific caveat rather than contradicting its strategy snapshot. Public ops at 16:18:10Z is HTTP 200 / `degraded`, database ok, 7/7 eligible snapshots fresh, three unresolved failures, eight stale/policy-skipped strategy records. No key or Render environment values were opened or changed.

2026-09-27 16:28 UTC growth measurement update: Rankings now emits a consent-gated `strategy_comparison_view` event once when a visitor selects a second strategy, distinguishing actual comparison use from a single checkbox click and enabling a landing → comparison → outbound-intent funnel. Commit `f717468` is Live on Render as `dep-dask6v59fdbs73dqth3g`; the deployed JavaScript asset returns HTTP 200 and contains the event. Static JS syntax and whitespace checks passed; automated tests were not run. The latest Render Cron log record (15:47 UTC) shows 0 new snapshots, 4 reused Splinterlands snapshots, and 3 Farmers World failures on CoinGecko HTTP 401; 8 other strategy rows remain non-refreshable/partial. Public ops at 16:28 UTC remains degraded, with database ok, 7/7 eligible models fresh, three unresolved failures, and eight stale/policy-skipped strategies. The API key and environment settings remain untouched; see `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 15:45 UTC acquisition diagnosis: current hero and visitor paths are now legible, but product utility remains too weak to drive search/social acquisition: seven fresh strategy rows cover only Splinterlands and Farmers World; the lead Splinterlands estimate is about $0.0019/day from $10, with 0.57% 30-day ROI, 5,289 modeled break-even days, risk 100 and confidence 40. Render Cron at 15:36 UTC refreshed four Splinterlands rows but failed three Farmers World rows on CoinGecko HTTP 401; live ops at 15:44:59Z is `degraded`, though all seven eligible rows remain inside freshness policy. WAX chain orderbook exploration did not establish an executable USD exit price; CoinPaprika free use is non-commercial and public redistribution requires Enterprise. Key/config were not viewed or changed. Historical channel reads show little measured acquisition and no attributable YouTube sessions, while current user analytics could not be refreshed through connected Windsor/PostHog tools. No site, settings, provider or channel changes were made; this pass updated the growth diagnosis and priorities only. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 15:07 UTC growth release and recovery: homepage first-screen decision paths and setup-cost/value proposition shipped in commit `e02863c`, Render deployment `dep-dasj0s8473hc738h6r20` Live. Chrome verification confirmed the visitor paths appear before the low modeled return card and the under-$25 link yields all seven matching current strategies. Static checks passed; no automated tests were run. GitHub recovery run `36327836866` refreshed all seven eligible snapshots at 14:58:46 UTC with zero failures; live ops returned `ok`, database `ok`, 7/7 fresh, zero unresolved failures. The latest observed Render Cron run at 14:50 UTC still failed all seven strategies on CoinGecko HTTP 401/429; Cron cadence remains unresolved. Render's CoinGecko credential was not opened or changed at the user's instruction. Eight non-eligible/policy-skipped strategy records remain stale. See `docs/GROWTH_OPERATING_PLAN.md` for the full acquisition evidence and next priorities.

2026-09-27 15:14 UTC opportunity-detail clarity fix: commit `44ebb75` is Live on Render as `dep-dasj34g473hc738hhmj0`. Chrome verified `/opportunities/kaito-yaps` now states “What is still unverified: Points cannot currently be converted to cash reliably” in the plain-language summary, instead of generic filler. This is a copy/data presentation correction; it does not expand modeled coverage or establish acquisition lift. No tests were run for this copy-only patch. CoinGecko key/configuration remains untouched.

2026-09-27 15:12 UTC production ops recheck: `/api/v1/ops/status` remains `ok` with database `ok`, 7/7 eligible models fresh, zero unresolved failures, newest snapshot age ~13 minutes, and last successful calculation at 14:58:46Z. Eight configured but policy-skipped strategies are stale (last snapshots Aug 31 or Sep 8); `ok` does not mean all 15 strategies are current. First-party totals are 4,429 landing events and 1,476 outbound clicks, with zero content performance records; these are event counts, not unique users or proof of attributable acquisition.

2026-09-27 14:17 UTC refresh diagnosis: fresh Render dashboard evidence shows 19 Cron runs and no successful run; the latest scheduled run (13:47 UTC) exited 1 after seven strategy failures, created/reused zero snapshots, and lasted 27.8 seconds. Its structured output identifies CoinGecko `get_token_prices`: the first SPS calls returned HTTP 401 and later per-strategy retries returned HTTP 429. The public ops sample at 14:12:06Z is `degraded`, database `ok`, 7/7 eligible snapshots still inside the six-hour freshness window (newest age about 66 minutes), seven unresolved failures, 370 historical failures, and eight policy-skipped/stale records. GitHub Actions currently has only one recent scheduled success (13:05Z); manual successes do not prove scheduled reliability. Root failure is the provider rejecting the configured credential, with same-run retries compounding the provider rate limit. The user declined changing the Render CoinGecko API key; it was not inspected or changed. No manual refresh was triggered. A no-key SPS price endpoint was discovered, but the provider requires prior notice for commercial use and prominent attribution; it is not adopted. A separate DEX API option has terms that treat access as acceptance of a binding contract, so no endpoint was accessed pending an explicit action-time decision. This keeps the reliability issue open.

2026-09-27 14:09 UTC growth UX release: ranked strategy comparison shipped in Render deployment `dep-dasi6bjtqb8s7386n0j0` from commit `79d9cb8`. On `/rankings`, manually verified selecting two strategies renders source-backed opportunity, starting capital, modeled net/day, 30-day ROI, break-even, risk, confidence, effort/time (with unmeasured attention explicit), and calculation freshness side by side; Clear selection resets the panel. Comparison is capped at three selections and does not change model inputs or organic ordering. `node --check frontend/assets/app.js` and `git diff --check` passed; no tests were run. The public page returned successfully and the deployment reached Live. CoinGecko API key and Render environment settings were not viewed or changed. This feature does not establish human acquisition or improve the still-degraded refresh status recorded below.

2026-09-27 13:16 UTC growth continuation: published the reviewed 90.048-second Acurast long-form companion publicly as `ve5GT3A6jj8`; publisher verification now reports `processed` / `succeeded`, and its custom thumbnail is present. YouTube Studio confirms the Acurast Setup Short `nw04V-8NAtI` points to “Can Your Phone Earn ACU? 3 Checks Before Setup”; Studio showed “All changes saved.” The channel profile CTA remains tagged to `/opportunities`, while the video description carries its Acurast-specific tagged route. Long-form queue metadata and UTM parsing are represented explicitly in code and the canonical Content Pack. Public ops at 13:16:23Z is `ok`, database `ok`, 7/7 eligible snapshots fresh, zero unresolved failures, latest success 13:05:50Z; eight non-eligible/policy-skipped strategy records remain stale, so this is not full-catalog health and does not establish automatic cadence. The tagged Acurast page and rankings API return HTTP 200. The user explicitly declined changing Render's CoinGecko key; no Render configuration or key was viewed or changed. No test suite was run; render/ffprobe and YouTube publication, processing, thumbnail, Studio save, public routes, and package CLI verification were checked. Later `git diff --check` passed through commit `eb90247` at 13:50 UTC; tests remain unrun.

2026-09-27 13:25 UTC acquisition-flow improvement prepared: production ops is `ok`, 7/7 eligible fresh, zero unresolved failures, with eight stale/out-of-policy strategies. First-party totals are 4,392 landing events / 1,476 outbound events / 0 content records; these are not unique people or attributable conversion. Exact same-day GA4 filter found no sessions for the newly published Acurast video campaign yet; no synthetic traffic was generated. Updated opportunity-detail server/client rendering to hide the external top CTA when there is no fresh model, remove the duplicate empty-state on never-modeled pages, and show evidence-matched internal next steps for unavailable/stale pages. `node --check frontend/assets/app.js`, Python compilation of `backend/app/web/seo.py`, and `git diff --check` pass. Render deployment `dep-dashjf0jo6nc73bqj4l0` released commit `77a692e` at 13:28 UTC; internal health checks returned 200. Fresh Chrome verification of the public Acurast page confirms the no-model state, clear ROI evidence gap, no top external CTA, and internal links to modeled strategies and all opportunities. No tests were run. Render's CoinGecko API key/settings remain untouched.

2026-09-27 08:07 UTC Search Console follow-up: successfully resubmitted the current sitemap; Google confirmed acceptance, but last read remains Sep 26 / 34 discovered pages, so crawl effect is not yet verified. The page-index report is stale (last updated Sep 21): 17 indexed, 68 excluded (62 discovered-not-indexed, 3 redirects, 2 robots-blocked, 1 crawled-not-indexed). The `/opportunities` landing page is indexed; “timpi node rewards” led to it for 8 impressions at average position 61.1, with no clicks. The 28-day baseline (Aug 28–Sep 24) is 124 impressions, 0 clicks, 48.5 average position. No Timpi ROI model was added because public material does not establish current reproducible payout economics. Search Console's URL reindex request reached a reCAPTCHA-gated step and was not submitted. See growth plan for detail.

2026-09-27 08:12 UTC Search Console page breakdown: top 28-day rows were `/opportunities` (31 impressions), three DFK Jeweler strategy URLs (27/15/14), homepage (22), Kaito Yaps opportunity (14), and Gods Unchained opportunity (13); all 10 visible pages had zero clicks. DFK routes must be reconciled with current fresh-model/noindex behavior before investing in those pages. The user explicitly said not to change the Render CoinGecko API key; no key was opened or modified. See growth plan.

2026-09-27 09:49 UTC Render Cron diagnostic verification: deployed commit `9c528e8` completed its first scheduled run at 09:47:16Z. It safely reported CoinGecko `get_token_prices` HTTP 401 and HTTP 429 by strategy, with no raw provider body or credential in the output. All seven eligible strategies failed, zero snapshots were created or reused, and the live API remains `degraded` (seven fresh snapshots from 08:16:48Z; unresolved failures increased to 14). This confirms the deployed diagnostic patch and confirms Render's refresh is still blocked. The Render API key was not opened or changed. Do not claim scheduler recovery; use the known-working GitHub recovery only when a refresh is needed.

2026-09-27 09:56 UTC measurement quality correction prepared: PostHog's last-28-day events contained 67 page views (3 people), 18 strategy views (2 people), and 7 ranking-to-strategy clicks (2 people); all queried events were classified `Automation`, and no `$session_id` was present. Added explicit `consented_browser` provenance plus a 30-minute session id to consented browser events, a matching short-lived `/go` cookie, and the same PostHog `$session_id` on consented server redirect events. Rejecting analytics deletes the session cookie and storage value. Backend observability tests pass 8/8; frontend tests pass 63/63. Deployment and post-deploy PostHog event verification remain pending; consent is still required, and these fields identify event origin/session rather than proving a visitor is human.

2026-09-27 08:18 UTC recovery/UI finding: GitHub workflow `36305677249` successfully refreshed all seven eligible strategies (`refreshed_count=7`, `reused_count=0`, `failed_count=0`); live ops returned `ok`, 7/7 fresh, zero unresolved failures, last success `08:16:48Z`. This restores data through GitHub only; Render Cron remains unproven and its CoinGecko key was left unchanged at the user's request. Live rankings UI had visual sequence `#1, #2, #5, #3, #6, #4, #7`; corrected card and JSON-LD ordering to preserve rank and added a regression test. Change pending deployment. Targeted web suite passed 14/14; `git diff --check` passed.

2026-09-27 08:24 UTC organic ranking-order release: Render deploy `dep-dasd48e0tbcc73et90f0` made `ad06524` live. Production `/rankings?capital_max=25` returned HTTP 200; visible rank chips and structured ItemList positions both run `1–7` in ascending organic rank. API remains `ok`, 7/7 refresh-eligible snapshots fresh, zero unresolved failures after GitHub recovery. No API credential was changed.

2026-09-27 08:34 UTC homepage coverage clarity fix prepared: production has 15 configured strategy records across eight opportunities but only seven fresh ranking results across two opportunities. The homepage summary is being changed to distinguish current results from configured models; guide-only count stays visible. Frontend tests passed 63/63; backend web tests passed 14/14; release pending.

2026-09-27 08:04 UTC SEO release verification: Render deploy `dep-dascreo473hc73fodbs0` made commit `1bc8f74` live. Production sitemap returns 20 canonical URLs (19 daily, one weekly; zero hourly); stale DIMO strategy is excluded. DIMO strategy and opportunity detail return HTTP 200 with `noindex,follow`; fresh Splinterlands strategy returns HTTP 200 with `index,follow`. Live ops remains `degraded` with last successful refresh 06:38:26 UTC, 7/7 eligible snapshots fresh, 14 unresolved failures, and 101 historical source request errors. No tests were run; `git diff --check` passed.

2026-09-27 07:57 UTC operations/SEO recheck: Render Cron logs show CoinGecko `get_token_prices` HTTP 401 and HTTP 429 across scheduled runs through 07:47 UTC. The user declined changing the key; no Render secret was opened or edited. GitHub Actions schedules `36283152098` (00:39 UTC) and `36300672548` (06:38 UTC) succeeded. Live ops at 07:57 UTC is `degraded`, with 14 unresolved failures, last successful refresh 06:38:26 UTC, 7/7 refresh-eligible models fresh and eight other strategy records stale. Cadence is not proven reliable. Implemented a freshness-aware sitemap/indexing patch locally: stale/no-snapshot strategy, opportunity, and game pages are noindex; only currently fresh model pages enter sitemap; page summaries prefer a fresh model; sitemap changefreq defaults to daily. Deployment verification pending. `git diff --check` passed; no tests were run. See growth plan.

2026-09-27 00:13 UTC production release check: Render deployment `dep-das5trnpn0mc73ev6lm0` successfully made commit `5a24980` live. Browser verification confirms the strategy page displays the configured activity assumption and the old unquantified placeholder is gone; `/api/v1/rankings?limit=1` returns the matching `effort_summary`. The strategy page and API return HTTP 200. Cron's 23:47 UTC attempt failed with seven unresolved failures and zero refreshes; current ops is `degraded`, while all seven eligible snapshots remain fresh within the six-hour window (last success 23:13:14 UTC). Current visible logs do not prove a specific provider status for this failure. The user explicitly declined changing the CoinGecko API key; no secret/environment setting was changed. No tests were run; `git diff --check` passed. Growth plan has the detailed evidence.

2026-09-27 23:14 UTC recovery check: GitHub Actions run `36278728801` completed at 23:13 UTC with `auto_refreshed=7`, `refreshed_count=7`, `reused_count=0`, and `failed_count=0`. The live API now reports `ok`, 7/7 eligible strategies fresh, zero unresolved failures, and persisted snapshots at `2026-09-26T23:13:14.982482Z`. This verifies GitHub recovery, not Render Cron credentials/cadence. The product change `2becc3b` remains undeployed; live `effort_summary` is null because Render deploys are manual and the dashboard session is signed out. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 02:05 Europe/Istanbul product improvement pushed to `master` as `2becc3b`: strategy summaries now expose activity quantities already present in model configuration (ranked battles/day or production cycles/tool/day) while stating that active player time is not measured. This does not alter calculations or rankings. The additive API/UI change is not deployed; live API omits the field and ops remains `degraded` with seven unresolved refresh failures. Render dashboard access and CoinGecko credential rotation remain pending with the account owner. `git diff --check` passed; no tests were run. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 01:53 Europe/Istanbul strategy-coverage clarification: live `/api/v1/rankings?limit=100` and `/rankings?capital_max=25` show seven fresh strategy results across two opportunities (four positive, three negative), not only two strategies. The homepage deliberately shows two representative cards, one per opportunity. Positive Splinterlands base estimate is +$0.001884/day at 0.565% 30-day ROI, risk 100/confidence 39; three other Splinterlands variants lose $0.000679–$0.003135/day; positive Farmers World variants earn only $0.000000165–$0.000001646/day. Results are from 22:12:36 UTC snapshots; Cron at 22:47 failed and did not update them. Prior “two current results” means two opportunities/representative cards, not two fresh strategies.

2026-09-27 01:47 Europe/Istanbul production recheck: the scheduled Render attempt at 22:47:14 UTC tried the seven eligible strategies and failed them; `SourceRequestError` increased from 31 to 38, unresolved failures returned to seven, and ops is `degraded`. Last successful snapshots remain 22:12:36 UTC and are still inside the six-hour freshness window. The public API does not report HTTP status codes for this attempt; 401/429 were observed on earlier Render runs only. This supersedes the preceding prediction that the 22:47 run might be a no-op. New key entry is not confirmed; GitHub recovery uses a different secret and does not verify Render.

2026-09-27 01:40 Europe/Istanbul cadence guard: the next Render scheduled run at 22:47 UTC is only 35 minutes after the 22:12:36 GitHub recovery snapshot, inside the configured 60-minute calculation window. A successful run may reuse all snapshots without a CoinGecko request and would not verify the Render credential. Do not call Cron recovered until a post-window run attempts source access and persists fresh results; keep the GitHub path as recovery.

2026-09-27 01:36 Europe/Istanbul analytics configuration recheck: GA4 Admin now shows `outbound_click` starred as a key event (only other key event is inactive `purchase`). Windsor still reports 3 outbound event occurrences and zero key events for the trailing 28 days. The star’s change time was not checked; GA4 counts events after configuration, so this may be a newly enabled prospective measure or a reporting mismatch. Keep it as outbound intent, not partner conversion; await naturally occurring, consented non-test traffic to verify reporting. This supersedes the earlier note that no funnel event was a key event. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 01:37 Europe/Istanbul search audit: live sitemap has 34 URLs, including eight stale strategy pages and seven overlapping filtered ranking pages; 33 entries declare `hourly` change frequency, even where the page's lastmod is Aug 31 or Sep 8. Search Console has only nine visible query strings and 17 query-row impressions / 0 clicks in this sample. Treat sitemap/canonical cleanup as a later SEO hygiene task after product utility and reliable fresh coverage, not the present acquisition lever. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 01:30 Europe/Istanbul product-funnel audit (coverage clarification added 01:53): the homepage shows two representative cards, one per modeled opportunity, while the primary “Start under $25” route contains seven fresh strategy results (four positive, three negative) across two opportunities out of 51 reviewed. The rankings filter budget/risk and opportunity metadata, but strategy pages explicitly say required time/effort is not quantified; the product therefore cannot match users on the time/device/eligibility constraints promised in its thesis. Public routes have no visitor-managed save/follow, alerts, or email subscription path. GA4 records strategy/opportunity/start/outbound events; later Admin review verified `outbound_click` is now a key event, although most current-period interactions are tagged operator tests and the key-event report still shows zero. Search Console query rows total only 17 sample impressions with zero clicks, mostly positions 47–83. See “User-facing funnel audit” in `docs/GROWTH_OPERATING_PLAN.md` for the ordered product and retention work.

2026-09-27 01:22 Europe/Istanbul channel re-read: Windsor GA4 aggregate is 55 sessions, 4 active users, 32 engaged sessions, 0 key events for the last 28 days. Its source breakdown totals 56 (30 operator/test, 23 direct/unattributed, 2 X, 1 unset); source rows are directional and no YouTube-attributed row appeared. Search Console reports 109 property impressions / 0 clicks; page rows sum to 149 and are not additive. YouTube reports 215 views, 60 engaged views, 39 watch minutes, and 0 subscribers gained. These figures replace the prior channel aggregates below; no qualified acquisition loop is proven. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 01:15 Europe/Istanbul recovery recheck: GitHub workflow `36275500580` refreshed all seven eligible strategies (`refreshed_count=7`, `reused_count=0`, `failed_count=0`). Its read-only recovery evidence and a direct production read confirm `ok`, seven of seven eligible snapshots fresh, zero unresolved failures, and newest calculation at 22:12:36 UTC. The homepage now shows Splinterlands at 0.57% modeled 30-day ROI, $0.0019/day, risk 100, confidence 39, and 5,308 modeled break-even days; Farmers World is 0.17% and under $0.0001/day. This restores current data through GitHub only. It does not validate the Render Cron key or scheduled Cron, whose earlier runs returned CoinGecko 401/429. The user must revoke the key posted in chat, enter a rotated key in Render, and verify the next scheduled Cron. See `docs/GROWTH_OPERATING_PLAN.md` for the recovery evidence and revised execution order.

2026-09-27 01:10 Europe/Istanbul live recheck: public homepage, opportunities, methodology, and ops-status endpoints return HTTP 200; the catalog API returns 51 opportunities. The homepage shows only two current results; the lead is $10 capital, 0.54% modeled 30-day ROI, $0.0018/day, risk 100, confidence 39, and 5,542-day modeled break-even. `/api/v1/ops/status` remains `degraded`: latest success 21:09 UTC, failed attempt 21:47 UTC, seven unresolved eligible-strategy failures, 7/7 snapshots currently within freshness, and eight policy-skipped/stale strategies. Runtime counters (4,230 landing events / 1,472 outbound clicks) are not qualified-user or conversion counts; content performance records are zero and external analytics reads are unavailable in runtime. The CoinGecko key was pasted into chat; the account owner must revoke it and enter a rotated key in Render. No key was entered by Codex. See the live-recheck/KPI section of `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 production deploy and recheck: Render deploy `dep-das3pdnavr4c738sto00` made commit `f781270` live at 21:45 UTC. Direct public checks returned HTTP 200 for `/opportunities`, the Farmers World strategy detail, and `/api/v1/ops/status`. The refreshed catalog now shows “Modelable” for stale/unavailable but model-feasible candidates and no “Ready” feasibility badges. The refreshed Farmers World SSR says 13 source observations (13 fresh), six configured assumptions, and 12 derived metrics. Ops remained `ok` at 21:46 UTC: 7/7 eligible strategies fresh from 21:09 UTC, zero unresolved failures, eight policy skips. This repairs public presentation; it does not refresh excluded models or prove hourly scheduler reliability.

2026-09-27 scheduler recheck: the 21:47 UTC scheduled Render Cron and an authorized manual run at 21:53 UTC both failed all seven eligible strategies. Render logs show CoinGecko `get_token_prices` HTTP 401 five times and HTTP 429 twice; failures span the Farmers World and Splinterlands models. `render.yaml` and the Cron environment page confirm the Cron key references `GAMEFI_COINGECKO_API_KEY` from `gamefi-roi-web`, so the Cron variable is configured; the key/provider authorization is still suspect, but its value is not exposed or changed. The 21:55 UTC GitHub Actions recovery run succeeded technically but reused all seven snapshots because they were still inside the 60-minute calculation window (`refreshed_count=0`, `reused_count=7`); it did not clear the Render failures. Production remains `degraded`, 7/7 eligible snapshots still within freshness, seven unresolved failures, eight policy skips. Restore source access, then verify a run writes new snapshots before calling the cadence healthy.

2026-09-27 channel measurement correction: latest trailing-28-day Windsor reads show GA4 49 sessions / 4 active users / 28 engaged sessions / 0 key events. Source split: 25 Codex smoke/operator sessions, 22 direct, 2 X/social, and 1 unset. No YouTube-attributed session appeared. Search Console returns 85 property impressions / 0 clicks; the page-grouped query totals 125 impressions, so the grouped value is inconsistent and not additive evidence. The GamCryp YouTube account has 193 views / 52 engaged views / 29 watch minutes / 0 subscribers gained. Official YouTube rules confirm Shorts description/comment URLs are non-clickable; a tagged long-form companion remains the next no-spend path experiment. These reads still show no verified acquisition loop. Details and source links are in `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-27 distribution preparation: created a draft 90–120 second English long-form bridge script with an exact content-tagged rankings URL, screen plan, description, and release checks under `distribution/content_packs/youtube_longform_bridge_20260927.md`. It contains no numeric return claims and is not uploaded; current-state checks and a creative review are still required before production. No paid narration or X credits were used.

2026-09-27 catalog wording correction: live catalog review found “Ready” on model-feasible opportunities whose current estimates were stale/unavailable (for example, DeFi Kingdoms), which can read as “current result ready.” Changed the public feasibility label to “Modelable” in server-rendered and hydrated catalog cards. Freshness/ROI availability remain separate labels. Deployed and live verification completed in `dep-das3pdnavr4c738sto00`.

2026-09-27 PostHog measurement recheck: in project `260916`, all 64 pageview events in the last 28 days are tagged by PostHog as bot/Automation across three person IDs, while the `sessions` table has zero rows and `$session_id` is absent from the observed event taxonomy. The same period has 1,064 base outbound events and 922 destination-class events; each `/go` redirect is recorded as both event types, and all queried rows are bot-tagged. These are not human visitor/conversion counts. Newer server redirects include a custom `traffic_class`, but that does not override PostHog's virtual bot label. The diagnosis is documented in `docs/GROWTH_OPERATING_PLAN.md`; qualified human acquisition remains unproven.

2026-09-26 public strategy SSR correction: a fresh live Farmers World strategy page still rendered “0 live observations” despite the API reporting 13 fresh input observations. The interactive frontend and server-rendered strategy description used different count sources; updated the SSR summary to use freshness input counts and preserve configured-assumption / derived-metric counts. Deployment and live recheck are pending. Growth audit also reconfirmed only 2 of 51 opportunities have current results, and public X / YouTube audience remains very small (4 followers / 2 subscribers). See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-26 first Render Cron run: scheduled run at 20:47 UTC exited 1 after 27.9 seconds. Its summary shows seven attempted strategies failed, zero new snapshots, and eight policy skips. Production ops now reports 7 unresolved failures; `SourceRequestError` count rose from 17 to 24, matching those seven failures. The Render logs contain per-strategy error messages, but their exact text has not yet been captured. Do not call scheduler reliability restored; diagnose the provider error before retrying manually.

2026-09-26 free fallback recovery: GitHub Actions dispatch `36271204879` completed at 20:56 UTC on current `master`; it refreshed all seven eligible strategies, with zero failures and eight policy skips. Production ops now records last success `20:56:21Z`, 7/7 eligible fresh, zero unresolved failures, and 8/15 overall stale or unrefreshable. This confirms the production DB and shared provider credentials can support a successful refresh outside that failed Cron attempt; it does not identify the transient/provider difference or prove the Cron cadence reliable.

2026-09-26 live ranking value recheck: the fresh top-ranked strategy shows $10 capital, $0.00179 net/day, 0.537% modeled 30-day ROI, 5,592-day break-even, risk 100, confidence 39. Three Farmers World scenarios show 0.146–0.171% modeled 30-day ROI and negligible estimated daily net; three Splinterlands variants are negative. The model coverage is current again for seven eligible strategies, but it is not yet a compelling earnings proposition. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-26 scheduler reliability follow-up: GitHub Actions had not produced a scheduled recalculation since 13:08 UTC. The Render Blueprint now shows the hourly Starter Cron resource built at minute 47 UTC, using the existing database and Render-held provider-secret references; the web service remains Free. At the 20:42 UTC production check, the API reported 60-minute cadence and 7/7 eligible strategies fresh from the previous 18:40 UTC snapshot, but Render showed no successful Cron runs yet. GitHub's schedule remains enabled as a fallback until a scheduled Render run succeeds. Cron billing has a $1/month minimum plus active runtime; obtain an explicit monthly spend ceiling before triggering a paid manual run or making further spend commitments. No numbered gate is active; this is Operations/Growth work, not a gate reopen.

2026-09-26 mobile hydration correction: commit `3ef32f4` reuses the full 100-record opportunity API page when hydrating the homepage, preventing the live 51 / 43 catalog coverage from reverting to 50 / 42. Frontend suite passed 63/63; Render deployment `dep-das1cl0jo6nc739qtegg` is Live from `3ef32f4`, and a fresh mobile reload retained 51 opportunities / 43 guide-only entries with no horizontal overflow. This corrects display consistency only; it does not demonstrate acquisition growth. See `docs/GROWTH_OPERATING_PLAN.md`.

2026-09-26 homepage decision transparency: commit `9a97f68` adds the snapshot's modeled break-even duration to the homepage's top strategy card, next to starting capital, net/day, and 30-day ROI. The 63-test frontend suite passes; Render deploy `dep-das1guou01pc73e9t630` is Live from `9a97f68`. Mobile production verification shows the leading Splinterlands estimate at 5,601 break-even days and preserves 51 opportunities / 43 guide-only records after hydration. No acquisition lift is claimed; see `docs/GROWTH_OPERATING_PLAN.md`.

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

Production UX follow-up (2026-09-26): Render deployment `dep-darvs5fpn0mc73e8o6o0` is live from `8509080`. Public strategy details now distinguish 13 fresh source observations from six configured assumptions and 12 derived metrics; verified after reloading the page to bypass its previously cached frontend bundle. This is a transparency correction, not an acquisition result. V1 remains in OPERATIONS / GROWTH MODE; no numbered gate is active.

2026-09-26 homepage focus release: Render deployment `dep-darvv7gjo6nc739lsuo0` is live from `5f6fe3f`. A fresh public browser session confirmed the guide-heavy catalog is collapsed by default and accurately summarizes 50 opportunities, 2 with current modeled results, and 48 without a current estimate; ROI finder results and filters remain visible. This is a usability change, not evidence of user growth. V1 remains in OPERATIONS / GROWTH MODE; no numbered gate is active.

Homepage server-rendered first-paint correction — 2026-09-26: `b5ab1b1` deployed as `dep-das01jgjo6nc739m5m8g`. Live HTML returns 200 with the catalog cards inside a closed details disclosure, and `/api/v1/ops/status` returns 200. The server-rendered initial view now matches the focused homepage intent. No traffic/conversion lift is claimed. See `docs/GROWTH_OPERATING_PLAN.md` for the active acquisition diagnosis.

Homepage coverage correction (2026-09-27): Render deployment `dep-dasdanp7lnhs738n2v60` is live from `2a5abf5`. The live homepage clearly separates 7 current strategy results across 2 opportunities from 15 configured strategies across 8 opportunities and 43 guide-only opportunities. Production operations API returned healthy status, 7/7 eligible models fresh, zero unresolved provider failures, 60-minute configured cadence, and 8 policy-skipped stale models; the most recent refresh remained at 08:16:48Z at the 08:37Z check, so scheduled refresh reliability is not established. First-party totals are event counts, not unique visitors or conversions. Growth objective remains active and incomplete.

2026-09-27 11:45 Europe/Istanbul DFK coverage evidence gate: revisited the three stale DFK Jeweler routes because they held the strongest historical strategy-page impressions. Official DFK docs say its Jeweler reward is variable with fee volume and has no fixed APR; a direct read-only request to the Ava Labs listed DFK Chain RPC returned HTTP 405. DFK is not being re-enabled or represented as current until RPC access, current contract/liquidity inputs, and fixture evidence are validated. The current key has not been changed. Growth priority order is now explicitly recorded in `docs/GROWTH_OPERATING_PLAN.md`: verify a naturally scheduled refresh; accept only official/public reproducible economics for further coverage; measure qualified consented acquisition separately from test/server events; then test the prepared no-spend YouTube path; consider retention only after utility. API at 08:37Z was ok, 7/7 eligible fresh, zero unresolved failures; scheduler reliability remains unverified.

2026-09-27 latest channel measurement: connected GA4 returned 55 sessions/256 page views for Aug 31–Sep 27; `codex_smoke` test traffic accounts for 30 sessions/188 views, and the tagged X row has 2 sessions. Search Console returned 12 impressions/0 clicks across nine query/page/date rows, narrower than the prior 124-impression baseline and requiring freshness/window reconciliation. YouTube (Aug 30–Sep 24) reported 198 views, 54 engaged views, and zero subscribers gained. PostHog's 28-day pageview, strategy-view, and outbound events were all classified as Automation; do not count these as human acquisition. No credential changed. Detail and limitations are recorded in `docs/GROWTH_OPERATING_PLAN.md`.

PostHog provenance follow-up (2026-09-27): although every 28-day event row is virtually classified `Automation`, a property breakdown separates the recent server redirects: 53 `outbound_go_click` and 45 fallback events declare `human_or_unknown`, while 17 of each declare automated. The remaining 997 / 863 rows lack current provenance fields. This mismatch blocks interpreting either aggregate as human clicks; growth reporting must segment by `event_origin` and declared traffic class and audit consented client events.

Render Cron recheck (2026-09-27 08:52 UTC): dashboard shows the recalculation Cron scheduled at minute 47 each hour, “No successful runs yet,” and the latest 14 visible runs failed. The latest run at 08:47:06Z refreshed/reused zero models and left seven unresolved failures; live ops at 08:49:53Z is `degraded`, though the seven published models remain within the six-hour freshness window from GitHub recovery at 08:16:48Z. Structured output exposes failure IDs, not provider messages; earlier Render attempts had CoinGecko HTTP 401/429. The user declined a Render key change. No additional retry or key edit was made. See growth plan.

2026-09-27 09:02 UTC Render log diagnosis: filtering the last 24 hours of Cron logs revealed repeated CoinGecko `get_token_prices` HTTP 401 and 429 responses. This confirms authentication rejection plus rate limiting in the Render path, but does not identify the key value as the sole cause. The user declined a key change and no credential was opened or edited. Commit `187a4f4` adds sanitized per-strategy provider/operation/HTTP status details to the Cron run JSON. Three focused backend suites passed 24/24; code is pushed but Cron redeployment and next scheduled diagnostic verification remain pending. See growth plan.

2026-09-27 10:06 UTC consented-session attribution release: web commit `d0a7477` deployed successfully to Render as `dep-dasekiojo6nc73bf7qdg`; Render reported `Deploy succeeded | Live`, and `/api/v1/ops/status` health checks returned 200. Backend observability tests passed 8/8 and frontend tests passed 63/63 before deployment. The change joins consented browser product events and `/go` redirects with an ephemeral session ID, and rejection clears the stored ID/cookie. Post-deploy event joining is not yet verified; only consented sessions carry this field, and it is not a human/bot verdict. No API key was changed. Growth remains active and incomplete.

2026-09-27 10:18 UTC live operations and attribution recheck: public status at 10:10:53Z is `degraded`, database `ok`, 7/7 refresh-eligible strategies fresh, 14 unresolved failures, latest success still 08:16:48Z. The 10:17 scheduled GitHub recovery was not present at 10:18; last scheduled run remains 06:38:04Z. Render Cron's next natural cycle is due at 10:47 UTC; no manual run was started. A controlled tagged `codex_smoke` visit did not appear in the recent PostHog query, and current pageview/outbound schemas do not list `$session_id`. No consent preference was changed; live join remains unverified and organic visitor status is unaffected by this absence. Homepage now shows 51 opportunities, 2 with current models, 15 configured strategies across 8 opportunities, 43 guide-only, and 49 without current model coverage. Keep the key untouched.

2026-09-27 10:36 UTC Gods Unchained guide update deployed: Render web commit `760d6a5` reached live state at 10:36:43Z. Public route `/opportunities/gods-unchained` returned HTTP 200 and contains the Daily Play & Earn community-pool explanation and official guide/API links; it remains `noindex` and no financial result was added. No Cron or API credentials were changed. Syntax compilation and `git diff --check` pass; tests not run. Growth remains active and incomplete.

2026-09-27 10:47 UTC natural Render Cron recheck: scheduled run at 10:47:16Z failed with sanitized CoinGecko `get_token_prices` HTTP 401/429 errors and produced zero new/reused snapshots. Public ops at 10:47:57Z remains `degraded`, database `ok`, last successful refresh 08:16:48Z, 7 eligible strategies still shown fresh from that older run, and unresolved failures increased to 21. Do not describe those values as newly refreshed. User explicitly declined changing the Render API key; no key/environment value was viewed or changed. Growth remains active and incomplete.

2026-09-27 10:51 UTC GitHub recovery: workflow run `36313870284` completed successfully after a user-authorized 60-minute dispatch. Live ops at 10:52:32Z reports `ok`, database `ok`, 7/7 eligible models fresh, zero unresolved failures, last successful snapshot at 10:51:51Z. Public rankings return 7 rows with matching 10:51:51Z snapshot time. This proves the manual recovery route, not reliable scheduled cadence; Render Cron still fails with provider 401/429. No Render setting or API key was changed or viewed. User-facing economic coverage remains limited to two opportunities and poor expected returns; growth remains active.

2026-09-27 CoinGecko display attribution prepared: frontend now conditionally adds a visible linked “Price data provided by CoinGecko API” line beside modeled financial metrics when the snapshot contains a LIVE USD price input. This follows the provider's attribution guidance; it does not establish that the current Demo plan permits the product's public/commercial use. Licensing must be confirmed before scaling distribution or monetization. No API key was viewed or changed. `node --check frontend/assets/app.js` and `git diff --check` pass; deployment pending; no tests run. Growth remains active.

2026-09-27 CoinGecko attribution SSR correction: live verification showed the previous client-only attribution did not appear in initial server-rendered rankings or strategy details. Added conditional attribution to both server-rendered surfaces when a LIVE USD price metric is present. python -m py_compile backend/app/web/seo.py and git diff --check pass; no tests run. Follow-up deployment and live UI verification pending. No API key changed.

2026-09-27 CoinGecko attribution SSR fix is live: commit 74b76f3 deployed successfully to Render (dep-dasfikl9fdbs73d7l0fg). Fresh-load UI verification confirms the provider attribution appears in initial ranking cards and strategy detail, alongside modeled financial metrics. Python syntax and diff checks passed; tests were not run. No API key changed.

2026-09-27 11:15 UTC growth priority checkpoint: user explicitly declined changing the Render CoinGecko API key; it remains untouched, and the prior key-rotation recommendation is superseded. Production ops currently returns ok, database ok, 7/7 refresh-eligible snapshots fresh, zero unresolved failures, newest snapshot 10:51:51Z; eight policy-skipped strategies remain stale and historical failure count is 349. This does not prove Render Cron schedule reliability. Updated docs/GROWTH_OPERATING_PLAN.md with the user decision and current execution sequence: preserve the working recovery path; improve a narrow evidence-backed user decision; clean analytics attribution; then run one tagged content test and measure qualified progression before scaling. No tests run.

2026-09-27 11:17 UTC PostHog read-only funnel audit: confirmed project 260916 and live event/session schema. Trailing-28-day product event rows (67 pageviews/3 persons, 18 strategy views/2 persons, 7 ranking-to-strategy clicks/2 persons) are all classified Automation; every queried event has zero $session_id, and the sessions table has no rows or UTM sessions. Outbound counts remain ambiguous: 997/863 rows lack origin fields; 53/45 are server_redirect human_or_unknown and 17/17 automated, but PostHog classifies every segment as Automation. This does not establish human acquisition; live consented-session join remains unverified. No synthetic event or consent change made. Detailed caveats recorded in the growth plan.

2026-09-27 11:26 UTC Kaito Yaps landing-page repair deployed: Render web deployment `dep-dasfq9t9fdbs73d8i740` made `14e0416` live. Fresh public-route inspection confirms the current FAQ source link and the new practical guidance sections render; financial ROI remains unavailable. This targets the 14-impression/zero-click Kaito page from the prior Search Console sample; click impact remains unverified. Python syntax and `git diff --check` passed; no tests were run. Render Cron and the CoinGecko key were not touched.

2026-09-27 11:38 UTC Timpi search-intent page prepared: the official `Timpi-official/Nodes` repository publishes dated NTMPI/month reward schedules, while Timpi's July 2026 migration update says the destination chain is not yet selected. Added a guide-only Timpi opportunity with current official reward/setup/migration references and explicit unavailable-ROI reasons; no token amount was converted to USD. Search Console's prior 28-day sample showed eight `timpi node rewards` impressions landing on the broad `/opportunities` page at about position 61, with zero clicks, and `/opportunities/timpi` previously returned 404. This page is the sole explicit guide-only exception to the current index/sitemap rule because it now answers observed intent with primary evidence; all other unmodeled pages retain the existing rule. Render web deploy `dep-dasg0om0tbcc73f8au3g` made `fc64032` live; public verification returned HTTP 200, `index,follow`, self canonical, sitemap inclusion, and candidate API state with zero modeled strategies. Python syntax and `git diff --check` passed; tests not run; Render Cron and the CoinGecko key remain untouched.

2026-09-27 12:00 UTC ranking UX deployed: commit a162712 is live as Render web deployment dep-dasg8vvpn0mc7389f7jg. The rankings page now shows the ranked strategy list directly after the heading; the repeated comparison block is a collapsed disclosure with count and freshness preview, and Explore rankings follows the results. Live desktop accessibility-tree inspection confirms all 7 strategy rows and their positive/negative values, risk, confidence, timestamps, assumptions, and warnings remain present. This is a usability improvement only; no acquisition lift is established. Current fresh coverage remains 7 strategies across 2 opportunities and the leading modeled result is still very weak. Syntax checks and git diff --check passed before deploy; tests were not run. No API key or Cron setting was changed. Growth remains active/incomplete.
2026-09-27 12:03 UTC live growth recheck: public ops at 12:01:14Z reports `degraded`, DB ok, 7/7 eligible snapshots within freshness policy, 7 unresolved failures, 356 historical failures, eight policy skips, and latest successful snapshot 10:51:51Z. Render's 11:47 attempt failed. Latest GitHub scheduled run is 06:38:04Z; subsequent successes at 08:16 and 10:51 were manual dispatches, with no 10:17 schedule run. Automatic cadence remains unproven. No manual refresh was triggered while results remained fresh; no credential, Cron setting, or workflow was changed. Explicit activity counts exist, but actual active minutes and hourly earnings are not evidenced; do not infer them. Leading model remains approximately $0.002/day, 0.6% modeled 30-day ROI, risk 100, confidence 39, and 5,011-day break-even. Product economics and qualified acquisition remain unresolved; growth objective active/incomplete.
2026-09-27 12:08 UTC strategy-rankings UX release: commit `a5d21fb` is live on Render as `dep-dasgdfl9fdbs73db268g` (`Deploy succeeded | Live`; internal `/api/v1/ops/status` health check returned 200). `/rankings` now renders all seven ordered strategies individually with their own metrics and disclosures; homepage keeps opportunity-grouped diversity. Live forced-reload accessibility inspection confirms ranks 1–7, including negative scenarios and per-strategy ROI/net/day/capital/break-even/risk/confidence/freshness/effort/warnings. The Quick comparison disclosure opens and shows matching count, sort order, update time, and commercial policy. No calculations, source data, ranking rules, credentials, or Cron settings changed. `node --check frontend/assets/app.js` and `git diff --check` pass; tests were not run. QA browser request did not accept analytics consent and is not acquisition evidence. Growth remains active/incomplete.
2026-09-27 12:14 UTC ranking-card readability deployed: commit `61be9c3` is live on Render as `dep-dasgg60jo6nc73bm7de0`. On a fresh production browser load at desktop width, rankings show two readable card columns and place starting capital, modeled net/day, 30-day ROI, and break-even directly below each strategy title, before long risk explanations. All seven strategy rows still expose their own metrics and caveats. This improves scanability, not the underlying economics or proven acquisition. Live leader remains about $0.002/day and 0.6% modeled 30-day ROI with risk 100/confidence 39; coverage is seven strategies across two opportunities. No API key, Cron configuration, or analytics consent was changed. `node --check frontend/assets/app.js` and `git diff --check` passed; tests were not run. Growth remains active and incomplete.

2026-09-27 12:19 UTC authorized manual recovery: GitHub Actions run `36318573837` (`workflow_dispatch`, 60-minute calculation window) completed successfully. The public ops endpoint at 12:19:50Z returned `ok`, database `ok`, 7/7 refresh-eligible snapshots fresh, zero unresolved failures, latest successful run `12:19:22Z`; historical failure count remains 356. This restores current public data through the known GitHub path. It does not prove automatic hourly scheduling: the latest prior scheduled run remained 06:38Z and later runs were manual. No API key, Render environment, or Cron setting was changed. Growth remains active.

2026-09-27 12:36 UTC recheck after recovery: public ops remains `ok`, database `ok`, 7/7 eligible snapshots fresh and zero unresolved failures; latest successful run remains 12:19:22Z. `gh run list` still shows no scheduled event after 06:38Z; the 12:19Z success is manual only. Do not call automatic cadence repaired. Growth plan now defines the YouTube funnel cohort, progression measures, QA exclusions, and diagnostic decision rules; Acurast long-form remains a research-backed script draft, not a rendered or published video. API key unchanged.

2026-09-27 13:36 UTC acquisition/UX follow-up: read-only GA4 (trailing 28 days) returned 123 search impressions across the 15 highest page rows and zero clicks; the exact Acurast campaign had no sessions, while at least 33 GA4 sessions were internal/manual QA campaigns. PostHog session overview after configured internal/test filtering returned 0 visitors, views, and sessions; the previous event sample was classified as Automation. YouTube's processed daily report (through Sep 24 only) recorded 198 channel views, 54 engaged views, 26 minutes watched, and zero gained subscribers; this is not attributable to the Sep 27 video, which has no per-video report row yet. Live 1280×720 homepage inspection found the fixed consent panel obscures the first strategy card's lower details/actions. Responsive CSS now keeps consent choices side by side at narrow widths and reduces panel height; deployment and live responsive verification pending. User's API-key constraint remains in force; no secret/config changed. No tests were run.

2026-09-27 13:50 UTC consent-panel fix: commit `1004a80` is live on Render as `dep-dashtf8473hc738cct9g`; build and health checks succeeded. Fresh 1280×720 production screenshot confirms the analytics-consent panel no longer covers the homepage first screen. Public ops returns HTTP 200/status ok/database ok, with 7/7 refresh-eligible models fresh, eight policy-skipped models stale, and latest successful calculation 13:05:50Z (about 41 minutes old at the 13:46Z status sample). Consent was not submitted; no tests were run. Render's CoinGecko key/settings remain untouched.

2026-09-27 13:52 UTC growth/ops recheck: scheduled GitHub workflow `36321190551` completed successfully at 13:06:07Z and production records its latest successful calculation at 13:05:50Z. The next calculation attempt at 13:47:15Z left seven unresolved failures; public ops at 13:51:39Z is `degraded` though database is `ok` and 7/7 eligible snapshots remain within the six-hour freshness policy. Eight configured models are stale/policy-skipped. Do not confuse current snapshot validity with scheduler health; no manual recovery was triggered while snapshots remain fresh. YouTube's Sep 27 per-video report has no row yet for Acurast companion `ve5GT3A6jj8`; exact GA4 campaign session read is also empty at this early point. Organic search remains 123 page-row impressions / zero clicks in the sampled window, and filtered PostHog overview has zero sessions; qualified human acquisition and video lift remain unproven. CoinGecko key untouched. No tests run.

2026-09-27 14:53 UTC provider containment checkpoint: commit `de2de79` is deployed to both the web service (`dep-dasinfrncjis73aap850`) and Cron build (`bld-dasipng473hc738g3t90`). After one manual production Cron run, all seven eligible strategies still failed with CoinGecko 401/429 and zero snapshots; public ops remained `degraded`, DB ok, 7/7 snapshots inside freshness policy, 14 unresolved and 377 historical failures at 14:52:57Z. Cache impact on provider request count is inconclusive from available logs. CoinGecko API key/environment were not inspected or changed. Continue acquisition only after a permitted reliable price route; DEX API access requires separate action-time acceptance because the published terms make access binding.

2026-09-27 15:29 UTC source-path change prepared: Splinterlands SPS reward valuation now consumes the already-recorded `splinterlands.settings.sps_price_usd` observation from the official settings API, retaining provider, official-API source type, timestamp, freshness and source field. It no longer makes separate CoinGecko calls for the four SPS strategies. Public strategy/ranking attribution now identifies this value as the official Splinterlands reference price and explicitly says it is not an executable sell quote. The live read-only probe returned status `ok` at 15:27 UTC, with SPS reference price $0.0043676 and modeled net/day $0.00189; this remains a very low modeled result, not a reason to imply attractive earnings. The price was within about 1.2% of the independently read BSC SPS/WBNB and WBNB/USDT reserve spot at the time, a point-in-time cross-check rather than an exit-liquidity guarantee. Focused tests passed (5), Python and browser-script syntax checks passed, and `git diff --check` passed. This change is not yet deployed as of this entry. It does not repair the three Farmers World price failures, stale policy-skipped models, or prove scheduled refresh reliability. CoinGecko key/configuration was neither viewed nor changed. Sources: [Splinterlands settings API](https://api.splinterlands.com/settings), [Splinterlands SPS token reference](https://support.splinterlands.com/hc/en-us/articles/8454967337748-Importing-Tokens-to-the-Metamask-External-Wallet).

2026-09-27 15:37 UTC production verification after commit `1a1328b`: Render Web deployment `dep-dasje8bncjis73adu010` and Cron latest build `bld-dasjfdnpn0mc738m9sn0` both succeeded. The public `/rankings` page now shows four Splinterlands snapshots at 15:36 UTC with official Splinterlands SPS reference-price attribution and the non-executable-sell-quote caveat. The model reads $0.0019/day net for the lead strategy (0.57% modeled 30-day ROI, about 5,289 break-even days); this confirms technical freshness, not product attractiveness. A manual Cron run refreshed all four Splinterlands strategies but failed the three Farmers World strategies with CoinGecko HTTP 401. Public ops at 15:36:59Z is therefore `degraded`, database `ok`, 7/7 refresh-eligible snapshots fresh, three unresolved failures, 380 historical failures, and eight policy-skipped stale strategies. First-party counters are 4,433 landing events / 1,476 outbound clicks / zero content-performance rows; these are event totals, not unique users or attributable acquisition. Scheduled reliability is not yet proven. CoinGecko key/configuration remained untouched. No gate acceptance claim is made; V1 remains in operations/growth mode.
