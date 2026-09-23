# GamCryp V2 Master Control

Updated: 2026-09-23 (Europe/Istanbul)

This is the durable operational summary for the GamCryp V2 finish pass. Repository files, verified runtime state, provider logs, and deployment evidence outrank chat memory. This document does not override `AGENTS.md`, the master specification, the architecture, the ROI methodology, or the data contract.

## 0b. 2026-09-23 data freshness and measurement recovery

- Repository recovery commit `9200350` aligns the recalculation policy with the five-minute publication-fresh market observation window. The paid Render blueprint and beta workflow now use `*/5 * * * *`; a 30-minute scheduler left `/api/v1/rankings` empty between successful runs.
- CoinGecko price reads use a bounded 30-second in-process cache keyed by provider/request/transport. This reduces repeated identical calls across strategy variants without extending observation freshness or inventing values. A local production-shaped run refreshed 7 eligible strategies with 0 failures after DFK was policy-skipped.
- A manual GitHub Actions run on `2eebe25` (`35880386491`) completed with 7 fresh snapshots, 7 scores, 0 failure ids, and 8 policy-skipped strategies. Public `/api/v1/rankings` subsequently returned 7 items and public ops status returned `ok`.
- `/api/v1/ops/status` now exposes aggregate first-party measurement truth (`landing_events`, `outbound_clicks`, and content-performance records) separately from ROI/rankings. Empty acquisition data is reported as `instrumented_no_records`; browser capture configuration is not treated as proof of traffic.
- Render web deploy `dep-dapuq32d0e5s73agfdp0` is live from `2eebe25`; the Render environment override `GAMEFI_SCHEDULER_CADENCE_MINUTES` was corrected from `30` to `5`. Public verification now reports cadence `5`, `fresh_eligible_count=7`, `stale_count=0`, `unresolved_failure_count=0`, and the measurement field is live.

## 0c. 2026-09-23 live analytics and YouTube recovery

- Windsor.ai read access is now available for the connected GamCryp GA4 property (`551782569`), Search Console domain (`sc-domain:gamcryp.com`), and YouTube accounts. Last-30-day GA4 data filtered out explicit manual-test source labels and returned 5 active users, 5 new users, 41 sessions, 22 engaged sessions, 108 page views, and 5,173 engagement seconds. These are aggregate analytics values, not a claim of five unique human identities.
- Search Console returned 0 clicks and low nonzero impressions for the last 28-day window. YouTube read data verified the GamCryp channel with 7 prior videos, 196 prior lifetime views, and 2 subscribers before the new publication. The strongest prior Shorts were Acurast (60 views), GEODNET (39), and DFK/Aethir (31 each); GEODNET remains the next editorial priority but its current render is blocked by missing approved product-specific visual evidence.
- The explicitly approved Filecoin Storage Provider Short was published through the existing quality-gated handoff as public video `pr7D-6j0RMI`. Local state records the exact approved checksum and upload; the read-only YouTube probe reports `uploadedStatus=uploaded`, `privacyStatus=public`, and `processingStatus=processing`. The one-public-Short daily cap is now used for the local calendar day.
- Commit `ade0674` makes a prior `YouTubeAuthError` dead-letter self-recover after a read-only authenticated/channel/upload-scope probe succeeds. The worker no longer requires manual state-file editing after a transient OAuth restoration.

## 0a. Product-hardening pass (deployed and verified)

- The homepage and degraded fallback now use product language rather than the public-beta label.
- The homepage top-model view selects at most one strategy per opportunity without changing API ranking order.
- The browser rankings view groups repeated strategies under their opportunity, so one project cannot visually occupy the first several cards.
- These changes are deployed in `cbf28b0` and verified on `gamcryp.com` after the Render health check passed.
- Current proof media remains local-only; no additional YouTube publication is permitted after the one successful publication recorded for the local calendar day.

## 1. Source-of-truth rules

- `docs/STATUS.md` and the authoritative specification documents define product and engineering boundaries.
- Stored observations and snapshots preserve provenance, timestamps, freshness, model version, and input references.
- Missing, stale, invalid, or incomplete financial evidence is unavailable; it is never converted to zero or presented as current.
- A production claim is only considered verified when the repository, runtime, provider, or deployment evidence supports it.

