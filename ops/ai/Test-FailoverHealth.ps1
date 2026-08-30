<#
.SYNOPSIS
    GamCryp AI Failover Health Check Script
.DESCRIPTION
    Read-only local health-check script for the AI failover foundation.
    Verifies prerequisites, reports status, and exits non-zero if any required local prerequisite is missing.
.NOTES
    - Runs NO writes
    - Runs NO git add/commit/push
    - Runs NO network mutation
    - Exposes NO credentials/tokens
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = if ($ScriptDir) { (Get-Item $ScriptDir).Parent.Parent.FullName } else { $null }
$OpsAiDir = if ($RepoRoot) { Join-Path (Join-Path $RepoRoot "ops") "ai" } else { $null }

function Write-Status {
    param(
        [string]$Check,
        [string]$Status,
        [string]$Message = ""
    )
    
    $color = if ($Status -eq "PASS") { "Green" } else { "Red" }
    Write-Host "[$Status] $Check" -ForegroundColor $color
    if ($Message) {
        Write-Host "  $Message" -ForegroundColor "DarkGray"
    }
}

function Test-RequiredFile {
    param(
        [string]$FilePath,
        [string]$FileName
    )
    
    $fullPath = Join-Path $OpsAiDir $FileName
    if (Test-Path -LiteralPath $fullPath) {
        Write-Status -Check "$FileName exists" -Status "PASS"
        return $true
    } else {
        Write-Status -Check "$FileName exists" -Status "FAIL" -Message "Missing: $fullPath"
        return $false
    }
}

# Initialize tracking
$allPassed = $true
$failedChecks = @()

Write-Host "`n=== GamCryp AI Failover Health Check ===" -ForegroundColor "Cyan"
Write-Host "Started at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor "DarkGray"

# 1. Verify ops/ai directory location
if (-not $OpsAiDir -or -not (Test-Path -LiteralPath $OpsAiDir)) {
    Write-Status -Check "ops/ai directory location" -Status "FAIL" -Message "Cannot locate ops/ai directory"
    $allPassed = $false
    $failedChecks += "ops/ai directory location"
} else {
    Write-Status -Check "ops/ai directory location" -Status "PASS" -Message $OpsAiDir
}

# 2. Verify required files exist
$requiredFiles = @(
    "AGENT_RULES.md",
    "CURRENT_STATE.md",
    "WORK_QUEUE.md",
    "DECISIONS.md",
    "HANDOFF.md",
    "ACCESS.md",
    "Update-FailoverBundle.ps1"
)

Write-Host "`n--- Required Files ---" -ForegroundColor "DarkCyan"
foreach ($file in $requiredFiles) {
    if (-not (Test-RequiredFile -FilePath $OpsAiDir -FileName $file)) {
        $allPassed = $false
        $failedChecks += "$file missing"
    }
}

# 3. Verify git availability
Write-Host "`n--- Git & Repository ---" -ForegroundColor "DarkCyan"
try {
    $gitVersion = git --version 2>$null
    if ($gitVersion) {
        Write-Status -Check "git available" -Status "PASS" -Message $gitVersion.Trim()
    } else {
        Write-Status -Check "git available" -Status "FAIL" -Message "git command not found"
        $allPassed = $false
        $failedChecks += "git not available"
    }
} catch {
    Write-Status -Check "git available" -Status "FAIL" -Message "git command error: $_"
    $allPassed = $false
    $failedChecks += "git error"
}

# 4. Verify gh availability
try {
    $ghVersion = gh --version 2>$null
    if ($ghVersion) {
        Write-Status -Check "gh available" -Status "PASS" -Message "GitHub CLI detected"
    } else {
        Write-Status -Check "gh available" -Status "FAIL" -Message "gh command not found"
        $allPassed = $false
        $failedChecks += "gh not available"
    }
} catch {
    Write-Status -Check "gh available" -Status "FAIL" -Message "gh command error: $_"
    $allPassed = $false
    $failedChecks += "gh error"
}

# 5. Verify current git repository
try {
    $gitRoot = git rev-parse --show-toplevel 2>$null
    if ($gitRoot) {
        Write-Status -Check "git repository detected" -Status "PASS" -Message $gitRoot
    } else {
        Write-Status -Check "git repository detected" -Status "FAIL" -Message "Not in a git repository"
        $allPassed = $false
        $failedChecks += "not in git repository"
    }
} catch {
    Write-Status -Check "git repository detected" -Status "FAIL" -Message "git repo detection error: $_"
    $allPassed = $false
    $failedChecks += "git repo detection error"
}

# 6. Report current git branch
try {
    $currentBranch = git branch --show-current 2>$null
    if ($currentBranch) {
        Write-Status -Check "current git branch" -Status "PASS" -Message $currentBranch
    } else {
        Write-Status -Check "current git branch" -Status "FAIL" -Message "Cannot determine current branch"
        $allPassed = $false
        $failedChecks += "cannot determine branch"
    }
} catch {
    Write-Status -Check "current git branch" -Status "FAIL" -Message "git branch error: $_"
    $allPassed = $false
    $failedChecks += "git branch error"
}

# 7. Check if working tree is clean
try {
    $gitStatus = git status --short 2>$null
    if (-not $gitStatus) {
        Write-Status -Check "working tree clean" -Status "PASS" -Message "No uncommitted changes"
    } else {
        Write-Status -Check "working tree clean" -Status "FAIL" -Message "Working tree has uncommitted changes"
        if ($Verbose) {
            Write-Host "  Changes:`n$gitStatus" -ForegroundColor "DarkGray"
        }
        $allPassed = $false
        $failedChecks += "working tree not clean"
    }
} catch {
    Write-Status -Check "working tree clean" -Status "FAIL" -Message "git status error: $_"
    $allPassed = $false
    $failedChecks += "git status error"
}

# 8. Check if origin remote exists
try {
    $originUrl = git remote get-url origin 2>$null
    if ($originUrl) {
        Write-Status -Check "origin remote exists" -Status "PASS" -Message "Remote configured"
    } else {
        Write-Status -Check "origin remote exists" -Status "FAIL" -Message "No origin remote configured"
        $allPassed = $false
        $failedChecks += "origin remote missing"
    }
} catch {
    Write-Status -Check "origin remote exists" -Status "FAIL" -Message "git remote error: $_"
    $allPassed = $false
    $failedChecks += "git remote error"
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor "Cyan"
if ($allPassed) {
    Write-Host "PASS: All health checks passed" -ForegroundColor "Green"
    exit 0
} else {
    Write-Host "FAIL: $($failedChecks.Count) check(s) failed:" -ForegroundColor "Red"
    foreach ($fail in $failedChecks) {
        Write-Host "  - $fail" -ForegroundColor "Yellow"
    }
    exit 1
}