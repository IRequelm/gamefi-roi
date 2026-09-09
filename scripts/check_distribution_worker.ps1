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
  $heartbeat = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
  $updatedAt = [DateTimeOffset]::Parse($heartbeat.updated_at).ToUniversalTime()
} catch {
  Write-Error "Distribution worker heartbeat is invalid: $path"
  exit 3
}

$age = ([DateTimeOffset]::UtcNow - $updatedAt).TotalMinutes
if ($heartbeat.status -ne "ok") {
  Write-Error "Distribution worker heartbeat status is '$($heartbeat.status)'"
  exit 4
}
if ($age -gt $MaxAgeMinutes) {
  Write-Error ("Distribution worker heartbeat is stale: {0:N1} minutes old" -f $age)
  exit 5
}

Write-Output ("Distribution worker healthy: status=ok age_minutes={0:N1}" -f $age)
exit 0
