# GamCryp X Publishing Runbook

Updated: 2026-09-15
Status: official X API user-context path enabled locally; no browser automation

## Purpose

GamCryp prepares and publishes posts for `@GamCryp` through the authenticated local worker:

`validated content pack -> X enrichment -> X queue -> safety validation -> autonomous publish`

The publisher consumes existing Content Pack Lite facts. It does not calculate ROI, alter rankings, refresh snapshots, or change risk/confidence. X's rules prohibit non-API browser automation; all automated X actions use the official API and remain fail-closed.

Links are intentionally occasional: methodology/source posts and every third ordered post retain the tracked GamCryp URL; other posts keep the source URL in queue/outbox metadata without repeating it in visible copy. Enrichment adds only deterministic, bounded hashtags and an explicitly verified official handle. An absent handle is normal and never inferred.

## Enrichment and media

- `config/distribution/x_official_accounts.json` is the allowlist for official project handles. Every entry requires an explicit HTTPS official-source URL and `verified: true`; an empty registry is safe.
- Hashtags are derived from the project name and catalog category, capped at 13, and never enter ROI, risk, confidence, admission, or ranking calculations.
- X previews and manual-ready records carry media metadata. Selection is local-only: catalog official logo, approved local product asset under `data/local/video_assets`, then a deterministic GamCryp SVG card containing only content-pack facts. Missing external media never blocks a valid post and no arbitrary hotlink/screenshot is used.
- The verified handle remains metadata even when the source copy has no room under X's weighted 280-character limit; claims and the canonical source URL are not silently removed to make room.

## Live X discovery and amplification

`app.distribution.x_intelligence` queries the official recent-search endpoint for GameFi, DePIN, node-reward, points, and crypto-reward signals. It stores timestamps, source account, post URL, public metrics, and a transparent engagement score. Search failures (including depleted credits) are recorded as `BLOCKED`; the previous feed is not treated as live and cannot be retweeted.

Only accounts in `config/distribution/x_source_whitelist.json` with explicit verification, stable status URLs, fresh timestamps, direct catalog relevance, high engagement, and no unsafe/promotional language can become `REPOST_NOW`. Other relevant signals remain non-actionable; invalid, stale, untrusted, or irrelevant signals are ignored. The autonomous X path has no human-approval queue.

Actionable candidates are written to `distribution/manual_outbox/x_amplification_ready.json`, deduplicated by source account + source post ID + URL, with history in `distribution/manual_outbox/x_amplification_history.json`. In live mode and only when `GAMEFI_X_AMPLIFICATION_AUTO_REPOST=true`, the worker retweets `REPOST_NOW` candidates through `POST /2/users/:id/retweets` and records the source fingerprint and returned post id. Re-running the worker cannot retweet the same fingerprint twice. If the existing SMTP handoff is enabled, a bounded digest with subject `GamCryp X Amplification` is sent once per digest. Browser automation is never used.

`GAMEFI_X_AMPLIFICATION_AUTO_REPOST=false` remains the safe repository default. The local operator environment may enable it after X billing and whitelist review. Quote-post generation is not automated; X failures remain isolated from YouTube.

## Current official X API model

Verified against official X documentation on 2026-09-01:

