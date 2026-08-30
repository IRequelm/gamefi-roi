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