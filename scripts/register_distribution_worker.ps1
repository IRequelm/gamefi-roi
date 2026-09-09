param(
  [string]$TaskName = "GamCryp Distribution Worker",
  [int]$IntervalMinutes = 30
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_distribution_worker.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Worker runner not found: $runner"
}
if ($IntervalMinutes -lt 1) {
  throw "IntervalMinutes must be at least 1"
}

$intervalSeconds = $IntervalMinutes * 60
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" --interval-seconds $intervalSeconds" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 3650) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Runs the fail-closed GamCryp distribution worker (interval ${IntervalMinutes}m)." -Force
Write-Output "Registered $TaskName for $repo"
Write-Output "The worker loads the ignored .env file at startup and runs every ${IntervalMinutes}m after logon."
