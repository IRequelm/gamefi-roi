<#
.SYNOPSIS
    GamCryp AI failover health check.
.DESCRIPTION
    Read-only local health check for the vendor-independent AI failover foundation.
    It verifies required handoff files and local tooling, reports current Git state, and exits non-zero only when a required prerequisite is missing or unavailable.
.NOTES
    - Performs no writes.
    - Performs no git add/commit/push.
    - Performs no network mutation.
    - Prints no credentials, tokens, DSNs, cookies, API keys or private secret values.
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$failures = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

function Write-Check {
    param(
        [string]$Status,
        [string]$Name,
        [string]$Detail = ""
    )

    $color = switch ($Status) {
        "PASS" { "Green" }
        "WARN" { "Yellow" }
        default { "Red" }
    }
    Write-Host "[$Status] $Name" -ForegroundColor $color
    if ($Detail) {
        Write-Host "  $Detail" -ForegroundColor "DarkGray"
    }
}

function Add-Failure {
    param([string]$Message)
    $failures.Add($Message) | Out-Null
}

function Add-Warning {
    param([string]$Message)
    $warnings.Add($Message) | Out-Null
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) {
    Write-Check "FAIL" "script directory" "Could not locate script directory."
    Add-Failure "script directory missing"
} else {
    $opsAiDir = (Resolve-Path -LiteralPath $scriptDir).Path
    $repoRoot = (Resolve-Path -LiteralPath (Join-Path $opsAiDir "..\..")).Path
    Write-Check "PASS" "ops/ai directory" $opsAiDir
}

Write-Host "`n=== GamCryp AI Failover Health ===" -ForegroundColor "Cyan"
Write-Host "Read-only check. No writes or network mutations are performed.`n" -ForegroundColor "DarkGray"

if ($scriptDir) {
    $requiredFiles = @(
        "AGENT_RULES.md",
        "CURRENT_STATE.md",
        "WORK_QUEUE.md",
        "DECISIONS.md",
        "HANDOFF.md",
        "ACCESS.md",
        "WORKER_CAPABILITIES.md",
        "FAILOVER_BUNDLE.md",
        "Update-FailoverBundle.ps1",
        "Test-FailoverHealth.ps1"
    )

    foreach ($file in $requiredFiles) {
        $path = Join-Path $opsAiDir $file
        if (Test-Path -LiteralPath $path) {
            Write-Check "PASS" "required file: $file"
        } else {
            Write-Check "FAIL" "required file: $file" "Missing canonical handoff file."
            Add-Failure "missing $file"
        }
    }
}

try {
    $gitVersion = git --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $gitVersion) {
        Write-Check "PASS" "git available" ($gitVersion | Select-Object -First 1)
    } else {
        Write-Check "FAIL" "git available" "git command not found or failed."
        Add-Failure "git unavailable"
    }
} catch {
    Write-Check "FAIL" "git available" "git command threw an error."
    Add-Failure "git unavailable"
}

try {
    $ghVersion = gh --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $ghVersion) {
        Write-Check "PASS" "gh available" (($ghVersion | Select-Object -First 1).Trim())
    } else {
        Write-Check "FAIL" "gh available" "GitHub CLI is required for failover branch/push operations."
        Add-Failure "gh unavailable"
    }
} catch {
    Write-Check "FAIL" "gh available" "GitHub CLI command threw an error."
    Add-Failure "gh unavailable"
}

try {
    $detectedRoot = git -C $repoRoot rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0 -and $detectedRoot) {
        Write-Check "PASS" "git repository detected" $detectedRoot.Trim()
    } else {
        Write-Check "FAIL" "git repository detected" "Could not detect repository root."
        Add-Failure "repo not detected"
    }
} catch {
    Write-Check "FAIL" "git repository detected" "git rev-parse failed."
    Add-Failure "repo not detected"
}

try {
    $branch = git -C $repoRoot branch --show-current 2>$null
    if ($LASTEXITCODE -eq 0 -and $branch) {
        Write-Check "PASS" "current branch" $branch.Trim()
        if ($branch.Trim() -eq "master") {
            Write-Check "WARN" "branch safety" "Current branch is master; failover workers must create isolated task branches before writing."
            Add-Warning "current branch is master"
        }
    } else {
        Write-Check "FAIL" "current branch" "Could not determine current branch."
        Add-Failure "branch unknown"
    }
} catch {
    Write-Check "FAIL" "current branch" "git branch failed."
    Add-Failure "branch unknown"
}

try {
    $status = git -C $repoRoot status --short 2>$null
    if ($LASTEXITCODE -eq 0) {
        if ($status) {
            Write-Check "WARN" "working tree" "Dirty working tree detected; ensure exactly one worker owns this task/branch."
            Add-Warning "working tree dirty"
            if ($Verbose) {
                $status | ForEach-Object { Write-Host "  $_" -ForegroundColor "DarkGray" }
            }
        } else {
            Write-Check "PASS" "working tree" "Clean"
        }
    } else {
        Write-Check "FAIL" "working tree" "git status failed."
        Add-Failure "status failed"
    }
} catch {
    Write-Check "FAIL" "working tree" "git status threw an error."
    Add-Failure "status failed"
}

try {
    $origin = git -C $repoRoot remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0 -and $origin) {
        Write-Check "PASS" "origin remote" "Configured"
    } else {
        Write-Check "FAIL" "origin remote" "No origin remote configured."
        Add-Failure "origin missing"
    }
} catch {
    Write-Check "FAIL" "origin remote" "git remote failed."
    Add-Failure "origin missing"
}

Write-Host "`n=== Summary ===" -ForegroundColor "Cyan"
if ($failures.Count -eq 0) {
    if ($warnings.Count -gt 0) {
        Write-Host "PASS with $($warnings.Count) warning(s)." -ForegroundColor "Yellow"
    } else {
        Write-Host "PASS: all failover health checks passed." -ForegroundColor "Green"
    }
    exit 0
}

Write-Host "FAIL: $($failures.Count) required check(s) failed." -ForegroundColor "Red"
foreach ($failure in $failures) {
    Write-Host "  - $failure" -ForegroundColor "Yellow"
}
exit 1