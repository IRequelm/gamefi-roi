# GamCryp Failover Bundle

This file is a portable read-only handoff snapshot for an AI worker that cannot access the repository directly.

IMPORTANT:
- Treat this bundle as context, not as permission.
- Do not expose secrets.
- Do not deploy, merge, create accounts or modify production unless explicitly authorized.
- If repository access becomes available, verify this bundle against the live repository before making changes.

Generated from the canonical files in ops/ai.

Health check command:
``powershell
powershell -ExecutionPolicy Bypass -File ops/ai/Test-FailoverHealth.ps1
``

Portable bundle regeneration command:
``powershell
powershell -ExecutionPolicy Bypass -File ops/ai/Update-FailoverBundle.ps1
``

---

# AGENT_RULES.md

# GamCryp AI Agent Rules

## Required Start

1. Read `CURRENT_STATE.md`, `WORK_QUEUE.md`, `HANDOFF.md`, `DECISIONS.md`, `ACCESS.md` and `WORKER_CAPABILITIES.md` before doing any work.
2. GitHub/repository is the operational source of truth.
3. Confirm the active branch/task is not being modified simultaneously by another worker.
4. Before every write task run:
   - `git status --short`
   - `git branch --show-current`
5. Preserve production behavior unless the active task explicitly requires a change.
6. Do not restart completed research or implementation. Continue from the latest checkpoint.

## Security

1. Never expose secrets, tokens, DSNs, passwords, cookies, API keys or private credentials.
2. Human approval is required for irreversible account, billing, legal, security, production-data or credential decisions.
3. Never create duplicate accounts, projects, organizations or resources without checking for an existing GamCryp resource first.

## Branch Ownership

1. One worker = one task = one branch.
2. Never let two workers mutate the same working tree concurrently.
3. If another worker/task owns the current branch, STOP.
4. Workers must create isolated task branches.
5. Emergency/free/cheap workers must not write directly to `master`.
6. No merge or deploy without explicit approval.
7. Default ops failover branch convention: `ops/<worker-or-purpose>/<task>`.

## Quota-Saver And Platform Blockers

1. API-first; browser automation is fallback only.
2. Browser/platform blocker budget: maximum 3 minutes.
3. Maximum retry policy: 1 normal attempt + 1 materially different fallback.
4. If still blocked, stop that path and record the exact human action required.
5. Pre-flight auth, permissions, verification, file upload support, secret access, and write access before substantive work.
6. Batch safe independent actions where possible.
7. Do not spend 20+ minutes on native file dialog, browser file chooser, or brittle platform automation battles.

## Failover

Canonical order is maintained in `WORKER_CAPABILITIES.md`:

1. Normal: OpenAI Work / Codex.
2. OpenAI quota/blocker: DeepSeek V3.2 / OpenRouter / OpenCode.
3. Secondary: Gemini CLI / Google API.
4. Tertiary: Nemotron 3 Ultra / OpenCode Zen.
5. If all fail: stop safely and report the exact blocker.

Quota exhaustion means shift change, not project halt.

## Completion

1. Test before merge or deploy.
2. Do not merge or deploy unless the active task explicitly authorizes it.
3. At the end of every meaningful task, update `CURRENT_STATE.md` and `HANDOFF.md` when the task changes operational state.
4. Regenerate `FAILOVER_BUNDLE.md` after changes to canonical failover files.

---

# CURRENT_STATE.md

# GamCryp Current State

## Production
Status: LIVE
Domain: gamcryp.com

Catalog:
- 32 opportunities
- 15 modeled strategies

Core systems currently expected to remain intact:
- ROI calculations
- Risk / confidence
- Rankings
- Snapshot generation
- Referral routing and official fallback
- GA4
- Search Console
- Operator referral panel

## AI Failover P0
Status: CLOSED / OPERATIONAL
Closed baseline date: 2026-08-30

Canonical failover order:
1. Normal: OpenAI Work / Codex.
2. Primary independent failover: DeepSeek V3.2 / OpenRouter / OpenCode.
3. Secondary independent failover: Gemini CLI / Google API.
4. Tertiary last resort: Nemotron 3 Ultra / OpenCode Zen.
5. If all fail, stop safely and report the exact blocker.

Operational rules:
- Quota exhaustion means shift change, not project halt.
- One worker = one task = one branch.
- No emergency/free/cheap worker writes directly to `master`.
- No merge or deploy without explicit approval.
- Health check: `powershell -ExecutionPolicy Bypass -File ops/ai/Test-FailoverHealth.ps1`.
- Portable bundle: `powershell -ExecutionPolicy Bypass -File ops/ai/Update-FailoverBundle.ps1`.

