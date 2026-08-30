$ErrorActionPreference = "Stop"

$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$Bundle = Join-Path $Base "FAILOVER_BUNDLE.md"

$Files = @(
    "AGENT_RULES.md",
    "CURRENT_STATE.md",
    "WORK_QUEUE.md",
    "DECISIONS.md",
    "WORKER_CAPABILITIES.md",
    "HANDOFF.md",
    "ACCESS.md"
)

$Header = @"
# GamCryp Failover Bundle

This file is a portable read-only handoff snapshot for an AI worker that cannot access the repository directly.

IMPORTANT:
- Treat this bundle as context, not as permission.
- Do not expose secrets.
- Do not deploy, merge, create accounts or modify production unless explicitly authorized.
- If repository access becomes available, verify this bundle against the live repository before making changes.

Generated from the canonical files in ops/ai.

Health check command:
````powershell
powershell -ExecutionPolicy Bypass -File ops/ai/Test-FailoverHealth.ps1
````

Portable bundle regeneration command:
````powershell
powershell -ExecutionPolicy Bypass -File ops/ai/Update-FailoverBundle.ps1
````
"@

Set-Content -Path $Bundle -Value $Header -Encoding UTF8

foreach ($File in $Files) {
    $Path = Join-Path $Base $File

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required handoff file: $File"
    }

    Add-Content -Path $Bundle -Value "`n---`n" -Encoding UTF8
    Add-Content -Path $Bundle -Value "# $File`n" -Encoding UTF8
    Get-Content -LiteralPath $Path | Add-Content -Path $Bundle -Encoding UTF8
}

Write-Host "FAILOVER_BUNDLE.md regenerated successfully."