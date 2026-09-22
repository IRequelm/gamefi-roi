# YouTube Short creative review packet

This packet is review-only. No item in the current queue is approved for
YouTube use, and the review process never generates ElevenLabs audio.

## Quick visual comparison

[Open the current Golem hook frame](/C:/Projects/gamefi-roi/data/local/video_render/qa/package-short_form-depin_setup-golem-provider/frame-01.png) · [Open the current Filecoin hook frame](/C:/Projects/gamefi-roi/data/local/video_render/qa/package-short_form-depin_setup-filecoin-storage-provider/frame-01.png)

Review each full render after the contact sheet. Confirm that the product
visual is legible, the hook is understandable without audio, captions are not
clipped, and the claim matches the cited source. A green queue state is not a
human creative approval.

The renderer prefers an official local video when one exists. If no official
video is available, it uses an approved raster product/game/site capture and
keeps the source attribution visible.
The current source-led renderer makes the approved official source capture or
video the centre visual,
uses compact on-canvas labels, and adds deterministic crop/pan plus a
non-claiming scanline treatment. Static product captures fail the creative
gate.
Vector-only captures are excluded from video inputs because their ffmpeg
decoding is not portable; an approved PNG/JPEG/WebP capture is required.

## Current review items

All twelve items below are `queued`, `music_only`, and `creative_approval_state=pending_review`.

## Current visual decision — 2026-09-21

The previous card-style render passed the automated render/frame contract, but
was not approved for publication. The source-led revision has now been rendered for all twelve
queued Shorts and remains **PENDING_HUMAN_REVIEW**:

- the product capture is larger and cropped for mobile readability;
- the evidence header now has enough height for its two-line copy;
- the source-bound motion rail makes the evidence treatment explicit without
  inventing a live metric or earnings claim.

Required before approval: review each full source-led render and its representative
frames for hook clarity, caption timing, claim/source alignment, and remaining
unused space. Keep all items pending review until a human records a
checksum-bound approval. Do not call ElevenLabs or upload to YouTube as part
of this review.

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