## Current Active Sprint
Sentry + PostHog Production Activation

Status: IN_PROGRESS

Completed:
- Sentry + PostHog instrumentation implemented by Codex
- Branch: codex/sentry-posthog-instrumentation
- Commit: 4a15eac3c63c28060837130bb98390189e477a47
- Backend tests: 204 passed
- Frontend tests: 31 passed
- compileall passed
- pip check passed
- doctor passed
- API probe passed
- web probe passed
- PostHog GamCryp organization confirmed
- PostHog project confirmed
- Sentry GitHub OAuth completed
- User approved creation of new GamCryp Sentry organization/project
- Sentry data region approved: EU
- GitHub email use for Sentry account approved

Current blocker:
- OpenAI Work usage limit interrupted execution

Next exact action:
1. Create/finish GamCryp Sentry organization/project in EU
2. Retrieve Sentry DSN values securely
3. Retrieve/use existing GamCryp PostHog project configuration
4. Configure Render production environment variables without exposing secrets
5. Merge step is already DONE; master and origin/master are already at the instrumentation commit
6. Deploy existing master commit after Render env configuration
7. Run production smoke tests
8. Verify Sentry, PostHog, GA4 and referral routing

## Safety
Do not expose secrets in repository files or chat.
Do not restart completed instrumentation work.
Do not create duplicate PostHog resources.

---

# WORK_QUEUE.md

# GamCryp Work Queue

## P0
- Complete Sentry + PostHog production activation

## Closed P0
- AI Failover / Vendor-Independent Operations: CLOSED / OPERATIONAL

## P1
- Human-First UX / Progressive Disclosure
- Customer acquisition / distribution
- Referral coverage expansion
- What is this / How does it work / Where does the money come from?
- YouTube API Publishing Layer
- Content Scheduler + Autonomous Publishing

## P2
- Project Trust / Legitimacy Layer
- Referral Independence / Trust Standard
- Retention Layer
- Weekly Product Truth Dashboard
- Lightweight Compliance Check
- Free / Premium + Stripe
- Autopilot hardening

## Parked / Later
- Grok X Intelligence Layer
- TikTok / Instagram / Bilibili
- WalletConnect
- 100+ opportunity catalog
- B2B / API product

## Rule
Priority changes must be recorded here and in DECISIONS.md when they represent a durable product decision.

---

# DECISIONS.md

# GamCryp Durable Decisions

1. GitHub/repository is the operational source of truth.
2. Primary/authoritative data only for financial modeling inputs.
3. Referral availability must never affect organic ranking, ROI, risk or confidence.
4. Human-First UX with progressive disclosure.
5. API-first automation; browser automation is fallback only.
6. GREEN content may become automatic after learning/validation.
7. YELLOW content requires approval.
8. RED content remains manual.
9. AI vendors/workers must be replaceable without stopping GamCryp operations.
10. No duplicate external resources should be created without checking existing GamCryp resources first.
11. Product growth priority remains:
    - Human-First UX
    - Customer acquisition / distribution
    before lower-priority feature expansion.
12. Catalog growth must be demand- and quality-driven, not number-driven.
13. Project legitimacy/trust is evaluated separately from ROI model performance.
14. Premium/paywall comes after evidence of repeat usage and retention demand.
15. YouTube publishing should migrate to an official API-based publishing layer instead of browser file-upload dependence.
16. Final system should minimize founder/operator intervention and use exception-based control.
17. Major milestones may receive an independent red-team / architecture audit.
18. AI Failover P0 is closed as an operational system. The canonical order is OpenAI Work/Codex for normal work, then DeepSeek V3.2 / OpenRouter / OpenCode, then Gemini CLI / Google API, then Nemotron 3 Ultra / OpenCode Zen.
19. Failover workers must use isolated branches. Emergency/free/cheap workers must not write directly to `master`; merge and deploy require explicit approval.
20. Browser/platform blockers have a maximum 3-minute budget: 1 normal attempt, 1 materially different fallback, then stop and report the exact human action required.
21. The portable failover bundle must be regenerated from canonical `ops/ai` files after material failover documentation changes.

---

# WORKER_CAPABILITIES.md

# GamCryp AI Worker Capabilities

Status: AI Failover P0 CLOSED / OPERATIONAL
Updated: 2026-08-30

This is the canonical worker capability matrix and failover order for GamCryp operations. It contains no secrets and does not authorize merge, deploy, account, billing, legal, security, production-data or credential decisions.

## Canonical Failover Order

NORMAL:
OpenAI Work / Codex

IF OPENAI QUOTA OR PLATFORM BLOCKER:
DeepSeek V3.2 / OpenRouter / OpenCode

