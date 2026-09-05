param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$WorkerArguments
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  throw "Repository virtual environment not found: $python"
}
$env:PYTHONPATH = Join-Path $repo "backend"
& $python -m app.publishing.distribution_worker @WorkerArguments
exit $LASTEXITCODE
