# GamCryp Growth Operating Plan

Status: INCOMPLETE — implementation and live-service verification remain in progress.

Updated: 2026-09-21 (Europe/Istanbul)

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
| Content quality | Representative frame QA, approved product visual, approved narration, checksum-bound human approval | FAIL-CLOSED; twelve Shorts have v7 asset-led renders with music-only audio and no new ElevenLabs usage, and they pass automated media/frame QA, but visual review rejected the current batch pending a stronger mobile composition (larger/cropped product interaction, less dead space, and more scene progression). All remain pending explicit human checksum approval with reviewer acknowledgement; stale historical assets remain review-only |
| X cadence | Two successful daily posts or explicit operational reason for zero, with live API evidence | INCOMPLETE; OAuth refresh and `@GamCryp` identity verification succeed, manual mode prepares two improved GREEN posts, one historical manual publication is recorded, but live read/publish calls currently return a credits-depleted condition and live API publication evidence is absent |
| YouTube cadence | One successful daily Short only after quality approval and cap check | INCOMPLETE; twelve queued GREEN Shorts are prepared as a review buffer, but no item is human-approved for upload |
| User growth | Search/indexability, X/YouTube distribution, referral attribution, and weekly cohort metrics | PARTIAL; source-backed `content_performance_records` storage/import is ready, six official referral-program leads are recorded as `APPLICATION_REQUIRED`, but no real platform metrics have been imported yet |
| Revenue | Verified referral, sponsor, YouTube, or advertising attribution reaches the target | NOT YET EVIDENCED; no personal referral links are active and no verified clicks/conversions/revenue exist |
| Reliability | Fresh heartbeat, external alerting, production-grade database backup, and recovery drill | INCOMPLETE; local Docker Postgres, migrations through `20260921_0011`, doctor checks, and Task Scheduler heartbeat are verified, but the Render free PostgreSQL trial for `gamefi-roi-db` has expired and the database is suspended. The beta recalculation workflow is fail-closed and paused until a funded database is restored; external alerting, production backup, and recovery drill remain open |

## Operating metrics

Track weekly and rolling 28-day values for:

- discovery leads received, approval rate, evidence-verification rate, and time from lead to published candidate;
- X posts attempted/successful, impressions, profile visits, link clicks, and follower growth;
- YouTube Shorts uploaded, views, average retention, subscribers, and click-through to GamCryp;
- landing visits, outbound `/go` clicks, verified conversions, verified revenue, and revenue by channel;
- content rejection rate, stale-source rate, queue age, worker heartbeat age, and provider error duration.

The read-only live snapshot is available with `PYTHONPATH=backend .venv/Scripts/python.exe scripts/growth_metrics_report.py`; it combines inbound attribution, `/go` clicks, referral coverage/open tasks, verified revenue metrics, the X/YouTube safety queues, and the distribution-worker heartbeat/dead-letter state without publishing or generating audio.

After a real platform dashboard export exists, source-backed per-content metrics can be recorded with `PYTHONPATH=backend .venv/Scripts/python.exe scripts/import_content_performance.py --platform X|YOUTUBE ... --evidence-url https://...` (or `--evidence-reference`); the importer rejects unsupported periods, negative values, and records without evidence.

Do not count a configured referral URL, upload attempt, ambiguous upload, or unverified revenue record as a successful business result.

## Current release decision

The system is not ready to be called complete. The next release can be considered operationally ready only when the mailbox loop is exercised end to end, a candidate is enriched with official evidence, one Short passes the current creative contract without consuming credits before approval, two X posts are successfully published under the daily cap, and the resulting clicks/conversions are visible in the separated commercial analytics records.
