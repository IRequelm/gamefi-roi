param(
  [string]$TaskName = "GamCryp Discovery Worker",
  [int]$IntervalHours = 6
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_discovery_worker.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Discovery worker runner not found: $runner"
}
if ($IntervalHours -lt 1) {
  throw "IntervalHours must be at least 1"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours $IntervalHours) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Runs the fail-closed GamCryp discovery intelligence worker every ${IntervalHours}h." -Force
Write-Output "Registered $TaskName for $repo"
Write-Output "The worker performs no publication and writes provider state under data\local\discovery."
