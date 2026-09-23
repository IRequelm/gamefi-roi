# GamCryp Growth Operating Plan

Status: INCOMPLETE — implementation and live-service verification remain in progress.

Updated: 2026-09-23 (Europe/Istanbul)

This plan extends the completed engineering roadmap with the operating loop required to make GamCryp useful to users and grow it toward a USD 1,000 monthly revenue target within three months. The revenue target is a target, not a guaranteed outcome.

## Product loop

1. Observe Google Trends and authorized X signals.
2. Persist each new lead with provenance and a one-time approval token.
3. Email the operator a research summary and the exact `SITEYE_EKLE <token>` command.
4. On approval, add a clearly labelled `RESEARCH` candidate page. Do not invent an official URL, reward value, exit path, or ROI.
5. Verify official identity, participation, reward mechanism, and exit evidence.
6. Promote only evidence-backed candidates to GUIDE_ONLY or MODELED status.
7. Generate content from the approved evidence and current GamCryp pages.
8. Require creative review, product visuals, narration metadata, frame QA, and checksum approval before paid audio or external publication.
9. Publish at most two X posts and one YouTube Short per local day, subject to live credentials, quota, caps, and quality gates.
10. Measure acquisition, outbound clicks, verified conversions, verified revenue, and content performance separately from ROI and organic ranking.

## Workstreams and closure criteria

| Workstream | Closure evidence | Current state |
|---|---|---|
| Trend discovery | Live provider result, stored provenance, bounded cadence, no stale fallback | PARTIAL; cookie-backed Google Trends Explore/widget retrieval and official RSS fallback are implemented, but the latest live cycle was `QUERY_EMPTY` because Explore was rate-limited and RSS had no relevant crypto/Web3 lead. The bounded, freshness-filtered Google News RSS path supplied 25 provenance-backed research leads (not trend volume or ROI evidence). X discovery remains disabled until authorized API access/credits are available |
| Operator approval | SMTP/IMAP configured, token-bound email delivered, `SITEYE_EKLE` reply creates a one-time candidate | PARTIAL/CODE COMPLETE; when SMTP is disabled, token-bound unsent `.eml` drafts are written to the ignored local outbox, but real SMTP delivery and IMAP reply processing are not yet configured or exercised |
| Evidence enrichment | Official identity, participation, reward, and exit evidence stored per candidate | CODE COMPLETE; approved research candidates now have an operator-reviewed HTTPS evidence enrichment path that promotes GUIDE_ONLY, carries verified facts into content guidance, retires the research-only card, and keeps ROI unavailable when economic evidence is missing; no live candidate has been enriched yet |
| ROI integrity | Reproducible inputs, explicit unavailable state, freshness/risk/confidence shown | ENGINE COMPLETE; new candidates remain ROI-unavailable until verified |
| Content quality | Representative frame QA, approved product visual, approved narration, checksum-bound human approval | FAIL-CLOSED; 11 Shorts are queued and pending human review. No queued item has a policy-qualified approval. One older uploaded item is tagged approved despite music-only audio; that does not meet the current ElevenLabs narration policy and is excluded from approval readiness. |
| X cadence | Two successful daily posts or explicit operational reason for zero, with live API evidence | INCOMPLETE; manual-ready drafts exist, but live publication evidence is absent. The latest recorded X API publish attempt returned credits depleted; GA4 currently attributes four last-28-day sessions to X/t.co, a small signal only. |
| YouTube cadence | One successful daily Short only after quality approval and cap check | INCOMPLETE; one upload is recorded for 2026-09-23, and the daily cap is consumed. The uploaded item is tagged music-only, which conflicts with the current narration policy; no further upload is permitted until the next local day and a compliant, reviewed item is available. |
| User growth | Search/indexability, X/YouTube distribution, referral attribution, and weekly cohort metrics | PARTIAL; GA4 last-28-day read returned 5 active users and 63 sessions, including 22 sessions explicitly tagged as manual tests; the remaining 41 sessions were 37 Direct and 4 organic-social. Search Console returned 128 impressions and 0 clicks. YouTube reported about 203 views and 0 subscriber gains across eight videos for the same window; several watch metrics are inconsistent, so use views directionally only. |
| Revenue | Verified referral, sponsor, YouTube, or advertising attribution reaches the target | NOT YET EVIDENCED; six official program leads remain `APPLICATION_REQUIRED`; no account-specific referral link or verified partner revenue is recorded in the database queried locally. Public production counters report aggregate redirect events, not verified human clicks, conversions, or revenue. |
| Reliability | Fresh heartbeat, external alerting, production-grade database backup, and recovery drill | INCOMPLETE; local doctor and database checks pass. The public DB endpoint responds `ok`, but its current Render plan, backup status, and restore evidence are not independently verified. A manual refresh restored 7/7 eligible strategies briefly; all 7 aged stale again after the five-minute observation window, while scheduled GitHub runs show multi-hour gaps. The local distribution task is `Ready`, not running; its last result was non-zero and the heartbeat exceeded 45 minutes. External alerting, production backup, and recovery drill remain open. |

## Operating metrics

Track weekly and rolling 28-day values for:

- discovery leads received, approval rate, evidence-verification rate, and time from lead to published candidate;
- X posts attempted/successful, impressions, profile visits, link clicks, and follower growth;
- YouTube Shorts uploaded, views, average retention, subscribers, and click-through to GamCryp;
- landing visits, outbound `/go` clicks, verified conversions, verified revenue, and revenue by channel;
- content rejection rate, stale-source rate, queue age, worker heartbeat age, and provider error duration.

The local read-only snapshot is available with `PYTHONPATH=backend .venv/Scripts/python.exe scripts/growth_metrics_report.py --public-status-url https://gamcryp.com`. Database-backed referral, click, conversion, and revenue details come from the database configured in the current environment and are not assumed to be production. The optional public ops status adds aggregate production event counts; those counts are not unique people or verified human clicks. The report marks a worker heartbeat stale after 45 minutes, matching `scripts/check_distribution_worker.ps1`.

After a real platform dashboard export exists, source-backed per-content metrics can be recorded with `PYTHONPATH=backend .venv/Scripts/python.exe scripts/import_content_performance.py --platform X|YOUTUBE ... --evidence-url https://...` (or `--evidence-reference`); the importer rejects unsupported periods, negative values, and records without evidence.

Do not count a configured referral URL, upload attempt, ambiguous upload, or unverified revenue record as a successful business result.

## Current release decision

The system is not ready to be called complete. The next release can be considered operationally ready only when the mailbox loop is exercised end to end, a candidate is enriched with official evidence, one Short passes the current creative contract without consuming credits before approval, two X posts are successfully published under the daily cap, and the resulting clicks/conversions are visible in the separated commercial analytics records.