IF THAT FAILS:
Gemini CLI / Google API

IF THAT FAILS:
Nemotron 3 Ultra / OpenCode Zen

IF ALL FAIL:
Stop safely and report the exact blocker, required account/action, branch, command, or missing access.

Quota exhaustion means shift change, not project halt.

## Worker Matrix

### OpenAI Work / Codex

Role: normal primary worker.

Verified capability:
- Strong repository and application implementation capability.
- Best default for regular development when quota is available.

Failure-domain note:
- Shares the OpenAI quota/platform failure domain.
- Not considered an independent failover worker.

Safety:
- May work on approved task branches.
- Must still follow repository gate, branch, test, and deployment rules.

### DeepSeek V3.2 / OpenRouter / OpenCode

Role: primary independent non-OpenAI failover.

Verified capability:
- Read takeover test: PASS.
- Real isolated write test: PASS.
- Commit test: PASS.
- Push test: PASS.
- Safe branch behavior: PASS.

Use for:
- Emergency continuation when OpenAI Work/Codex is unavailable.
- Branch-local implementation, diagnosis, tests, commits, and pushes.

Safety:
- Use only isolated task branches.
- No direct master writes.
- No merge or deploy without explicit human approval and strong review.
- Re-read `ops/ai` handoff files before acting.

### Gemini CLI / Google API

Role: secondary independent failover.

Verified capability:
- Context/read understanding: PASS.
- Suitable for emergency review, diagnosis, or smaller implementation tasks.

Observed limitations:
- Slower than primary failover.
- One real write test experienced fetch/network failure.

Safety:
- Same isolated-branch rule.
- No direct master writes.
- No merge or deploy without explicit human approval and strong review.
- Treat network/API instability as a reason to stop and report, not to keep retrying.

### Nemotron 3 Ultra / OpenCode Zen

Role: tertiary / last-resort independent failover.

Verified capability:
- Real write test: PASS.
- Commit test: PASS.
- Push test: PASS.
- Correctness acceptable in the tested task.

Observed limitations:
- Severe latency.

Use for:
- Last-resort independent continuation when OpenAI, DeepSeek/OpenRouter/OpenCode, and Gemini are unavailable.

Safety:
- Use only isolated task branches.
- No direct master writes.
- No merge or deploy without explicit human approval and strong review.

## Eliminated Or Parked Workers

- Groq + Qwen: parked due to context/compaction failure.
- Z.AI / GLM: parked due to payment/resource wall.
- Claude Code: parked until a paid Claude plan is available.
- Codex CLI: useful locally, but shares the OpenAI quota failure domain and is not a true independent failover.

## Branch Ownership Rule

- One worker = one task = one branch.
- Never let two workers mutate the same working tree concurrently.
- Before every write task run:
  - `git status --short`
  - `git branch --show-current`
- If another worker/task owns the current branch, STOP.
- Workers must create isolated task branches.
- Emergency/free/cheap workers must not write directly to `master`.
- No merge or deploy without explicit approval.

Branch convention for ops failover work:
`ops/<worker-or-purpose>/<task>`

Existing product feature branches may continue to use established `codex/<task>` naming when OpenAI/Codex owns the work.

## Quota-Saver Policy

- Browser/platform blocker budget: maximum 3 minutes.
- Try 1 normal attempt and 1 materially different fallback.
- If still blocked, stop that path and report the exact human action required.
- Pre-flight authentication, permissions, file upload capability, secrets, and write access before substantive work.
- API-first; browser automation is fallback only.
- Do not create duplicate accounts, projects, organizations, channels, apps, or resources without checking for existing GamCryp resources first.
- Batch safe independent actions where possible.
- Do not spend 20+ minutes fighting native file dialogs, file pickers, or brittle browser automation.

