# GamCryp YouTube API Publishing Runbook

Updated: 2026-08-30
Status: infrastructure ready; no production videos published by this implementation

## Purpose

GamCryp uses the official YouTube Data API v3 for operator-controlled uploads, metadata updates, thumbnail setting, and verification. Browser Studio upload remains a fallback only when the API path is unavailable or Google account policy blocks automation.

This runbook covers infrastructure only. It does not authorize creating a new channel, changing existing public videos, or publishing a new video without an explicit operator-approved manifest and command.

## Architecture

Code location:

- `backend/app/publishing/youtube.py`: OAuth, manifest validation, duplicate protection, upload, thumbnail, metadata, status, verification, safe error redaction.
- `backend/app/publishing/youtube_cli.py`: operator CLI entry point, `youtube-publisher`.
- `data/local/youtube/`: recommended local secret/token/state directory. This path is ignored by Git.

Official API surfaces used:

- OAuth 2.0 installed-app flow for user consent and refreshable credentials.
- `videos.insert` for upload.
- `videos.update` for metadata, privacy, and scheduled publish metadata.
- `videos.list` for upload/processing/status verification.
- `thumbnails.set` and thumbnail response data for custom thumbnails.

The configured scope is `https://www.googleapis.com/auth/youtube.force-ssl`, the narrow single YouTube scope that supports the required upload, metadata, thumbnail, and status operations. Service accounts are not supported for YouTube channel uploads.

## Environment Variables

No secrets are committed. Configure paths and operator defaults through environment variables:

- `GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE=data/local/youtube/client_secret.json`
- `GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE=data/local/youtube/token.json`
- `GAMEFI_YOUTUBE_PUBLISH_STATE_FILE=data/local/youtube/publish_state.json`
- `GAMEFI_YOUTUBE_CHANNEL_HANDLE=@GamCryp`
- `GAMEFI_YOUTUBE_MAX_RETRIES=2`

The client secret JSON and token JSON must never be pasted into chat, committed to Git, printed in logs, or returned from API responses.

## One-Time Google Setup

Human action required from Zafer:

1. Open Google Cloud Console using the Google account that owns or manages the existing GamCryp YouTube channel.
2. Select or create the existing GamCryp Google Cloud project.
3. Enable YouTube Data API v3.
4. Configure the OAuth consent screen if Google requires it.
5. Create an OAuth client ID for an installed desktop application or loopback local-server flow.
6. Download the OAuth client JSON.
7. Store it locally at `data/local/youtube/client_secret.json`, or set `GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE` to the private path you choose.
8. Do not paste the JSON into chat. Do not commit it.

## First-Time Authorization

After the client secret file exists, run:

```powershell
youtube-publisher status
youtube-publisher authorize
```

The authorize command opens a local Google OAuth consent flow. Sign in as the existing GamCryp channel owner/manager account and approve the YouTube scope. A refreshable token is stored at `GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE`.

If authorization fails, do not fall back to password sharing or copied browser cookies. Fix the Google OAuth project, consent screen, account access, or channel permissions.

## Publish Manifest

Uploads are driven by a JSON manifest. Example shape:

```json
{
  "content_id": "gamcryp-example-2026-08-30",
  "video_path": "C:/path/to/video.mp4",
  "thumbnail_path": "C:/path/to/thumbnail.png",
  "title": "GamCryp Example Video",
  "description": "Operator-approved description.",
  "privacy": "private",
  "publish_at": "2026-09-01T16:00:00Z",
  "category_id": "22",
  "source_snapshot_id": "snapshot-id-if-applicable",
  "source_snapshot_timestamp": "2026-08-30T12:00:00Z"
}
```

Manifest rules:

- `content_id`, `video_path`, `title`, `description`, and `privacy` are required.
- `privacy` must be `private`, `unlisted`, or `public`.
- Scheduled `publish_at` requires `privacy: private`.
- Video files must be `.mp4`, `.mov`, `.m4v`, or `.webm`.
- Thumbnail files must be `.jpg`, `.jpeg`, or `.png` and at most 2 MB.
- Manifests must not contain credentials, refresh tokens, access tokens, API keys, cookies, or authorization headers.

## Safe Operator Flow

Always validate before mutating YouTube:

```powershell
youtube-publisher status
youtube-publisher dry-run --manifest C:/path/to/manifest.json
youtube-publisher upload --manifest C:/path/to/manifest.json --confirm-publish
youtube-publisher verify --video-id VIDEO_ID
```

Set or validate thumbnails separately:

```powershell
youtube-publisher thumbnail --video-id VIDEO_ID --image C:/path/to/thumbnail.png --dry-run
youtube-publisher thumbnail --video-id VIDEO_ID --image C:/path/to/thumbnail.png
youtube-publisher verify --video-id VIDEO_ID --thumbnail
```

Metadata updates also require explicit confirmation:

```powershell
youtube-publisher metadata --video-id VIDEO_ID --title "New title" --confirm-update
```

## Duplicate Protection

The publisher stores local publish records in `GAMEFI_YOUTUBE_PUBLISH_STATE_FILE` keyed by `content_id`.

Behavior:

- Reusing the same `content_id` with the same video checksum returns the existing uploaded video ID and does not upload again.
- Reusing the same `content_id` with a different video checksum fails closed.
- Re-running a command after an operator timeout is retry-safe when the same content ID and file are used.

The state file is not a secret, but it is local operational state and should not be committed.

## Error Handling And Logging

Operator-facing errors are structured and redacted. Secret-like keys, bearer tokens, OAuth tokens, client secrets, credentials, and API keys are scrubbed before display.

Provider/API errors should be handled by fixing the manifest, OAuth state, channel permissions, quota/rate limits, or Google API availability. Do not weaken validation to make an upload pass.

## Recovery

If upload succeeds but a later thumbnail or metadata operation fails:

1. Keep the returned YouTube video ID.
2. Re-run `youtube-publisher verify --video-id VIDEO_ID`.
3. Re-run only the failed operation.
4. Do not create a second upload unless the operator deliberately uses a new `content_id` and manifest.

If a mistaken video is uploaded, remove or correct it manually in YouTube Studio using the existing channel account. This runbook does not automate deletion of public videos.

## Production Safety

- Normal GamCryp API/web traffic must not upload to YouTube.
- The publishing CLI is an operator action, not a public endpoint.
- Tokens and client secrets live only in environment-managed private paths.
- No live YouTube API calls are made in automated tests.
- Browser Studio upload is fallback only after the API path is known to be blocked or unavailable.

## Current Human Blocker

The code is ready to run status and dry-run locally, but live upload readiness requires Zafer to complete Google Cloud OAuth setup and store the OAuth client JSON/token outside Git.