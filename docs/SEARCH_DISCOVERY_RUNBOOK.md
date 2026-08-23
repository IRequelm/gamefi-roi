# Search / AI Discoverability Runbook

G16 makes the public beta crawlable and easier to cite without changing analytical outputs.

## Architecture

Public pages are server-rendered by the FastAPI monolith, then enhanced by the existing browser JavaScript.

Canonical public pages:

- `/`
- `/opportunities`
- `/opportunities/{opportunity_id}`
- `/strategies/{strategy_id}`
- `/games/{game_id}`
- `/rankings`
- `/rankings/under-25`
- `/rankings/high-confidence`
- `/rankings/gamefi`
- `/methodology`

Normal page requests read persisted API-service data only. They must not trigger adapters, live providers, recalculation, scoring, or blockchain/market-data calls.

## Configuration

Required or optional environment variables:

- `GAMEFI_PUBLIC_BASE_URL`: canonical HTTPS public origin in production, for example `https://gamefi-roi-web.onrender.com` or a future custom domain.
- `GAMEFI_INDEXNOW_KEY`: optional IndexNow key. Leave blank to disable IndexNow submission.
- `GAMEFI_GOOGLE_SITE_VERIFICATION`: optional Google Search Console verification token.
- `GAMEFI_BING_SITE_VERIFICATION`: optional Bing Webmaster Tools verification token.

Do not commit provider keys, site verification secrets, or partner credentials.

## Metadata Policy

Every canonical public page must include:

- page-specific title,
- meta description,
- canonical URL,
- robots directive,
- Open Graph metadata,
- Twitter metadata,
- truthful JSON-LD.

JSON-LD is limited to `Organization`, `WebSite`, `WebPage`, and `BreadcrumbList`. Do not use product, offer, review, FAQ, or rating schemas unless a future gate adds evidence and compliance controls for them.

SEO copy must not promise returns, imply investment advice, or present unavailable ROI as zero.

## Robots Policy

`/robots.txt` allows public content and disallows:

- `/api/`,
- `/go/`,
- `/admin/`,
- `/internal/`,
- `/debug/`,
- `/test/`,
- query traps.

The policy intentionally does not block Googlebot, Bingbot, OAI-SearchBot, or PerplexityBot.

OpenAI crawler reference:

- `OAI-SearchBot` is for ChatGPT search discovery.
- `GPTBot` is for training-related crawling.
- `ChatGPT-User` is user-triggered and is not the search indexing control.

Source: https://developers.openai.com/api/docs/bots

If the project later decides to opt out of model-training crawling while staying visible in ChatGPT search, update `robots.txt` with an explicit GPTBot policy and keep OAI-SearchBot allowed.

## Sitemap

`/sitemap.xml` contains absolute canonical URLs derived from `GAMEFI_PUBLIC_BASE_URL`.

The sitemap must exclude:

- `/api`,
- `/go`,
- assets,
- query URLs,
- admin/internal/debug/test paths,
- arbitrary filter permutations.

Last modified dates should come from latest stored snapshots where available, or from catalog review timestamps for non-modeled opportunity pages.

`/go/{destination_slug}` redirects also return `X-Robots-Tag: noindex, nofollow`.

## IndexNow

IndexNow is optional and operator-triggered.

Source: https://www.indexnow.org/documentation

Requirements:

- configure `GAMEFI_INDEXNOW_KEY`,
- verify that `https://your-host/{GAMEFI_INDEXNOW_KEY}.txt` returns exactly the key,
- submit only canonical public URLs on the configured host,
- never submit `/api`, `/go`, query permutations, wrong-host URLs, or private/test URLs,
- do not submit from normal page requests,
- use bounded retries and tolerate submission failure without affecting the web app.

Manual command examples:

```bash
python -m app.search.indexnow_cli --all
python -m app.search.indexnow_cli --url https://example.com/rankings
python -m app.search.indexnow_cli --changed-file changed_urls.txt
```

Run the command from the backend environment with production settings.

## Acquisition Attribution

Inbound acquisition tracking is privacy-minimal:

- landing path,
- referrer domain,
- `utm_source`,
- `utm_medium`,
- `utm_campaign`,
- normalized channel,
- timestamp,
- optional coarse session id if already supplied.

No cookies, fingerprinting, raw IP storage, wallet identifiers, or user-level tracking are introduced in G16.

Normalized channels:

- `google`,
- `bing`,
- `chatgpt`,
- `perplexity`,
- `x`,
- `reddit`,
- `direct`,
- `referral`,
- `other`.

Inbound acquisition records are separate from G15 outbound clicks, revenue attribution, sponsored placements, and partner reporting. They must never affect ROI, Risk, Confidence, historical snapshots, or organic ranking order.

## Verification

Before marking G16 complete:

- server-rendered pages contain meaningful HTML before JavaScript runs,
- public links are crawlable `<a href>` links,
- metadata and canonical URLs are page-specific,
- query pages are `noindex,follow`,
- sitemap XML parses and excludes private/query URLs,
- robots policy disallows private routes and does not block target search/AI bots,
- JSON-LD parses and uses truthful schema types,
- IndexNow host/key validation, failure isolation, and key redaction tests pass,
- inbound attribution tests pass,
- ROI/risk/confidence/ranking integrity tests pass,
- backend tests, frontend tests, doctor, compileall, pip check, API probe, web probe, and `git diff --check` pass.
