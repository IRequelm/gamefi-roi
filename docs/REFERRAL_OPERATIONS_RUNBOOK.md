# GamCryp Referral Operations Runbook

Updated: 2026-09-21
Gate: G17 - Referral Operations + Operator Console

## Scope

This runbook covers the internal referral operations workflow for the existing Opportunity catalog.

Referral operations may manage:

- official outbound URLs,
- referral URLs,
- referral codes/templates,
- affiliate program metadata,
- referral coverage tasks,
- manual partner-verified conversion/revenue records.

Referral operations must never change:

- ROI calculations,
- risk/confidence scores,
- strategy snapshots,
- validation results,
- organic ranking order,
- adapter inputs,
- source observations.

## Access

Operator console:

```text
/operator/referrals
/operator/revenue
```

Required environment variables:

```text
GAMEFI_OPERATOR_USERNAME
GAMEFI_OPERATOR_PASSWORD
GAMEFI_REFERRAL_REVERIFY_DAYS=30
GAMEFI_REFERRAL_PENDING_RECHECK_DAYS=14
```

There is no default password. If either credential is missing, operator routes fail closed with `503`.

Do not paste operator credentials, referral partner dashboards, settlement reports, database URLs, provider keys, or private partner terms into chat or commit them to Git.

## Coverage States

`REFERRAL_ACTIVE`

Reviewed referral link is safe, current, and usable by `/go`.

`REFERRAL_PENDING`

Application or partner approval is pending. `/go` uses official URL fallback.

`REFERRAL_MISSING`

No referral metadata exists yet. Create a research task.

`REFERRAL_RESEARCH_REQUIRED`

Operator must research or apply before any referral can be used.

`NO_PROGRAM_FOUND`

Operator found evidence that no affiliate/referral program currently exists.

`REFERRAL_EXPIRED`

Stored program/link has expired. `/go` uses official URL fallback.

`REFERRAL_PAUSED`

Program/link is intentionally paused. `/go` uses official URL fallback.

`REFERRAL_REVERIFY`

Stored active program/link is old enough to require periodic re-verification.

## Work Queue

Run the stored-metadata health check from:

```text
/operator/referrals
```

The health check creates or updates open tasks and does not call live providers or partner dashboards.

Task types:

- `FIND_REFERRAL_PROGRAM`,
- `APPLY_TO_PROGRAM`,
- `VERIFY_REFERRAL_LINK`,
- `RECHECK_PENDING_APPLICATION`,
- `REVERIFY_PROGRAM`,
- `REPLACE_EXPIRED_LINK`.

The queue prevents duplicate open tasks for the same opportunity and task type.

## Adding Or Updating A Referral Link

1. Open `/operator/referrals`.
2. Select the opportunity.
3. Enter the reviewed official URL if the catalog URL needs an operational override.
4. Enter either:
   - a full referral URL, or
   - a referral URL template containing `{code}` plus a referral code.
5. Add affiliate program name/type.
6. Add commission or reward description when known.
7. Add eligibility and geographic restrictions when known.
8. Add evidence URL or evidence reference.
9. Set `verified_at` and `last_checked_at`.
10. Set `expires_at` when the program or link has an expiry.
11. Set status to `ACTIVE` only after validation evidence exists.

The system accepts only HTTPS outbound URLs. It rejects unsafe schemes, localhost/private-network destinations, and referral hosts that do not match the reviewed official-domain relationship.

If validation fails, the metadata is not activated. Public `/go/{destination_slug}` falls back to the official URL.

## Missing, Pending, Expired, And Paused Links

Use `REFERRAL_MISSING` when no work has been done.

Use `REFERRAL_RESEARCH_REQUIRED` when a program might exist but needs investigation.

Use `APPLICATION_REQUIRED` when an operator must apply before a link can exist.

Use `PENDING` after application while waiting for approval.

Use `NO_PROGRAM_FOUND` only when there is an evidence URL/reference or operator note explaining the conclusion.

Use `EXPIRED` when the link/program is past its valid date.

Use `PAUSED` when the link should not be used even though the program may exist.

In all non-active states, public outbound routing uses official URL fallback.

## Current Research Baseline

The local operator database currently records six official-program leads as
`APPLICATION_REQUIRED`: Acurast, DIMO, EarnApp, Grass, Honeygain, and
Splinterlands. These records contain official evidence only; none contains a
GamCryp referral code or active monetized link. The operator must apply or
obtain an account-specific code, verify the current terms and disclosure, and
then activate the link separately. Until that happens, `/go` continues to use
the reviewed official destination.

The corresponding official evidence pages are:

- Acurast: `https://acurast.com/ambassador-program/`
- DIMO: `https://support.drivedimo.com/en-US/sharing-your-referral-code-287684`
- EarnApp: `https://earnapp.com/referrals`
- Grass: `https://www.grass.io/learn/i-just-got-a-referral-to-grass-what-does-it-mean/`
- Honeygain: `https://www.honeygain.com/refer-a-friend/`
- Splinterlands: `https://support.splinterlands.com/hc/en-us/articles/8626548249748-Ambassador-Program-FAQ`

Do not copy a referral code from an invitation URL, infer a parameter, or
describe a program as active before the operator has verified the account-
specific link.

## Revenue Entry

Use `/operator/revenue` only for manual partner/operator records.

Records default to `PENDING`.

Only `VERIFIED` records count as verified revenue/conversion inputs for commercial reporting. A verified record requires settlement/reference ID or evidence reference.

Do not infer conversions or revenue from click counts. Clicks alone are traffic events, not revenue evidence.

## Search And Privacy

Operator pages are:

- protected by Basic Auth,
- `noindex,nofollow`,
- excluded from sitemap,
- disallowed by robots,
- not part of public OpenAPI docs.

The operator console does not set session cookies. `/go` click tracking remains privacy-minimal and does not require invasive personal tracking.

## Routine Checklist

Daily:

- check open referral tasks,
- verify expired or paused states have official URL fallback,
- confirm no failed URL validation is being ignored.

Weekly:

- run referral health check,
- review `REFERRAL_REVERIFY` tasks,
- verify active links still resolve to the expected destination,
- update partner notes/evidence.

Monthly:

- review `NO_PROGRAM_FOUND` evidence,
- reconcile verified revenue records against partner statements,
- confirm referral/revenue changes did not affect organic rankings.

## Integrity Check

After major referral metadata edits, run:

```bash
python -m pytest backend/tests/test_referral_operations.py backend/tests/test_monetization.py
python -m app.doctor
```

The expected result is that referral metadata may change `/go` target selection and commercial reporting only. ROI, Risk, Confidence, snapshots, validation, and organic ranking order must remain unchanged.
