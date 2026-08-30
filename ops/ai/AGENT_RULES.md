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