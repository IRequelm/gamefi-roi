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