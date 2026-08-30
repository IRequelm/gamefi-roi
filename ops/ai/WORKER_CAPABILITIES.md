# Verified AI Worker Capabilities Matrix

## OpenAI Codex CLI
- local repo access: yes
- git/gh access through host: yes
- limitation: shares OpenAI/Codex usage quota
- role: primary local coding worker while quota is available

## OpenAI Work
- role: browser/account operations
- limitation: OpenAI usage quota

## Gemini CLI
- local repo access: yes
- authentication: Gemini API key
- handoff comprehension: passed
- observed limitation: very slow on the read-only handoff test
- role: secondary failover

## OpenCode + DeepSeek V3.2 via OpenRouter
- local repo access: yes
- handoff comprehension: passed
- observed read-only test time: 13.5 seconds
- observed test cost shown by OpenCode: $0.00
- role: primary non-OpenAI failover candidate

## Safety Principles
- No AI worker writes directly to master.
- Every takeover uses an isolated branch.
- Production deploy requires explicit authorization.
- Secrets are never written to repository files.
- A worker must read ops/ai handoff files before acting.
- If another worker owns the active task, do not modify the same task/branch.