## 2. Current production and repository state

- Active repository branch: `master`; current product-hardening changes are committed in `cbf28b0` and deployed.
- Product hardening and canonical-host commits are deployed; latest verified deployed source is `a738300`. Local distribution/runtime state is intentionally kept outside the product commits.
- Public Render web service: `gamefi-roi-web`, Ohio, Blueprint-managed. The operator dashboard showed the paid `0.5c-512mb` web plan on 2026-09-09. This removes the Free web-service sleep limitation, but does not guarantee application or database availability.
- The `cbf28b0` production deploy passed build, Alembic migration, and `/api/v1/ops/status` health checks. No billing change was made by Codex.
- Canonical public host is `https://gamcryp.com`; Render’s `onrender.com` host is infrastructure-only and must not appear in public canonical, Open Graph, Twitter, JSON-LD, or sitemap URLs.
- The paid web service may still show application, database, deploy, or edge/proxy failures; these must be classified separately rather than attributed to sleep.
- Render Postgres remains on the Free plan at the time of this verification. It is not production-grade: it expires after 30 days and does not provide the paid backup/PITR guarantees. The paid Blueprint target is `basic-256mb`.
- Direct requests to `gamcryp.com` can still receive Cloudflare/edge `429` Managed Challenge responses with `Cf-Mitigated: challenge`; this is not an application rate-limit response. Browser and controlled low-rate requests also reached 200 for `/`, `/opportunities`, `/methodology`, `/robots.txt`, `/api/v1/rankings`, and a representative strategy page.

## 3. Product invariants

- MODELED requires reproducible economics.
- GUIDE_ONLY supports evidence-backed setup, how-to, earning-mechanic, and claim content without unsupported financial ROI claims.
- Risk and Confidence are separate.
- Affiliate, referral, sponsorship, and commercial metadata never affects ROI, admission, risk, confidence, or organic ranking.
- YELLOW requires approval; RED never auto-publishes.
- No basic/system/robotic TTS is publishable. Approved narration is ElevenLabs with Sarah/Bella/Laura rotation.

## 3a. Controlled public route verification

The paid-web verification on 2026-09-07 used low-rate browser-shaped requests. Results were not treated as a crawler/indexability claim:

| Route | Observed result | Interpretation |
|---|---:|---|
| `/` | 200 | Origin reached successfully |
| `/opportunities` | 200 | Origin reached successfully |
| `/methodology` | 200 | Origin reached successfully |
| `/robots.txt` | 200 | Origin reached successfully |
| `/api/v1/rankings` | 200 on a later controlled request | Origin/API reached successfully |
| representative strategy page | 200 on a later controlled request | Origin/page reached successfully |
| `/rankings` | 200 on the controlled post-deploy check | Origin reached successfully; ranking presentation fix is live |
| `/sitemap.xml` | not re-probed in this closure check | No application change was made to sitemap generation |

Render application logs showed repeated `/api/v1/ops/status` 200 responses and public `/`, `/opportunities`, `/methodology`, and `/robots.txt` 200 responses. Cloudflare/edge responses without `x-render-origin-server` are not attributed to FastAPI without matching origin logs.

## 4. Catalog and model counts

- Opportunities: 51 total; 8 MODELED; 43 GUIDE_ONLY.
- Modeled strategies: 15.
- Content inventory: 165 topic candidates; 137 READY short-form packages; 6 PARTIAL; 22 BLOCKED; 0 READY long-form.
- Logo coverage: 12 of 51 opportunities have verified local logo assets; the renderer uses a branded identity-card fallback for the rest. Missing official assets remain a content-asset follow-up; no logos are fabricated.
- Guidance and ROI-unavailable coverage is generated from the catalog and preserves missing evidence as explicit unavailable state.
- Public opportunity cards expose one compact, evidence-backed start/earn cue when catalog guidance exists. Ranking cards expose up to two recorded risk-contribution reasons, without changing score or ranking semantics.

## 5. Referral and official destinations

