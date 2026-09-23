# GamCryp Operator V1 — LOCKED PLAN

Status: LOCKED
Date: 2026-09-23

## Mission

GamCryp must stop being a system that merely runs. Its operator must continuously work toward four outcomes:

1. attract qualified users,
2. help those users find genuinely useful Web3 earning opportunities,
3. increase qualified outbound/referral activity and monetization potential,
4. keep the product, catalog, distribution and automation healthy.

The public site already runs on Render. The Windows PC is the autonomous operator machine. If the PC is off, the site remains online. When the PC returns, the operator catches up from the last successful checkpoint.

## Hard architecture decisions

- No new control-center web app.
- No new domain.
- No migration of the site to a new cloud platform.
- No general-purpose custom AI army.
- GitHub remains the source of truth for code.
- Render remains the public production host.
- The Windows PC runs the GamCryp Operator while it is powered on.
- Existing discovery, distribution, video, X, YouTube, doctor/health, analytics, referral and content code must be reused before new code is introduced.
- The operator must be restart-safe and catch up after downtime.
- Scope expansion is forbidden until V1 acceptance. New feature ideas go to backlog.

## Operator responsibilities

### 1. Product/system health
Continuously inspect public site/API health, local worker state, queues, failures, stale data, repository/test status and known operational blockers. Automatically repair low-risk known failures when the remedy is deterministic and verifiable. Escalate only when owner action, credentials, payment, destructive data change or high-risk production change is required.

### 2. Opportunity discovery and catalog value
Run existing discovery/intelligence paths, find new qualified opportunities, deduplicate, preserve evidence, keep stale/broken catalog entries from accumulating and prioritize additions that can create useful user value. Never fabricate ROI or promote unsupported financial claims.

### 3. Distribution
Keep the existing content → render → YouTube/X pipeline supplied and healthy. Respect GREEN/YELLOW/RED, daily caps, evidence, narration and creative gates. Do not weaken safety/quality gates to increase volume.

### 4. Growth and acquisition
Use available GA4, Search Console, YouTube, X and first-party metrics to identify what is actually bringing qualified traffic. Separate test/manual/bot traffic from user growth. Prefer changes tied to evidence over generic growth advice.

### 5. Product/UX fit
Continuously ask whether a first-time user can quickly understand:
- what GamCryp does,
- which opportunity is relevant to them,
- what they need,
- what they may earn when measurable,
- what the risks are,
- how to start.

The operator must detect friction and produce evidence-backed recommendations such as:
“Changing X is likely to improve Y because Z.”
Recommendations should include evidence, expected impact, effort, confidence and risk.

Low-risk in-scope improvements such as copy clarity, information hierarchy, broken states, metadata/SEO, mobile readability and CTA wording may be executed automatically only when tests and rollback are available.
New product features, business-model changes, major redesigns or unbounded experiments must only be recommended and placed in backlog unless the owner explicitly approves them.

### 6. Monetization
Track outbound/referral coverage and qualified click/conversion signals where available. The operator should prioritize useful work that can plausibly move qualified outbound/referral activity, without allowing commercial metadata to contaminate ROI, risk, confidence or organic rankings.

### 7. Reporting
The operator itself produces the weekly report from its own action log and verified metrics. ChatGPT scheduled tasks are not the execution engine.

Weekly output should be short:
- what changed,
- traffic/growth,
- distribution performance,
- catalog/discovery progress,
- monetization/referral signals,
- fixes automatically completed,
- growth/product recommendations,
- “Müdahale gerekenler” only for owner-required decisions/actions.

## Decision loop

OBSERVE → DIAGNOSE → PRIORITIZE → ACT → VERIFY → LEARN → CHECKPOINT → REPEAT

Priority is based on mission impact, not task age alone.

## V1 phases

### Phase 1 — Operator core
Create one restart-safe local supervisor that:
- starts on Windows login,
- owns a single durable state/checkpoint,
- reads existing discovery/distribution/doctor/growth state,
- avoids double-running existing workers,
- performs a catch-up assessment after downtime,
- creates a prioritized action plan,
- records every attempted action and verified result,
- generates a read-only Growth/Product Recommendation section,
- does not yet add new product features or redesign the site.

Gate: restart test proves state recovery and one full observe→prioritize→act→verify→checkpoint cycle works.

### Phase 2 — Existing worker integration
Bring discovery, distribution, health and metrics under the supervisor without rewriting them. Remove duplicate scheduling only after the supervisor is proven.

Gate: one supervisor cycle can safely invoke/skip each existing subsystem and preserve current safety gates.

### Phase 3 — Growth/UX intelligence
Build a verified metrics snapshot and recommendation engine around current analytics and first-party events. Recommendations must be evidence-bound and prioritized by impact/effort/confidence/risk.

Gate: operator can identify at least one real funnel/UX issue and explain why it matters without inventing metrics.

### Phase 4 — Safe autonomous maintenance
Allow only reversible, low-risk, in-scope fixes with tests, Git evidence and rollback. Major UX/product changes remain recommendations.

Gate: operator detects, fixes, tests and verifies one real maintenance issue without owner intervention.

### Phase 5 — Weekly owner report
Generate the concise weekly report directly from operator state, actions and verified analytics.

Gate: report distinguishes completed autonomous actions from owner-required actions.

### Phase 6 — Acceptance
PC reboot → operator auto-starts → catches up → performs useful work → preserves site operation → logs actions → produces truthful report.

## Scope guard

Until V1 acceptance:
- no new dashboard,
- no new cloud migration,
- no new domain,
- no native app,
- no unrelated integrations,
- no visual redesign project,
- no new monetization product,
- no self-modifying architecture,
- no replacing working subsystems for elegance.

Any idea outside this plan goes to backlog.
