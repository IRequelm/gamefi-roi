param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$WorkerArguments
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
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
$distributionLog = Join-Path $repo "data\local\distribution\worker.log"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $distributionLog) | Out-Null
Start-Transcript -LiteralPath $distributionLog -Append | Out-Null
$env:PYTHONPATH = Join-Path $repo "backend"
try {
  & $python -m app.publishing.distribution_worker @WorkerArguments
  $exitCode = $LASTEXITCODE
} finally {
  Stop-Transcript | Out-Null
}
exit $exitCode
