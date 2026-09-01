# GamCryp X Publishing Runbook

Updated: 2026-09-01
Status: code and dry-run workflow ready; OAuth and live publishing not authorized

## Purpose

GamCryp publishes to `@GamCryp` only through an operator-controlled, API-first workflow:

`validated content pack -> X queue -> safety validation -> approval -> explicit publish command`

The publisher consumes existing Content Pack Lite facts. It does not calculate ROI, alter rankings, refresh snapshots, or change risk/confidence. Browser automation is not the primary publisher and is not a dependency.

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
```

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

- `GREEN`: enters the publishable queue, but still requires the explicit `publish ... --confirm-publish` operator action.
- `YELLOW`: enters `awaiting_human_approval`. It cannot publish until `approve` stores an approval for the exact source and final-copy checksums.
- `RED`: appears only in blocked inventory. Approval and publishing both fail.

Referral availability never changes these states.

## YELLOW approval

Review the generated report, then place an edited final Post in a plain UTF-8 file when changes are needed:

```powershell
x-publisher approve CONTENT_ID --copy-file C:/private/reviewed-copy.txt
x-publisher preview CONTENT_ID
x-publisher revoke CONTENT_ID
```

Approval fails when the copy is too long, stale, unsupported, missing attribution, or otherwise invalid. Approval binds to the exact source content checksum and approved-copy checksum. Regeneration or any source/copy/URL/snapshot change invalidates the approval and requires another review.

## Actual publishing

Only after a clean preview and explicit founder instruction:

```powershell
x-publisher publish CONTENT_ID --confirm-publish
```

There is no active scheduler. `publish-next` exists for a later operator-controlled cadence, but it has the same explicit confirmation and validation requirements. YELLOW is never auto-approved; RED is never publishable.

## Duplicate and failure recovery

- Same `content_id` and checksum already published: blocked before any API request.
- Changed YELLOW content: prior approval invalidates.
- A definite API error records `failed`, never `published`.
- A timeout, network loss after send, server error, or response without a Post ID records `ambiguous`.
- An ambiguous content ID is blocked from retries until the operator manually checks `@GamCryp` and reconciles the state. Do not retry blindly.
- Local publication state retains successful Post IDs; no delete operation is automated.

## Safely disabling publishing

There is no cron to disable. Remove access to the local token file, revoke the app authorization in X, or remove the app's pay-per-use credits. Do not delete publication history until any ambiguous attempt is reconciled.

## Deferred work

- Media upload and long-form video are not part of this text-post MVP.
- Thread/reply support is parked. Single-Post publishing is sufficient.
- Automatic scheduling is not active. A future scheduler may consume GREEN only, must remain duplicate-safe, and must stop on auth or validation failure.
