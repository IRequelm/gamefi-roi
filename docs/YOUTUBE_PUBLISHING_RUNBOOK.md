# GamCryp YouTube API Publishing Runbook

Updated: 2026-09-01
Status: queue and publisher ready for review; OAuth and live upload not performed

## Purpose

GamCryp uses the official YouTube Data API v3 for operator-controlled video uploads, metadata, thumbnails, and verification. Publishing consumes validated Content Pack Lite data. It does not calculate financial values or alter ROI, ranking, risk, confidence, referrals, analytics, snapshots, or publication readiness.

No scheduler is active. Browser automation is not a publishing dependency.

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

These commands operate only on an explicitly supplied video ID. They are not scheduled.

## Duplicate And Failure Safety

The local ignored publish state is keyed by `content_id` and video checksum:

- same content ID and same successful video checksum: skip duplicate upload;
- same content ID and changed video checksum: fail closed;
- changed YELLOW package or asset: require new approval;
- API error: do not record a successful upload;
- missing or malformed queue, provenance, asset, or approval: fail closed.

If an upload outcome is uncertain, inspect the channel and local state before issuing another upload. Never blindly retry by changing `content_id`.

## Safe Disable

Do not run `youtube-publisher authorize` or `youtube-publisher upload`. Removing the private token path or revoking the app in the Google Account also prevents authenticated publishing. No public application request and no active scheduler invoke this publisher.
