$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $projectRoot "src"
Set-Location $projectRoot

if (Test-Path -LiteralPath $venvPython) {
    & $venvPython -m axiom run
} else {
    & python -m axiom run
}

exit $LASTEXITCODE
