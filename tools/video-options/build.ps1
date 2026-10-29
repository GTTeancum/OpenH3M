$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $repo
$oldTemp = $env:TEMP; $oldTmp = $env:TMP
try {
    if (Get-Process halo3mp -ErrorAction SilentlyContinue) { throw 'Close the candidate before rebuilding its DLLs.' }
    $env:TEMP = Join-Path $repo 'work/build-temp'; $env:TMP = $env:TEMP
    cmake --build work/rexglue-sdk/out/pacing-release --target rexruntime rexgpu-xenos halo3mp video_settings_check --parallel 4
    if ($LASTEXITCODE -ne 0) { throw 'Video-options build failed' }
    & ./work/rexglue-sdk/out/win-amd64/video_settings_check.exe (Join-Path $repo 'work/video-options/settings-roundtrip.toml')
    if ($LASTEXITCODE -ne 0) { throw 'Video settings check failed' }
} finally {
    $env:TEMP = $oldTemp; $env:TMP = $oldTmp
    Pop-Location
}
