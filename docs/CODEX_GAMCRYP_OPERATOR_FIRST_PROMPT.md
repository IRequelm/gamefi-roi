# Codex CLI — First Prompt for GamCryp Operator V1

Use this from the repository root.

```text
You are implementing GamCryp Operator V1 in this existing repository.

FIRST: read AGENTS.md, docs/GAMCRYP_OPERATOR_V1_LOCK.md, docs/MASTER_CONTROL.md, docs/STATUS.md, docs/ARCHITECTURE.md, docs/GROWTH_OPERATING_PLAN.md, docs/PRODUCTION_RUNBOOK.md, and the relevant discovery/distribution/doctor/analytics code before changing anything.

The V1 plan is LOCKED. Do not add features outside docs/GAMCRYP_OPERATOR_V1_LOCK.md. Do not redesign the site. Do not create a new dashboard, domain, cloud service, agent framework, model router or database. Reuse existing code. Any attractive new idea goes only to a backlog note.

Goal of this task: complete PHASE 1 ONLY — the restart-safe local GamCryp Operator core.

Context:
- Public production site remains on Render.
- This Windows PC is the operator machine while it is powered on.
- If the PC is off, the site must remain unaffected.
- When the PC comes back, the operator must detect downtime and perform catch-up assessment from the last successful checkpoint.
- Existing discovery worker, distribution worker, doctor/health checks, growth metrics, content pipeline, YouTube/X publishing, referral operations and safety gates already exist. Do not rewrite them.
- The operator’s mission is: attract qualified users, make the site useful, grow qualified outbound/referral activity, and keep the system healthy.
- The operator must also produce evidence-backed recommendations such as “this site/content change is likely to attract more qualified users because …”, but Phase 1 recommendations are READ-ONLY. Do not implement new UX/product changes in this phase.

Required Phase-1 deliverables:
1. Inspect the current repository and document which existing subsystems can be reused by the operator and which existing schedulers/tasks could conflict with it.
2. Implement one local supervisor entry point for GamCryp Operator. Choose the smallest clean location consistent with the existing architecture.
3. Implement durable local operator state/checkpoint under an ignored local data path. State must include at minimum:
   - version,
   - last_cycle_started_at,
   - last_cycle_completed_at,
   - last_successful_checkpoint_at,
   - detected_downtime_seconds,
   - last_observation_summary,
   - prioritized_actions,
   - action_history,
   - owner_action_required,
   - growth_product_recommendations.
4. Implement the Phase-1 cycle:
   OBSERVE → DIAGNOSE → PRIORITIZE → ACT → VERIFY → CHECKPOINT.
5. OBSERVE must read available existing local/public evidence without inventing status:
   - public site/API health using existing health routes,
   - discovery state,
   - distribution heartbeat/state/queues,
   - doctor/runtime status where safe,
   - repository cleanliness/current revision if deterministic,
   - existing growth/metrics output if available.
6. PRIORITIZE must use deterministic mission-impact rules. Health/blocker first, then catalog/discovery value, distribution blockage, growth/UX evidence, monetization/referral gaps. Do not use an LLM as the authoritative runtime controller in Phase 1.
7. ACT in Phase 1 must be conservative:
   - it may invoke an already-existing SAFE read-only/status operation,
   - it may run an existing deterministic recovery only if that recovery already exists, is reversible/idempotent, and tests prove it,
   - otherwise record a proposed action instead of executing it.
8. Generate growth_product_recommendations from verified evidence. Each recommendation must contain:
   - recommendation,
   - evidence,
   - expected_impact,
   - effort,
   - confidence,
   - risk,
   - auto_action_allowed=false for Phase 1.
   Example type: “homepage copy/information hierarchy should be simplified because users/search traffic reach X but fail to progress to Y.” Never invent unavailable funnel data.
9. Add a Windows auto-start mechanism using the existing project conventions, but DO NOT disable or remove existing scheduled tasks yet. Document conflicts and keep the change reversible.
10. Add tests for:
   - first run,
   - restart and checkpoint recovery,
   - simulated multi-hour/day downtime catch-up calculation,
   - duplicate-instance protection,
   - corrupt/missing state recovery,
   - no unsafe action when evidence is missing,
   - recommendation generation never fabricates unavailable metrics.
11. Run the relevant test suite and doctor/static checks. Fix only failures caused by this task.
12. Update docs/GAMCRYP_OPERATOR_V1_LOCK.md only with implementation evidence/status, not new scope. Add a short Phase-1 runbook.

Acceptance gate:
- One command starts the operator.
- A full observe→prioritize→act/skip→verify→checkpoint cycle completes.
- Killing and restarting the process preserves state.
- Simulated downtime is detected and recorded.
- Existing workers are not accidentally double-run.
- No production site dependency is introduced.
- No existing GREEN/YELLOW/RED, publish cap, evidence, or financial-truth gate is weakened.
- Growth/Product recommendations are evidence-bound and read-only.
- All relevant tests pass.

When complete, STOP. Do not start Phase 2.
Return:
- files changed,
- tests/checks run and results,
- exact command to start the operator,
- exact Windows auto-start state,
- observed conflicts with existing scheduled workers,
- one sample operator cycle output,
- remaining Phase-1 blockers, if any.
```
