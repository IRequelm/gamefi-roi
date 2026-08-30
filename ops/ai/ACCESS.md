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
5. HANDOFF.md

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