Official destinations and reviewed outbound redirects remain allowlisted and separate from model inputs. Referral metadata is commercial-only. X now has a local official-API user-context path; automatic posting is enabled only in the ignored local `.env`, while repository defaults remain fail-closed.

## 6. Distribution state

- `GAMEFI_DISTRIBUTION_LIVE=true` in the local `.env`, but the current queue is fail-closed by the creative gates and today's one-success cap is already consumed; no additional upload is permitted today.
- Windows task `GamCryp Distribution Worker` exists, is enabled, runs at login, and was observed in `Running` state without a terminal window.
- Short handoff buffer target is bounded at 14; the current local handoff contains 0 queued and 3 previously uploaded records. New items are admitted only after the current creative contract, narration, asset, checksum, and frame-QA checks pass.
- YouTube daily cap remains one successful public Short per local calendar day. The local cap state records one success for 2026-09-09, so no further upload is permitted today. The cap check and successful-upload state update are protected by a process lock.
- Failed narration/render never enters the handoff. Music-only or silent media is never publishable: every Short requires approved ElevenLabs narration with provider/voice/model metadata. X failures are isolated from YouTube.
- The visual gate requires a category-specific hook, six planned beats with at least five meaningful scenes, scene diversity, approved non-caption product visuals, identity representation, transitions, validated safe captions, no clipping, a natural GamCryp evaluation close, a brand sting, matching narration/script metadata, and representative post-render frame QA. GamCryp is not shown as a generic intro.

## 7. YouTube and narration

- YouTube OAuth configuration and publisher code are present locally; no secret values are recorded here.
- Existing proof renders passed only the earlier structural gate; they are not approved under the current creative-director contract until an approved real product/UI/device visual is present and frame QA passes.
- ElevenLabs account quota/auth failure remains fail-closed. No basic TTS, music-only, or silent fallback is permitted for publishable Shorts. Missing approved product visuals also block before narration credits are spent.
- No long-form video is rendered because the enrichment layer found zero truly eligible candidates.

## 8. X

X OAuth user context is verified as `@GamCryp` with `tweet.write`, `users.read`, and refresh-token capability. The local `.env` is set to `GAMEFI_X_PUBLISHING_MODE=live` and `GAMEFI_X_AMPLIFICATION_AUTO_REPOST=true`; no post or retweet succeeded because the Developer Console returned `402 Payment Required / credits depleted`. The worker records that state as degraded/cooldown and does not use fixtures or stale feeds. Live X discovery and engagement ranking are implemented in `app.distribution.x_intelligence`; retweets remain restricted to fresh, catalog-relevant, explicitly whitelisted official accounts with a minimum engagement threshold. Non-API browser automation is intentionally not implemented. No YouTube or other-channel behavior was changed in this X-only pass.

## 8a. Operations commands

From the repository root:

```powershell
Get-ScheduledTask -TaskName 'GamCryp Distribution Worker' | Select-Object TaskName,State
Get-Content data/local/youtube/autonomous_daily_cap.json
Get-Content distribution/publish_queue/youtube_short_handoff.json
$env:GAMEFI_X_PUBLISHING_MODE='manual'
$env:GAMEFI_X_PUBLISHING_MODE='disabled'
$env:GAMEFI_DISTRIBUTION_LIVE='false'
Get-ScheduledTask -TaskName 'GamCryp Distribution Worker' | Disable-ScheduledTask
$env:GAMEFI_DISTRIBUTION_LIVE='true'
Get-ScheduledTask -TaskName 'GamCryp Distribution Worker' | Enable-ScheduledTask
```

The LIVE flag is local `.env` state and is currently `true` for the quality-gated worker. Disabling the scheduled task is an additional emergency stop; it does not delete queues.

## 9. Content and long-form readiness

- `config/distribution/content_inventory.json` and `content_packages.json` were regenerated from current catalog truth.
- `config/distribution/long_form_enrichment.json` contains 35 deterministic, source-bound candidates: 0 eligible and 35 blocked. The block reasons preserve insufficient evidence/word budget and unresolved evidence; the 1,200-word, six-section, and eight-minute contract was not loosened.
- Long-form rendering is therefore skipped.

