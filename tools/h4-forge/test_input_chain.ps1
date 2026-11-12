$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$priorTemp = $env:TEMP
$priorTmp = $env:TMP
Push-Location $repo
try {
    $env:TEMP = Join-Path $repo 'work/build-temp'
    $env:TMP = $env:TEMP
    & 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B tools/h4-forge/extract_input_chain.py
    if ($LASTEXITCODE -ne 0) { throw 'Input chain extraction failed' }
    & 'C:/Program Files/LLVM/bin/clang++.exe' -std=c++23 -DREX_PLATFORM_WINDOWS=1 `
        -Iwork/rexglue-sdk/include -Iwork/rexglue-sdk/thirdparty/simde `
        -Iwork/rexglue-sdk/thirdparty/fmt/include -Iwork/rexglue-sdk/thirdparty/spdlog/include `
        -Iwork/h4-forge-research/isolated tools/h4-forge/test_input_chain.cpp `
        work/h4-forge-research/isolated/input_chain_original.cpp `
        -o work/h4-forge-research/isolated/test_input_chain.exe
    if ($LASTEXITCODE -ne 0) { throw 'Input chain test build failed' }
    & work/h4-forge-research/isolated/test_input_chain.exe 2>&1 |
        Tee-Object work/h4-forge-research/isolated/input_chain-test.log
    if ($LASTEXITCODE -ne 0) { throw 'Input chain test failed' }
} finally {
    $env:TEMP = $priorTemp
    $env:TMP = $priorTmp
    Pop-Location
}