## Health Check

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File ops/ai/Test-FailoverHealth.ps1
```

The health check is read-only. It reports branch, clean/dirty state, canonical files, git, GitHub CLI, repository detection, and origin remote presence without printing tokens or mutating network state.

---

# HANDOFF.md

# GamCryp AI Handoff

Status: IN_PROGRESS

Current task:
Sentry + PostHog production activation

Primary execution owner:
OpenAI Work, when quota is available.

## AI Failover P0 State

Status: CLOSED / OPERATIONAL

Canonical failover order:
1. Normal: OpenAI Work / Codex.
2. If OpenAI quota/platform blocks work: DeepSeek V3.2 / OpenRouter / OpenCode.
3. If primary failover fails: Gemini CLI / Google API.
4. If secondary failover fails: Nemotron 3 Ultra / OpenCode Zen.
5. If all fail: stop safely and report the exact blocker.

Primary independent failover worker:
DeepSeek V3.2 / OpenRouter / OpenCode.

Secondary independent failover worker:
Gemini CLI / Google API.

Tertiary last-resort worker:
Nemotron 3 Ultra / OpenCode Zen.

Branch safety:
- One worker = one task = one branch.
- Before every write task, run `git status --short` and `git branch --show-current`.
- If another worker/task owns the branch, STOP.
- Emergency/free/cheap workers must not write directly to `master`.
- No merge or deploy without explicit approval.

Health check:
`powershell -ExecutionPolicy Bypass -File ops/ai/Test-FailoverHealth.ps1`

Portable bundle regeneration:
`powershell -ExecutionPolicy Bypass -File ops/ai/Update-FailoverBundle.ps1`

Operational rule:
Quota exhaustion means shift change, not project halt.

## Product Sprint Handoff

Failover rule:
If the current AI worker becomes unavailable because of quota, outage or vendor limitation, another capable agent may continue from this checkpoint.

Do not restart completed work.

Before continuing:
1. Read AGENT_RULES.md
2. Read CURRENT_STATE.md
3. Read WORK_QUEUE.md
4. Read DECISIONS.md
5. Read WORKER_CAPABILITIES.md
6. Confirm the active branch/task is not being modified simultaneously by another agent

Current checkpoint:
- Instrumentation code is already implemented and tested
- PostHog GamCryp organization/project already exists
- Sentry OAuth completed
- New GamCryp Sentry org/project creation approved
- Sentry region: EU
- GitHub email use approved
- Execution stopped only because OpenAI Work reached usage limit

Next exact step:
Continue Sentry account/project creation from the approved EU configuration, then proceed with secure Render env configuration, deploy existing master and production smoke.

## Experimental Branch Cleanup Recommendation

After this closure branch is reviewed/merged, these test branches can be deleted later by a human/operator if no longer needed:
- `ops/ai-failover-worker-test`: useful artifact adopted as `ops/ai/WORKER_CAPABILITIES.md`.
- `ops/failover-healthcheck-script`: useful artifact adopted as `ops/ai/Test-FailoverHealth.ps1`.
- `ops/failover-healthcheck-nemotron`: model-specific duplicate healthcheck; keep only for forensic history until closure review is accepted.

No remote branch deletion is authorized by this sprint.

At task completion:
Update CURRENT_STATE.md and this HANDOFF.md with the final commit, deployment result, blockers and next action when the active product sprint changes.

---

# ACCESS.md

# GamCryp AI Access Bootstrap

## Repository
Owner: IRequelm
Repository: gamefi-roi
Primary branch for failover foundation:
ops/ai-failover-foundation

Local Windows path:
C:\Projects\gamefi-roi

## Preferred access order

1. Direct local repository access
2. Authenticated GitHub connector / MCP / CLI access
3. Read-only FAILOVER_BUNDLE.md supplied manually
4. Manual copy of current handoff files as last resort

## Canonical failover order

1. Normal: OpenAI Work / Codex
2. Primary independent failover: DeepSeek V3.2 / OpenRouter / OpenCode
3. Secondary independent failover: Gemini CLI / Google API
4. Tertiary last resort: Nemotron 3 Ultra / OpenCode Zen
5. If all fail: stop safely and report the exact blocker

## Branch and collision rule

- One worker = one task = one branch.
- Never let two workers mutate the same working tree concurrently.
- Before every write task run:
  - `git status --short`
  - `git branch --show-current`
- If another worker/task owns the current branch, STOP.
- Workers must create isolated task branches.
- Ops failover branch convention: `ops/<worker-or-purpose>/<task>`.
- No direct `master` writes by emergency/free/cheap workers.
- No merge or deploy without explicit approval.

## If GitHub access is unavailable

Do NOT guess repository contents.
Do NOT search the public web and assume it is complete.

Ask for one of:
- local repository access
- GitHub authenticated access
- FAILOVER_BUNDLE.md

## Required read order

1. AGENT_RULES.md
2. CURRENT_STATE.md
3. WORK_QUEUE.md
4. DECISIONS.md
5. WORKER_CAPABILITIES.md
6. HANDOFF.md
7. ACCESS.md

## Health check

Run:

```powershell
powershell -ExecutionPolicy Bypass -File ops/ai/Test-FailoverHealth.ps1
```

The health check is read-only and prints no secrets.

## Security

Never request or expose:
- passwords
- API keys
- DSNs
- tokens
- cookies
- private credentials

Repository access and secret access are separate concerns.

## Failover objective

Loss of one AI vendor, quota, connector, browser session or tool must not stop GamCryp operations.
Quota exhaustion means shift change, not project halt.