- Create a Post: `POST https://api.x.com/2/tweets` ([official endpoint](https://docs.x.com/x-api/posts/create-post)).
- User authorization: OAuth 2.0 Authorization Code Flow with PKCE ([official guide](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code)).
- Required scopes: `tweet.read tweet.write users.read offline.access`.
- Text limit: 280 weighted characters; URLs count as 23 characters ([official counting rules](https://docs.x.com/fundamentals/counting-characters)).
- Rate limit documented for `POST /2/tweets`: 100 requests per user per 15 minutes and 10,000 per app per 24 hours ([official rate limits](https://docs.x.com/x-api/fundamentals/rate-limits)).
- Access uses pay-per-use credits. The official pricing page currently lists Content Create with a URL at USD 0.20 per request ([official pricing](https://docs.x.com/x-api/getting-started/pricing)). Prices and access rules can change; re-check the Developer Console before authorization or publishing.
- Spam and non-API browser automation are prohibited. Explicit consent and a preview of the exact Post are required ([official developer guidelines](https://docs.x.com/developer-guidelines), [developer policy](https://docs.x.com/developer-terms/policy)).

GamCryp does not purchase credits or authorize an account automatically.

GamCryp's dependency-free local counter follows the documented weighting ranges, NFC normalization, common emoji grapheme handling, and 23-character transformed URL rule. It preserves balanced URL brackets and query/fragment punctuation while counting terminal punctuation separately. Ambiguous, malformed, or unsupported URL-like text is conservatively over-counted; X remains the final validity authority.

## Files and state

Tracked, reviewable inputs:

- `distribution/content_packs/learning_batch_001.json`: authoritative distribution facts and editorial drafts.
- `distribution/publish_queue/next_publish_queue.json`: cross-channel editorial handoff.
- `distribution/publish_queue/x_publish_queue.json`: canonical normalized X execution queue.
- `distribution/publish_queue/x_yellow_approval_report.json`: compact current YELLOW review report.

Ignored local operator state:

- `data/local/x/approvals.json`: checksum-bound YELLOW approvals/revocations.
- `data/local/x/publications.json`: publishing attempts and successful Post IDs.
- `data/local/x/token.json`: OAuth access/refresh token.
- `data/local/x/oauth_pending.json`: short-lived PKCE verifier/state.
- `data/local/x/publish.lock`: overlap lock during one publish call.

Token and OAuth files must never be committed, pasted into chat, or printed in logs.

## Environment

```text
GAMEFI_X_CLIENT_ID=
GAMEFI_X_CLIENT_SECRET=
GAMEFI_X_REDIRECT_URI=http://127.0.0.1:8765/callback
GAMEFI_X_CONTENT_PACK_FILE=distribution/content_packs/learning_batch_001.json
GAMEFI_X_QUEUE_FILE=distribution/publish_queue/x_publish_queue.json
GAMEFI_X_TOKEN_FILE=data/local/x/token.json
GAMEFI_X_APPROVAL_FILE=data/local/x/approvals.json
GAMEFI_X_PUBLICATION_FILE=data/local/x/publications.json
GAMEFI_X_OAUTH_PENDING_FILE=data/local/x/oauth_pending.json
GAMEFI_X_PUBLISH_LOCK_FILE=data/local/x/publish.lock
GAMEFI_X_HTTP_TIMEOUT_SECONDS=20
GAMEFI_X_MAX_SNAPSHOT_AGE_SECONDS=1800
GAMEFI_X_PUBLISHING_MODE=manual
GAMEFI_X_AMPLIFICATION_AUTO_REPOST=false
GAMEFI_X_AMPLIFICATION_FEED_FILE=distribution/inbox/x_signal_feed.json
GAMEFI_X_AMPLIFICATION_WHITELIST_FILE=config/distribution/x_source_whitelist.json
GAMEFI_X_AMPLIFICATION_OUTBOX_FILE=distribution/manual_outbox/x_amplification_ready.json
GAMEFI_X_AMPLIFICATION_HISTORY_FILE=distribution/manual_outbox/x_amplification_history.json
GAMEFI_X_INTELLIGENCE_STATE_FILE=data/local/x/intelligence_state.json
GAMEFI_X_INTELLIGENCE_REFRESH_HOURS=6
GAMEFI_X_DISCOVERY_MAX_RESULTS=10
GAMEFI_X_DISCOVERY_MAX_FEED_ITEMS=50
GAMEFI_X_DISCOVERY_FRESHNESS_HOURS=48
GAMEFI_X_AMPLIFICATION_MIN_ENGAGEMENT=10
GAMEFI_X_DAILY_CAP_FILE=data/local/x/daily_cap.json
GAMEFI_X_DAILY_POST_CAP=1
GAMEFI_X_DAILY_RETWEET_CAP=2
GAMEFI_X_AMPLIFICATION_EMAIL_STATE_FILE=data/local/distribution/x_amplification_email_state.json
```

With `GAMEFI_X_PUBLISHING_MODE=manual`, the distribution worker never calls X. It writes one current GREEN/YELLOW manual-ready item to `distribution/manual_outbox/x_manual_ready.json`. The record contains the exact validated post text, source URL, prepared timestamp, content checksum, and `published: false`; RED items are excluded. Repeated worker cycles retain the current pending record. After the operator publishes that exact text manually, confirm it explicitly with:

```powershell
distribution-worker x-manual-confirm CONTENT_ID
```

The confirmation records the checksum as manually published for duplicate protection and marks the outbox item published. It does not claim that the X API published the post and never infers publication without the command.

Confirmed or duplicate content is never prepared again. A stale/blocked item is skipped so the worker can consider the next eligible X item; the daily brief reads only records whose `published` field is `false`.

If phone access is important, the same manual-ready item can optionally be delivered by SMTP email. Set `GAMEFI_X_MANUAL_EMAIL_ENABLED=true` and configure the recipient, sender, SMTP host, username, and app password in the ignored local `.env`. Gmail uses `smtp.gmail.com:587` with STARTTLS; use a mailbox app password, not the normal mailbox password. The worker records the last emailed checksum in `data/local/distribution/x_email_state.json`, so unchanged worker cycles do not send duplicates. Email failure is isolated from YouTube.

`GAMEFI_X_CLIENT_SECRET` is optional for a public/native PKCE client and required only when the Developer Console configures the app as confidential. Do not create or use an app until the founder accepts X's current pay-per-use terms and sets an explicit spending limit.

## One-time human setup

1. Sign in to the official X Developer Console with the human account authorized to manage `@GamCryp`.
2. Create or select the single GamCryp production app and describe the operator-approved publishing use case accurately.
3. Enable OAuth 2.0 with read/write user access.
4. Register the exact callback URI configured in `GAMEFI_X_REDIRECT_URI`.
5. Add sufficient pay-per-use credits and a conservative spending limit. This is a billing-sensitive human action.
6. Store the Client ID in the local environment. Store a Client Secret only if X issued one for a confidential client.
7. Run `x-publisher authorize-url`, open the returned official X URL, and approve the listed scopes as `@GamCryp`.
8. Copy the full callback URL from the local redirect and run `x-publisher authorize --callback-url "..."`.
9. Keep `data/local/x/token.json` private and outside Git.

Authorization does not publish content.

## Queue and preview

Regenerate the X queue from the validated content packs:

```powershell
x-publisher queue
x-publisher approval-report
x-publisher preview x-gamcryp-methodology-not-recommendation-20260831
x-publisher publish x-gamcryp-methodology-not-recommendation-20260831 --dry-run
```

Dry-run shows exact copy, weighted character count, checksum, snapshot reference, approval state, and blockers. It makes zero X API calls.

## GREEN / YELLOW / RED

- `GREEN`: enters the autonomous publishable queue after deterministic validation.
- `YELLOW`: also enters the autonomous publishable queue. It signals lower confidence, higher risk, or unavailable modeled return; the copy must still pass all provenance, freshness, attribution, length, and safety checks.
- `RED`: appears only in blocked inventory. Approval and publishing both fail.

Referral availability never changes these states.

## Legacy approval commands

The checksum-bound approval commands remain for explicit operator editing/backwards compatibility, but the autonomous X worker does not wait for them. It publishes GREEN/YELLOW content only after the same deterministic copy, provenance, freshness, attribution, length, and safety checks pass:

```powershell
x-publisher approve CONTENT_ID --copy-file C:/private/reviewed-copy.txt
x-publisher preview CONTENT_ID
x-publisher revoke CONTENT_ID
```

If used manually, the commands still reject copy that is too long, stale, unsupported, missing attribution, or otherwise invalid. Regeneration or any source/copy/URL/snapshot change invalidates a legacy approval record.

## Actual publishing

For a manual CLI override, use a clean preview and explicit operator instruction:

```powershell
x-publisher publish CONTENT_ID --confirm-publish
```

In live mode, the distribution worker publishes at most one eligible GREEN/YELLOW own post per UTC day and at most two whitelisted `REPOST_NOW` candidates per UTC day by default. `publish-next` remains explicit CLI-only. YELLOW is not held for human approval; RED is never publishable. A depleted X credit balance produces a visible `402` failure and cooldown; it is not converted to a successful publish. Intelligence refresh is cached for six hours by default so the 30-minute worker cadence does not cause unnecessary paid searches.

## Duplicate and failure recovery

- Same `content_id` and checksum already published: blocked before any API request.
- Changed YELLOW content: prior approval invalidates.
- A definite API error records `failed`, never `published`.
- A timeout, network loss after send, server error, or response without a Post ID records `ambiguous`.
- An ambiguous content ID is blocked from retries until the operator manually checks `@GamCryp` and reconciles the state. Do not retry blindly.
- Local publication state retains successful Post IDs; no delete operation is automated.

## Safely disabling publishing

Set `GAMEFI_X_PUBLISHING_MODE=disabled` or stop the Windows worker. Do not delete publication history until any ambiguous attempt is reconciled.

## Operator commands

```powershell
x-intelligence collect --json
x-intelligence status --json
distribution-worker --once --interval-seconds 1800
x-publisher status
```

`x-intelligence collect` is the only command that refreshes the live X discovery state. It never publishes. The worker performs publication only when `GAMEFI_DISTRIBUTION_LIVE=true` and `GAMEFI_X_PUBLISHING_MODE=live`; set both back to `false`/`disabled` for an emergency stop.

## Deferred work

- Media upload and long-form video are not part of this text-post MVP.
- Thread/reply support is parked. Single-Post publishing is sufficient.
- Google Trends, YouTube discovery, and other social sources are outside the X-only worker path. X search access remains dependent on current Developer Console credits and whitelisted official accounts.
