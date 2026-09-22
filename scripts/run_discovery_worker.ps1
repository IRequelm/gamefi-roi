param()

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repo | Set-Location
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  throw "Repository virtual environment not found: $python"
}

$envFile = Join-Path $repo ".env"
if (Test-Path -LiteralPath $envFile) {
  Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
      $name, $value = $line.Split("=", 2)
      [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
    }
  }
}

$logFile = Join-Path $repo "data\local\discovery\worker.log"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logFile) | Out-Null
Start-Transcript -LiteralPath $logFile -Append | Out-Null
$env:PYTHONPATH = Join-Path $repo "backend"
try {
  & $python -m app.discovery.worker --once
  $exitCode = $LASTEXITCODE
} finally {
  Stop-Transcript | Out-Null
}
exit $exitCode
