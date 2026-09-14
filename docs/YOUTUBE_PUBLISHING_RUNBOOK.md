# GamCryp YouTube API Publishing Runbook

Updated: 2026-09-15
Status: autonomous YouTube publishing uses the quality-gated Short handoff; live publication remains fail-closed when the cap, assets, narration, or worker health are not valid

## Purpose

GamCryp uses the official YouTube Data API v3 for operator-controlled video uploads, metadata, thumbnails, and verification. Publishing consumes validated Content Pack Lite data. It does not calculate financial values or alter ROI, ranking, risk, confidence, referrals, analytics, snapshots, or publication readiness.

The operator CLI remains available for review and one-off operations. Browser automation is not a publishing dependency. The autonomous worker does not publish from the legacy Content Pack queue; that queue is reserved for explicit operator/CLI use.

## Autonomous local distribution

The Windows distribution worker may load the ignored local `.env` and run in live mode after validation. The legacy learning-batch refill is optional and is disabled in the current local production configuration; autonomous YouTube uses only the Short handoff. Short refill is bounded to one render per worker cycle by `GAMEFI_SHORT_YOUTUBE_REFILL_BATCH=1`, while the handoff target remains capped at 14 items. This keeps heavy rendering bounded and prevents a stale-looking heartbeat caused by a burst of concurrent renders.

Refill uses the existing snapshot/opportunity API facts and `build_learning_batch` policy. Stale, invalid, unsupported, or non-refreshable financial facts remain RED; points-only or high-risk content remains YELLOW under the existing rules. A GREEN YouTube package without a matching rendered asset is held in the queue's `pending_asset` collection and is not publishable. X queue generation may continue while X publication remains fail-closed when credentials are unavailable.

