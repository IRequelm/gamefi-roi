# Search Discovery Operator Checklist

Use this checklist after deploying a G16 build.

## Canonical Host

- Confirm the intended public host.
- Set `GAMEFI_PUBLIC_BASE_URL` to the exact HTTPS origin.
- Do not include a trailing slash, query string, or path.
- Confirm every page canonical uses that host.

## Search Console / Webmaster Tools

- Create or open Google Search Console property for the canonical host.
- Store the verification token in `GAMEFI_GOOGLE_SITE_VERIFICATION`.
- Create or open Bing Webmaster Tools property for the canonical host.
- Store the verification token in `GAMEFI_BING_SITE_VERIFICATION`.
- Do not paste verification tokens into chat.
- Do not commit verification tokens.

## IndexNow

- Generate an IndexNow key that is 8-128 characters using letters, numbers, or dashes.
- Store it as `GAMEFI_INDEXNOW_KEY` in the deployment secret environment.
- Verify `https://your-host/{GAMEFI_INDEXNOW_KEY}.txt` returns exactly the key.
- Run a manual IndexNow submission for the sitemap or changed canonical URLs.
- Do not submit `/api`, `/go`, query URLs, test URLs, or wrong-host URLs.
- Do not paste the IndexNow key into chat or commit it.

## Robots and Sitemap

- Open `/robots.txt`.
- Confirm `/api/`, `/go/`, query traps, and internal/debug/test paths are disallowed.
- Confirm public content is allowed.
- Confirm target crawlers are not blocked by a dedicated `Disallow: /` rule.
- Open `/sitemap.xml`.
- Confirm URLs are absolute canonical URLs on the intended host.
- Confirm there are no `/api`, `/go`, query, asset, test, or debug URLs.

## AI Search Policy

- Keep OAI-SearchBot allowed for ChatGPT search discovery unless the product strategy changes.
- Treat GPTBot separately from OAI-SearchBot.
- If opting out of model-training crawls later, document and test a specific GPTBot policy without blocking OAI-SearchBot.

## Public Page Checks

- Open `/`, `/rankings`, `/opportunities`, `/methodology`.
- Open at least one GAME, POINTS, and strategy detail page.
- Confirm pages show meaningful content before or without JavaScript.
- Confirm unavailable ROI appears as unavailable, never zero.
- Confirm referral/sponsor disclosures are visible where outbound CTAs exist.
- Confirm organic rankings remain unchanged by sponsored/referral metadata.

## Acquisition Data

- Visit a page with UTM tags such as `?utm_source=chatgpt.com&utm_medium=search&utm_campaign=launch`.
- Confirm a privacy-minimal inbound landing event is stored.
- Confirm no cookies, raw IP storage, fingerprinting, wallet identifiers, or personal tracking were added.
