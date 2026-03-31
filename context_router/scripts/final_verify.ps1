param(
    [string]$BaseUrl = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent $envRoot
$openenvExe = Join-Path $repoRoot ".venv\Scripts\openenv.exe"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

$env:PYTHONIOENCODING = "utf-8"
$env:LANG = "en_US.UTF-8"
$env:LC_ALL = "en_US.UTF-8"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""
$env:NO_PROXY = "*"

Push-Location $envRoot
try {
    if (-not $SkipBuild) {
        & $openenvExe build
    }

    & $openenvExe validate --verbose
    & $pythonExe .\baseline\run_baseline.py --base-url "http://localhost:8000"

    if ($BaseUrl) {
        & $pythonExe .\baseline\run_baseline.py --base-url $BaseUrl
        & $openenvExe validate --verbose --url $BaseUrl --timeout 60
    }
}
finally {
    Pop-Location
}
