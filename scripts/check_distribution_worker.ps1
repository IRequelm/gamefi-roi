param(
  [int]$MaxAgeMinutes = 45,
  [string]$HeartbeatPath = "data\local\distribution\worker_heartbeat.json"
)

if ($MaxAgeMinutes -lt 1) {
  throw "MaxAgeMinutes must be at least 1"
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$path = Join-Path $repo $HeartbeatPath
if (-not (Test-Path -LiteralPath $path)) {
  Write-Error "Distribution worker heartbeat is missing: $path"
  exit 2
}

try {
  $heartbeatJson = Get-Content -LiteralPath $path -Raw -Encoding UTF8
  $heartbeat = $heartbeatJson | ConvertFrom-Json
  $updatedAtMatch = [regex]::Match($heartbeatJson, '"updated_at"\s*:\s*"([^"]+)"')
  if (-not $updatedAtMatch.Success) {
    throw "Heartbeat is missing an ISO-8601 updated_at string"
  }
  $updatedAt = [DateTimeOffset]::Parse($updatedAtMatch.Groups[1].Value).ToUniversalTime()
} catch {
  Write-Error "Distribution worker heartbeat is invalid: $path"
  exit 3
}

$age = ([DateTimeOffset]::UtcNow - $updatedAt).TotalMinutes
if ($heartbeat.status -ne "ok") {
  Write-Error "Distribution worker heartbeat status is '$($heartbeat.status)'"
  exit 4
}
if ($null -eq $heartbeat.pid -or -not ($heartbeat.pid -is [int] -or $heartbeat.pid -is [long]) -or $heartbeat.pid -lt 1) {
  Write-Error "Distribution worker heartbeat does not contain a valid process id"
  exit 6
}
if (-not (Get-Process -Id $heartbeat.pid -ErrorAction SilentlyContinue)) {
  Write-Error "Distribution worker process is not running: pid=$($heartbeat.pid)"
  exit 7
}
if ($age -gt $MaxAgeMinutes) {
  Write-Error ("Distribution worker heartbeat is stale: {0:N1} minutes old" -f $age)
  exit 5
}

Write-Output ("Distribution worker healthy: status=ok pid={1} age_minutes={0:N1}" -f $age, $heartbeat.pid)
exit 0
