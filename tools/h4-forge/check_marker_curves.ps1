$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $repo
try {
    $env:TEMP = Join-Path $repo 'work/build-temp'
    $env:TMP = $env:TEMP
    & "$PSScriptRoot/compile_isolated.ps1"
    & 'C:/Program Files/LLVM/bin/clang++.exe' -std=c++23 -DREX_PLATFORM_WINDOWS=1 `
        -Iwork/rexglue-sdk/include -Iwork/rexglue-sdk/thirdparty/simde `
        -Iwork/rexglue-sdk/thirdparty/fmt/include -Iwork/rexglue-sdk/thirdparty/spdlog/include `
        -Iwork/h4-forge-research/isolated tools/h4-forge/check_marker_curves.cpp tools/h4-forge/forge_bridge.cpp `
        work/h4-forge-research/isolated/forge_original.obj `
        -o work/h4-forge-research/isolated/check_marker_curves.exe `
        2> work/h4-forge-research/isolated/marker-curves-build.log
    if ($LASTEXITCODE -ne 0) { throw 'Marker curve checker build failed' }
    & 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B "$PSScriptRoot/verify_marker_curves.py"
    if ($LASTEXITCODE -ne 0) { throw 'Original marker curve check failed' }
} finally { Pop-Location }