The runner explicitly changes to the repository root before loading the worker, so relative state paths remain stable under Task Scheduler. The worker's append-only transcript is `data/local/distribution/worker.log`; cooldown, refill, lock, and heartbeat state are under `data/local/distribution/`. `data/local/distribution/worker.lock` is held for the worker lifetime, so a Task Scheduler restart cannot create competing workers. The atomic liveness record is `data/local/distribution/worker_heartbeat.json`; its `updated_at` must be recent and its status must be `ok` before treating unattended distribution as healthy. Set `GAMEFI_DISTRIBUTION_LIVE=false` and disable the scheduled task before stopping autonomous publishing.

Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_distribution_worker.ps1` from the repository root to fail closed when the heartbeat is missing, failed, invalid, or older than 45 minutes. Monitoring may treat any non-zero exit code as an alert.

The short-form handoff forward buffer is intentionally bounded at 14 queued GREEN renders (normally 7–14 in steady state) to avoid unnecessary render churn. New autonomous Shorts use an explicit no-TTS policy; the one successful public Short per local calendar day cap is unchanged.

## Architecture

- `backend/app/distribution/youtube_queue.py`: deterministic queue generation from canonical Content Packs.
- `backend/app/publishing/youtube_distribution.py`: GREEN/YELLOW/RED gates, exact creative approval, asset checksums, and queue-to-manifest conversion.
- `backend/app/publishing/youtube.py`: OAuth, YouTube Data API transport, upload/thumbnail operations, and duplicate state.
- `backend/app/publishing/youtube_cli.py`: operator-only CLI.
- `distribution/publish_queue/youtube_publish_queue.json`: committed queue derived from the current accepted Content Pack artifact.
- `data/local/youtube/`: ignored private OAuth, approval, and upload state.

The operator path is:

```text
canonical Content Pack
-> YouTube queue
-> readiness gate
-> rendered asset checksum
-> YELLOW approval when required
-> dry-run
-> explicit private upload
```

## Short-form visual quality gate

Short-form renders use the `short-motion-card-v3` visual contract and the `no-tts-motion-v4` autonomous policy. A GREEN/`RENDER_READY` Short must contain at least five meaningful scenes; the factory currently emits six: hook, identity, setup/mechanics, evidence, status, and CTA. Scene diversity and transitions are recorded in render metadata, and changing subtitle text alone cannot satisfy the gate.

Each Short must also contain a non-caption visual element in every planned beat, an early opportunity identity, and a mobile-safe caption area. Official local logos are used when catalog metadata points to a present asset. Missing logos use a branded GamCryp identity card; fabricated logos, hotlinked images, and gameplay screenshots are not allowed. GUIDE_ONLY and ROI-unavailable content remains subject to the existing evidence restrictions.

The render metadata records the quality version, scene count/diversity, non-caption visual-element count, identity mode, caption safe area, evidence-point count, product-visual provenance, animated-motion proof, transition effects, and audio provenance. Any missing or invalid quality metadata makes the Short `NOT_READY` and prevents queue eligibility. A slide-deck/static composition or TTS narration is not eligible for autonomous publication.

Direct free-form manifests are not an operator CLI input. This prevents a manually authored manifest from bypassing current distribution readiness.

## Current Official API Requirements

The publisher uses YouTube Data API v3:

- `videos.insert` for resumable upload: https://developers.google.com/youtube/v3/docs/videos/insert
- `videos.update` for metadata: https://developers.google.com/youtube/v3/docs/videos/update
- `videos.list` for verification.
- `thumbnails.set` for custom thumbnails: https://developers.google.com/youtube/v3/docs/thumbnails/set

OAuth uses Google's installed desktop application flow with a loopback callback. Service accounts cannot upload to a YouTube channel. The configured scope is:

```text
https://www.googleapis.com/auth/youtube.force-ssl
```

This scope is required because the retained publisher supports upload, thumbnail management, status reads, and metadata updates. The narrower `youtube.upload` scope supports upload and thumbnails but does not support the retained `videos.update` metadata capability.

Google currently documents a separate Video Uploads quota bucket and a default allowance that may change. Check the Cloud Console quota page before live operation. API projects created after July 28, 2020 that have not completed Google's required audit may have uploads restricted to private visibility. GamCryp's queue-generated upload manifest is private by default.

## Environment Variables

```text
GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE=data/local/youtube/client_secret.json
GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE=data/local/youtube/token.json
GAMEFI_YOUTUBE_PUBLISH_STATE_FILE=data/local/youtube/publish_state.json
GAMEFI_YOUTUBE_APPROVAL_FILE=data/local/youtube/approvals.json
GAMEFI_YOUTUBE_CONTENT_PACK_FILE=distribution/content_packs/learning_batch_001.json
GAMEFI_YOUTUBE_QUEUE_FILE=distribution/publish_queue/youtube_publish_queue.json
GAMEFI_YOUTUBE_CHANNEL_HANDLE=@GamCryp
GAMEFI_YOUTUBE_MAX_RETRIES=2
```

## Audio policy

ElevenLabs generation remains a separate legacy/manual production capability, but it is not used by the autonomous Short path. Configure the local ignored `.env` only when an operator explicitly needs that legacy command; the no-TTS policy prevents the resulting neural audio from entering a new autonomous upload.

Generate or validate one narration asset without publishing anything:

```powershell
video-narration generate CONTENT_ID --dry-run
video-narration generate CONTENT_ID
```

Assets use `CONTENT_ID` plus a script fingerprint and are stored beside checksum-bound JSON metadata. Matching audio is reused. Changing the script, voice, or model produces a new asset. The metadata records `narration_mode=neural_voice`, `voice_provider=elevenlabs`, voice/model identifiers, the exact spoken text, timestamp, checksum, and quality status.

GREEN video publication still requires the validated package, approved product-specific visual evidence, a valid rendered video, meaningful motion, and post-render frame QA. A provider error never falls back to Windows/system voices, pyttsx, generic TTS, or another neural provider. Short-form rendering uses a local instrumental bed when no approved non-TTS audio exists; captions remain on-screen guidance rather than pretending that text was spoken. Existing ElevenLabs assets are retained for audit/recovery, but a new autonomous Short with `neural_voice` is blocked by `TTS narration is forbidden for autonomous Shorts`.

Never paste or commit the OAuth client JSON, access token, refresh token, browser cookies, or authorization headers. Do not place secrets in Content Packs or queue files.

## Queue Policy

- `GREEN`: may proceed when its rendered video exists and all package/asset validation passes.
- `YELLOW`: requires explicit human creative approval bound to the exact package checksum, video checksum, and optional thumbnail checksum.
- `RED`: cannot be approved or uploaded.

Changing the Content Pack, title, description, script, attribution URL, source snapshot, rendered video, or thumbnail invalidates a prior YELLOW approval. Referral availability does not influence readiness or approval.

The queue records title, final description, script, attribution URL, snapshot/provenance references, refreshability, asset state, approval state, package checksum, and upload state. Actual rendered videos and thumbnails are not committed.

## Queue And Preview

Rebuild only from the canonical accepted Content Pack artifact:

```powershell
youtube-publisher rebuild-queue
youtube-publisher queue
youtube-publisher preview CONTENT_ID
youtube-publisher preview CONTENT_ID --video C:\private\short.mp4 --thumbnail C:\private\thumb.png
```

Preview does not call YouTube.

## Human Approval

YELLOW approval requires the exact rendered asset:

```powershell
youtube-publisher approve CONTENT_ID --video C:\private\short.mp4 --thumbnail C:\private\thumb.png
youtube-publisher revoke CONTENT_ID
```

RED approval fails. GREEN does not use a YELLOW approval record.

## One-Time Google Setup

Human action required:

1. Open Google Cloud Console with the account that owns or manages `@GamCryp`.
2. Select or create the GamCryp Cloud project.
3. Enable YouTube Data API v3.
4. Configure the OAuth consent screen and required test/production users.
5. Create an OAuth client ID for a Desktop application.
6. Download the client JSON privately to `data/local/youtube/client_secret.json`, or configure another ignored private path.
7. Do not paste the file into chat and do not commit it.

Authorize only after the merged code and queue are approved:

```powershell
youtube-publisher status
youtube-publisher authorize
```

The local browser consent flow stores a refreshable token at the configured ignored token path.

## Dry-Run And Upload

Dry-run validates the queue, approval, exact assets, metadata, and duplicate state without making a YouTube API call:

```powershell
youtube-publisher dry-run CONTENT_ID --video C:\private\short.mp4 --thumbnail C:\private\thumb.png
```

An actual upload requires a second explicit flag and remains private:

```powershell
youtube-publisher upload CONTENT_ID --video C:\private\short.mp4 --thumbnail C:\private\thumb.png --confirm-publish
```

No upload should be attempted until OAuth is complete, the queue item is eligible, the final creative has been reviewed, and dry-run passes.

## Thumbnail, Metadata, And Verification

```powershell
youtube-publisher thumbnail --video-id VIDEO_ID --image C:\private\thumb.png --dry-run
youtube-publisher thumbnail --video-id VIDEO_ID --image C:\private\thumb.png
youtube-publisher verify --video-id VIDEO_ID
youtube-publisher verify --video-id VIDEO_ID --thumbnail
youtube-publisher metadata --video-id VIDEO_ID --title "Updated title" --confirm-update
```

These commands operate only on an explicitly supplied video ID. They are not scheduled. Unattended publication uses only the quality-gated Short handoff, never the legacy queue.

## Duplicate And Failure Safety

The local ignored publish state is keyed by `content_id` and video checksum:

- same content ID and same successful video checksum: skip duplicate upload;
- same content ID and changed video checksum: fail closed;
- changed YELLOW package or asset: require new approval;
- API error: do not record a successful upload;
- missing or malformed queue, provenance, asset, or approval: fail closed.

If an upload outcome is uncertain, inspect the channel and local state before issuing another upload. Never blindly retry by changing `content_id`.

Run reconciliation after an interrupted upload or recovery:

```powershell
python -m app.publishing.youtube_cli reconcile-state
```

The command reads the authenticated channel. A local `uploaded` record whose video is absent/inaccessible, or a Short-handoff `uploaded` item without a verified local publication record, becomes `ambiguous`. It is retained and blocked from retry; it is never silently re-uploaded or deleted.

## Narration reuse and recovery

Visual-only rebuilds search approved local narration metadata by content id, exact normalized spoken script, approved voice/model, and SHA-256 audio checksum. A matching asset is never regenerated automatically. Under the current no-TTS publication policy, an existing neural asset is retained for audit but the rebuilt Short must use the non-TTS path before it can enter the autonomous handoff. Changed spoken text or invalid metadata produces `BLOCKED_NARRATION`, preserving the existing asset and requiring an explicit operator decision.

`python -m app.video_render.recovery_cli` performs an Akash legacy-audio recovery render without publishing or paid narration. Current creative and frame QA still apply; an old generic spoken hook may correctly remain `BLOCKED_VISUAL_QA`.

## Safe Disable

To temporarily stop autonomous publishing, update the ignored local `.env` and disable the scheduled task:

```powershell
$envPath = 'C:\Projects\gamefi-roi\.env'
(Get-Content $envPath) -replace '^GAMEFI_DISTRIBUTION_LIVE=.*$', 'GAMEFI_DISTRIBUTION_LIVE=false' | Set-Content $envPath -Encoding UTF8
Stop-ScheduledTask -TaskName 'GamCryp Distribution Worker' -ErrorAction SilentlyContinue
Disable-ScheduledTask -TaskName 'GamCryp Distribution Worker'
```

To re-enable unattended operation without changing the one-public-Short-per-local-day cap:

```powershell
$envPath = 'C:\Projects\gamefi-roi\.env'
(Get-Content $envPath) -replace '^GAMEFI_DISTRIBUTION_LIVE=.*$', 'GAMEFI_DISTRIBUTION_LIVE=true' | Set-Content $envPath -Encoding UTF8
Enable-ScheduledTask -TaskName 'GamCryp Distribution Worker'
Start-ScheduledTask -TaskName 'GamCryp Distribution Worker'
```

Check the worker with:

```powershell
Get-ScheduledTask -TaskName 'GamCryp Distribution Worker' | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName 'GamCryp Distribution Worker' | Select-Object LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns
Get-Content 'C:\Projects\gamefi-roi\data\local\distribution\worker.log' -Tail 40
```

The task is registered with an at-logon trigger and a 30-minute worker interval. It loads the ignored `.env` at startup, keeps OAuth and upload state under `data/local/youtube/`, and remains fail-closed when X credentials are unavailable. Do not run `youtube-publisher authorize` or `youtube-publisher upload` as part of unattended operation.
