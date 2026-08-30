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