## 10. Observability

- GA4: repository implementation and consent-gated browser wiring are present; local/production activation is not proven in this pass.
- Sentry: repository integration is present; Render logs show initialization, but full production error coverage is not independently verified here.
- PostHog: repository integration is present and consent-gated with explicit events; production activation is not proven here.
- First-party inbound/outbound analytics are implemented with privacy-minimal records. Commercial analytics remain separate from model data.
- PostHog outbound attribution uses the server-side `/go` redirect as the single `outbound_go_click` authority. Browser-side PostHog duplication was removed; future redirect events carry `event_origin=server_redirect` and `traffic_class=automated|human_or_unknown` so crawler/link-preview traffic can be separated. Historical totals before this change are not treated as unique human clicks.

Operational gaps still requiring explicit monitoring: snapshot refresh age, queue backlog, worker heartbeat freshness, database backup success, and ElevenLabs quota/auth failure duration. The worker writes an atomic local heartbeat and the repository includes a non-zero-exit freshness check; external alert delivery is not configured. Sentry initialization is visible in Render logs, but production alert delivery is not independently verified.

## 10a. Backup and recovery

- Reconstructible from Git: catalog definitions, strategy/model code, migrations, renderer, queue schemas, and policy docs.
- Not safely reconstructible from Git alone: current PostgreSQL snapshots/history, publishing state, quota state, worker retry state, OAuth/token files, and generated media.
- Current Render Free Postgres has no production-grade backup/PITR guarantee. This remains a documented operational limitation, not a blocker to using the public read-only catalog.
- Minimum recovery action: upgrade the database, create a scheduled logical export to an operator-controlled private location, and test one restore before enabling unattended publishing.
- Until that exists, honest classification is unknown RPO/RTO for database-backed history; local static artifacts remain separately recoverable if copied.

## 11. SEO/AEO/GEO

- Repository coverage includes canonical host configuration, server-rendered pages, sitemap, robots policy, answer-ready blocks, logos, and structured-data safeguards.
- Stale snapshot wording is hardened to use recorded/model language; browser/API failures now time out and render a usable error or degraded state. Catalog coverage uses explicit “Guide-only opportunities” counts instead of an ambiguous “ROI not measured” total.
- Public edge indexability and search-engine indexation are not claimed. The audit edge responses were Cloudflare challenges, not successful crawler responses.

## 12. Current limitations

1. Render Postgres remains Free; backups/PITR and expiry protection are not production-grade.
2. Cloudflare/edge Managed Challenge can return 429 to some non-browser probes; security was not weakened.
3. ElevenLabs currently reports 0 remaining credits; narrated production is blocked. Music-only and silent Shorts cannot enter the publish queue.
4. The worker restarted successfully on 2026-09-13 after its legacy refill batch was made tolerant of missing/stale ranking IDs. It is healthy, but it has no queued GREEN Short because no approved visual+narration package currently qualifies.
5. X uses local manual-ready handoff rather than API/browser automation. Email notification is not configured, but the outbox remains Git-visible and remotely readable.
6. The public homepage still needs deployment reconciliation: live `/api/v1/opportunities` reports 51 catalog entries while server-rendered homepage content shows its older 50-reviewed/8-opportunity slice. The safe homepage/catalog correction is included in the pending production release.

## 13. Release-closure decision

The current verified public web release is `cbf28b0`; Render build, migration, health check, public routes, and the manual snapshot workflow were verified on 2026-09-10. Publishing remains limited by the one-success daily YouTube cap; X has a local manual-ready path.

## 14. Verification evidence

Verified on 2026-09-09 from repository tests, source inspection, local rendering/UI contracts, operator Render screenshots, prior controlled route evidence, and local route tests. No secrets are included.

## 15. Operating model

- ChatGPT: strategy, review, and operational interpretation.
- Codex CLI: implementation, deterministic tests, local runtime checks, and Git.
- Work/browser: authorized research and operations review.
- NVIDIA NIM: helper only; never financial truth.

## 16. Rule

Chat memory cannot override repository, runtime, provider, or deployment verification.
