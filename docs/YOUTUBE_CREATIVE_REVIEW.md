# YouTube Short creative review packet

This packet is review-only. No item in the current queue is approved for
YouTube use, and the review process never generates ElevenLabs audio.

## Quick visual comparison

[Open the twelve-frame contact sheet](/C:/Projects/gamefi-roi/data/local/video_render/qa/youtube_short_review_contact_sheet_v7.png)

Review each full render after the contact sheet. Confirm that the product
visual is legible, the hook is understandable without audio, captions are not
clipped, and the claim matches the cited source. A green queue state is not a
human creative approval.

The renderer rotates among approved raster product captures deterministically
per package so different editorial angles do not all reuse the same screenshot.
The current v7 renderer makes the approved product capture the centre visual,
uses compact on-canvas labels, and adds deterministic crop/pan plus a
non-claiming scanline treatment. Static product captures fail the creative
gate.
Vector-only captures are excluded from video inputs because their ffmpeg
decoding is not portable; an approved PNG/JPEG/WebP capture is required.

## Current review items

All twelve items below are `queued`, `music_only`, and `creative_approval_state=pending_review`.

## Current visual decision — 2026-09-21

The v7 contact sheet passes the automated render/frame contract, but it is
not approved for publication. Human review remains **REJECTED_PENDING_REVISION**
for the current batch because:

- the evidence scene repeats a small, mostly static-looking capture and is not
  legible enough at Shorts/mobile scale;
- the capture, evidence ribbon, and caption region leave a large dead area,
  making the composition read like a PowerPoint slide rather than a social
  video;
- the six Filecoin/Golem angles are visually too similar to establish a
  strong hook or meaningful scene progression without audio.

Required before approval: produce a revised visual pass with a larger,
cropped product interaction, stronger scene-to-scene visual progression, and
less unused vertical space. Keep all items pending review until the revised
full renders and representative frames are checked. Do not call ElevenLabs or
upload to YouTube as part of this revision.

- [Filecoin storage provider Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-depin_setup-filecoin-storage-provider.mp4)
- [Golem provider setup Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-depin_setup-golem-provider.mp4)
- [Filecoin claim/exit Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-how_to_claim_or_exit-filecoin-storage-provider.mp4)
- [Golem claim/exit Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-how_to_claim_or_exit-golem-provider.mp4)
- [Filecoin how-to-start Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-how_to_start-filecoin-storage-provider.mp4)
- [Golem how-to-start Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-how_to_start-golem-provider.mp4)
- [Filecoin earnings-mechanism Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-how_you_earn-filecoin-storage-provider.mp4)
- [Golem earnings-mechanism Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-how_you_earn-golem-provider.mp4)
- [Filecoin requirements Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-what_you_need-filecoin-storage-provider.mp4)
- [Golem requirements Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-what_you_need-golem-provider.mp4)
- [Filecoin ROI-unavailable Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-why_roi_unavailable-filecoin-storage-provider.mp4)
- [Golem ROI-unavailable Short](/C:/Projects/gamefi-roi/data/local/video_render/short/package-short_form-why_roi_unavailable-golem-provider.mp4)

## Approving one item

Only after the full render passes human review, approve the exact current
checksum-bound video with:

```powershell
.\.venv\Scripts\python.exe -m app.publishing.short_youtube_handoff_cli approve PACKAGE_ID `
  --confirm-reviewed `
  --reviewed-by "operator" `
  --review-note "Full render, representative frames, captions, source claim, and product visual reviewed."
```

Approval alone does not publish. The YouTube worker still checks the checksum,
daily cap, source URL, and creative preflight immediately before any upload.
