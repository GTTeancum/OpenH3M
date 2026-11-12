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
        -Iwork/h4-forge-research/isolated tools/h4-forge/test_original_selection.cpp `
        work/h4-forge-research/isolated/forge_original.obj `
        -o work/h4-forge-research/isolated/test_original_selection.exe `
        2> work/h4-forge-research/isolated/test-build.log
    if ($LASTEXITCODE -ne 0) { throw 'Selection test build failed' }
    & ./work/h4-forge-research/isolated/test_original_selection.exe `
        work/h4-forge-research/h4-image.bin > work/h4-forge-research/isolated/selection-test.log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Original selection behavior failed' }
    Get-Content work/h4-forge-research/isolated/selection-test.log
} finally { Pop-Location }
