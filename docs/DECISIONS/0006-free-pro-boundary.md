# Decision 0006 — Free/Pro Boundary Readiness

Date: 2026-08-23

## Status

Accepted for G15 planning only.

## Decision

G15 does not implement authentication, billing, entitlements, subscriptions, paywalls, account storage, or premium-only product surfaces.

The repository may document the future Free/Pro boundary so monetization choices made in G15 do not block later account work.

Future Free tier may include:

- public organic rankings,
- public opportunity pages,
- strategy detail pages,
- methodology/disclosure pages,
- first-party Start/Open redirects,
- clearly separated sponsored placements if enabled.

Future Pro tier may include:

- deeper history views,
- saved filters/watchlists,
- alerts,
- portfolio-level tracking,
- advanced exports/API access,
- additional configurable analysis tools.

## Integrity Boundary

Free/Pro access level, affiliate relationships, sponsor relationships, paid placements, campaign revenue, EPC, conversion rate, and partner status must never alter:

- ROI outputs,
- Risk score,
- Confidence score,
- adapter calculations,
- historical snapshots,
- validation results,
- organic ranking order.

Sponsored placements, if displayed, must be explicitly labeled and separated from organic ranking results.

## Rationale

The MVP is an analytical trust product. Account and premium packaging can add convenience, workflow depth, or access to larger historical surfaces, but cannot change what the model says about an opportunity.

Separating commercial analytics from strategy economics avoids a future rewrite when authentication/billing arrives and protects the core product promise.

## Consequences

- G15 adds commercial persistence and reporting foundations only.
- No auth or billing dependency is introduced.
- Commercial records live outside snapshot, score, observation, and ranking inputs.
- G16+ may build acquisition/account features on top of this boundary without modifying ROI core behavior.
