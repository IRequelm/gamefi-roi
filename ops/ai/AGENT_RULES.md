# GamCryp AI Agent Rules

1. Read CURRENT_STATE.md, WORK_QUEUE.md, HANDOFF.md and DECISIONS.md before doing any work.
2. GitHub/repository is the operational source of truth.
3. Never expose secrets, tokens, DSNs, passwords, cookies, API keys or private credentials.
4. API-first. Browser automation is fallback only.
5. Browser/platform blocker budget: maximum 3 minutes.
6. Maximum retry policy: 1 normal attempt + 1 materially different fallback.
7. If still blocked, stop that path and record the exact human action required.
8. Never create duplicate accounts, projects, organizations or resources without checking for an existing GamCryp resource first.
9. Never let two agents modify the same task/branch simultaneously.
10. Preserve production behavior unless the active task explicitly requires a change.
11. Test before merge or deploy.
12. Do not merge or deploy unless the active task explicitly authorizes it.
13. Do not restart completed research or implementation. Continue from the latest checkpoint.
14. At the end of every meaningful task, update CURRENT_STATE.md and HANDOFF.md.
15. Human approval is required for irreversible account, billing, legal, security, production-data or credential decisions.
