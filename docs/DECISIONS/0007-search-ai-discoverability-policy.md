# Decision 0007 — Search and AI Discoverability Policy

Status: Accepted for G16.

Date: 2026-08-23

## Context

The public beta originally behaved like a client-rendered application. That was acceptable for the G11 web MVP, but G16 requires public pages to be readable by search engines, AI search crawlers, social previews, and users without depending on JavaScript execution.

The project also needs acquisition measurement, but G15 already established a strict boundary: commercial and referral data must never affect ROI, Risk, Confidence, snapshots, validation, or organic rankings.

## Decision

GamCryp will render canonical public pages as meaningful server-side HTML from persisted read models, while keeping the existing frontend JavaScript as progressive enhancement.

Canonical discovery surfaces are limited to:

- `/`,
- `/opportunities`,
- `/opportunities/{opportunity_id}`,
- `/strategies/{strategy_id}`,
- `/games/{game_id}`,
- `/rankings`,
- curated `/rankings/{slug}` landing pages,
- `/methodology`.

The canonical host is configurable via `GAMEFI_PUBLIC_BASE_URL`. Application logic must not hard-code Render or any future platform URL.

Search metadata must remain truthful and source-constrained:

- no guaranteed return language,
- no fabricated financial ROI,
- unavailable ROI remains unavailable,
- no “Product”, “Review”, “Offer”, rating, or FAQ structured data without a future evidence/compliance gate,
- referral/sponsor/commercial data remains separate from organic analytical outputs.

`/robots.txt` will allow public content and disallow private or non-indexable surfaces including `/api`, `/go`, query traps, and internal/debug/test paths.

OAI-SearchBot is allowed for ChatGPT search discovery. GPTBot is documented separately as a training crawler. If the project later chooses to opt out of model-training crawling, it must add an explicit GPTBot rule without unintentionally blocking OAI-SearchBot.

IndexNow is operator-triggered only. Normal page requests must never submit IndexNow notifications. Submissions require a configured key, public root key verification file, canonical host validation, bounded retries, timeouts, and secret redaction.

Inbound acquisition attribution is privacy-minimal and stores only landing path, referrer domain, UTM source/medium/campaign, normalized channel, timestamp, and optional coarse session id already supplied by the client. It does not set cookies, fingerprint users, store raw IPs, or create affiliate revenue attribution.

## Consequences

- Search and AI crawlers can read core public content without executing the SPA.
- Social previews and canonical links become page-specific.
- Query/filter permutations are controlled with `noindex,follow` and curated landing pages, avoiding index bloat.
- `/go` redirects remain excluded from indexing and crawler discovery.
- Acquisition measurement can support traffic diagnostics without weakening product integrity.
- Future SEO/content growth must use the canonical inventory and truthful metadata rules instead of adding arbitrary indexed routes.

## External References

- OpenAI crawler documentation: https://developers.openai.com/api/docs/bots
- IndexNow documentation: https://www.indexnow.org/documentation
