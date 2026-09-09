# GamCryp V2 Master Control

Updated: 2026-09-09 (Europe/Istanbul)

This is the durable operational summary for the GamCryp V2 finish pass. Repository files, verified runtime state, provider logs, and deployment evidence outrank chat memory. This document does not override `AGENTS.md`, the master specification, the architecture, the ROI methodology, or the data contract.

## 0a. Product-hardening pass (local, pending deployment)

- The homepage and degraded fallback now use product language rather than the public-beta label.
- The homepage top-model view selects at most one strategy per opportunity without changing API ranking order.
- The browser rankings view groups repeated strategies under their opportunity, so one project cannot visually occupy the first several cards.
- These changes are tested locally but are not considered production-live until the deployed commit is verified on `gamcryp.com`.
- Current proof media remains local-only; no additional YouTube publication is permitted after the one successful publication recorded for the local calendar day.

## 1. Source-of-truth rules

- `docs/STATUS.md` and the authoritative specification documents define product and engineering boundaries.
- Stored observations and snapshots preserve provenance, timestamps, freshness, model version, and input references.
- Missing, stale, invalid, or incomplete financial evidence is unavailable; it is never converted to zero or presented as current.
- A production claim is only considered verified when the repository, runtime, provider, or deployment evidence supports it.

## 2. Current production and repository state

- Active repository branch: `master`; current product-hardening changes are in the local working tree and are not yet committed.
- Product hardening and canonical-host commits are deployed; latest verified deployed source is `a738300`. Local distribution/runtime state is intentionally kept outside the product commits.
- Public Render web service: `gamefi-roi-web`, Ohio, Blueprint-managed. The operator dashboard showed the paid `0.5c-512mb` web plan on 2026-09-09. This removes the Free web-service sleep limitation, but does not guarantee application or database availability.
- The production source commit still requires a fresh dashboard/live-route check after the current local hardening changes are deployed. No billing change was made by Codex.
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

Official destinations and reviewed outbound redirects remain allowlisted and separate from model inputs. Referral metadata is commercial-only. The X manual outbox contains GREEN-only handoff data and no secrets; automatic X posting remains disabled.

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

X API access remains unavailable. `GAMEFI_X_PUBLISHING_MODE=manual` now lets the local worker prepare one exact GREEN post in `distribution/manual_outbox/x_manual_ready.json` without calling X; the operator pastes it into the normal X website and confirms the checksum. Non-API browser automation is intentionally not implemented because X rules prohibit it. Visible GamCryp links use an occasional deterministic cadence; source URLs remain in metadata. Own posts now carry bounded hashtags, explicitly verified handles when configured, and local media metadata with a verified-facts fallback card. The manual amplification radar is fail-closed and writes only actionable, deduplicated candidates to `distribution/manual_outbox/x_amplification_ready.json`; it never calls X. `GAMEFI_X_AMPLIFICATION_AUTO_REPOST=false` remains required.

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

The LIVE flag is local `.env` state and must remain `false` until visual proof approval. Disabling the scheduled task is an additional emergency stop; it does not delete queues.

## 9. Content and long-form readiness

- `config/distribution/content_inventory.json` and `content_packages.json` were regenerated from current catalog truth.
- `config/distribution/long_form_enrichment.json` contains 35 deterministic, source-bound candidates: 0 eligible and 35 blocked. The block reasons preserve insufficient evidence/word budget and unresolved evidence; the 1,200-word, six-section, and eight-minute contract was not loosened.
- Long-form rendering is therefore skipped.

## 10. Observability

- GA4: repository implementation and consent-gated browser wiring are present; local/production activation is not proven in this pass.
- Sentry: repository integration is present; Render logs show initialization, but full production error coverage is not independently verified here.
- PostHog: repository integration is present and consent-gated with explicit events; production activation is not proven here.
- First-party inbound/outbound analytics are implemented with privacy-minimal records. Commercial analytics remain separate from model data.

Operational gaps still requiring explicit monitoring: snapshot refresh age, queue backlog, worker heartbeat freshness, database backup success, and ElevenLabs quota/auth failure duration. The worker now writes an atomic local heartbeat, but alerting on stale/missing heartbeat is not yet independently verified. Sentry initialization is visible in Render logs, but production alert delivery is not independently verified.

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
4. Autonomous YouTube worker is enabled locally, but today's one-public-Short cap is already consumed; X uses local manual-ready handoff rather than API/browser automation.

## 13. Release-closure decision

The current previously verified public web release is `a738300`; the operator dashboard later showed the paid web plan, but the current local hardening changes are still pending deployment/live verification. Publishing remains limited by the one-success daily YouTube cap; X has a local manual-ready path.

## 14. Verification evidence

Verified on 2026-09-09 from repository tests, source inspection, local rendering/UI contracts, operator Render screenshots, prior controlled route evidence, and local route tests. No secrets are included.

## 15. Operating model

- ChatGPT: strategy, review, and operational interpretation.
- Codex CLI: implementation, deterministic tests, local runtime checks, and Git.
- Work/browser: authorized research and operations review.
- NVIDIA NIM: helper only; never financial truth.

## 16. Rule

Chat memory cannot override repository, runtime, provider, or deployment verification.
