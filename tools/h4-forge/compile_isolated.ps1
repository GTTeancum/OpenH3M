$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $repo
try {
    $env:TEMP = Join-Path $repo 'work/build-temp'
    $env:TMP = $env:TEMP
    & 'C:/Program Files/LLVM/bin/clang++.exe' -std=c++23 -DREX_PLATFORM_WINDOWS=1 `
        -Iwork/rexglue-sdk/include -Iwork/rexglue-sdk/thirdparty/simde `
        -Iwork/rexglue-sdk/thirdparty/fmt/include -Iwork/rexglue-sdk/thirdparty/spdlog/include `
        -c work/h4-forge-research/isolated/forge_original.cpp `
        -o work/h4-forge-research/isolated/forge_original.obj `
        2> work/h4-forge-research/isolated/compile.log
    if ($LASTEXITCODE -ne 0) { throw "Original Forge compilation failed; see isolated/compile.log" }
} finally { Pop-Location }
