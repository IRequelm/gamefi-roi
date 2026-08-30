<# 
.SYNOPSIS
Nemotron failover health check - read-only validation of prerequisites
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$failures = @()

function Log { param($msg) Write-Host "[HEALTH] $msg" }
function Fail { param($msg) $failures += $msg; Log "FAIL: $msg" }
function Pass { param($msg) Log "PASS: $msg" }

# Required handoff files
$requiredFiles = @(
    "ops/ai/AGENT_RULES.md",
    "ops/ai/CURRENT_STATE.md",
    "ops/ai/WORK_QUEUE.md",
    "ops/ai/DECISIONS.md",
    "ops/ai/HANDOFF.md",
    "ops/ai/ACCESS.md"
)

Log "=== Nemotron Failover Health Check ==="

# Verify required ops/ai handoff files exist
foreach ($f in $requiredFiles) {
    $full = Join-Path (Get-Location) $f
    if (Test-Path -LiteralPath $full) {
        Pass "File exists: $f"
    } else {
        Fail "Missing file: $f"
    }
}

# Verify git exists
try {
    $gitVer = git --version
    Pass "Git available: $($gitVer.Trim())"
} catch {
    Fail "Git not found in PATH"
}

# Verify gh exists
try {
    $ghVer = gh --version
    Pass "GitHub CLI available: $($ghVer.Split("`n")[0].Trim())"
} catch {
    Fail "GitHub CLI (gh) not found in PATH"
}

# Detect repo
try {
    $repoRoot = git rev-parse --show-toplevel 2>$null
    if ($repoRoot) {
        Pass "Git repository detected: $repoRoot"
    } else {
        Fail "Not inside a git repository"
    }
} catch {
    Fail "Git repo detection failed"
}

# Report current branch
try {
    $branch = git branch --show-current
    Pass "Current branch: $branch"
} catch {
    Fail "Could not determine current branch"
}

# Report working tree clean/dirty
try {
    $status = git status --porcelain
    if ($status) {
        Log "Working tree: DIRTY"
        $status.Split("`n") | Where-Object { $_ } | ForEach-Object { Log "  $_" }
    } else {
        Pass "Working tree: CLEAN"
    }
} catch {
    Fail "Could not check working tree status"
}

# Verify origin exists
try {
    $remotes = git remote -v
    if ($remotes -match "origin") {
        Pass "Origin remote configured"
    } else {
        Fail "Origin remote not configured"
    }
} catch {
    Fail "Could not check remotes"
}

# Summary
Log "=== Summary ==="
if ($failures.Count -eq 0) {
    Log "HEALTH: PASS"
    exit 0
} else {
    Log "HEALTH: FAIL ($($failures.Count) issue(s))"
    $failures | ForEach-Object { Log "  - $_" }
    exit 1
}