param([string]$Python = 'python', [string]$CMake = 'cmake')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $repo
$oldTemp = $env:TEMP; $oldTmp = $env:TMP
try {
    if (Get-Process halo3mp -ErrorAction SilentlyContinue) { throw 'Close Spartan before rebuilding its runtime DLL.' }
    $env:TEMP = Join-Path $repo 'work/build-temp'; $env:TMP = $env:TEMP
    New-Item -ItemType Directory -Force $env:TEMP | Out-Null
    & $Python -B tools/input-focus/prepare_test.py
    if ($LASTEXITCODE -ne 0) { throw 'Keyboard test preparation failed' }
    & $CMake --build work/rexglue-sdk/out/pacing-release --target rexruntime halo3mp input_focus_check --parallel 4
    if ($LASTEXITCODE -ne 0) { throw 'Input-focus build failed' }
    & ./work/rexglue-sdk/out/win-amd64/input_focus_check.exe
    if ($LASTEXITCODE -ne 0) { throw 'Input-focus checks failed' }
} finally {
    $env:TEMP = $oldTemp; $env:TMP = $oldTmp
    Pop-Location
}
