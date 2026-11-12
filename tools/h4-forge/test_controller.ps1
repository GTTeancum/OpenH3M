$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$priorTemp = $env:TEMP
$priorTmp = $env:TMP
Push-Location $repo
try {
    $env:TEMP = Join-Path $repo 'work/build-temp'
    $env:TMP = $env:TEMP
    & 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B tools/h4-forge/verify_original.py
    if ($LASTEXITCODE -ne 0) { throw 'Original dependency verification failed' }
    & 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B tools/h4-forge/extract_controller_test.py
    if ($LASTEXITCODE -ne 0) { throw 'Controller extraction failed' }
    & 'C:/Program Files/LLVM/bin/clang++.exe' -std=c++23 -DREX_PLATFORM_WINDOWS=1 `
        -Iwork/rexglue-sdk/include -Iwork/rexglue-sdk/thirdparty/simde `
        -Iwork/rexglue-sdk/thirdparty/fmt/include -Iwork/rexglue-sdk/thirdparty/spdlog/include `
        -Iwork/h4-forge-research/isolated tools/h4-forge/test_controller.cpp `
        work/h4-forge-research/isolated/controller_original.cpp `
        -o work/h4-forge-research/isolated/test_controller.exe
    if ($LASTEXITCODE -ne 0) { throw 'Controller test build failed' }
    & work/h4-forge-research/isolated/test_controller.exe 2>&1 |
        Tee-Object work/h4-forge-research/isolated/controller-test.log
    if ($LASTEXITCODE -ne 0) { throw 'Controller test failed' }
    & 'C:/Program Files/LLVM/bin/clang++.exe' -std=c++23 -DREX_PLATFORM_WINDOWS=1 `
        -Iwork/rexglue-sdk/include -Iwork/rexglue-sdk/thirdparty/simde `
        -Iwork/rexglue-sdk/thirdparty/fmt/include -Iwork/rexglue-sdk/thirdparty/spdlog/include `
        -Iwork/h4-forge-research/isolated tools/h4-forge/test_activation.cpp `
        work/h4-forge-research/isolated/activation_original.cpp `
        -o work/h4-forge-research/isolated/test_activation.exe
    if ($LASTEXITCODE -ne 0) { throw 'Activation test build failed' }
    & work/h4-forge-research/isolated/test_activation.exe 2>&1 |
        Tee-Object work/h4-forge-research/isolated/activation-test.log
    if ($LASTEXITCODE -ne 0) { throw 'Activation test failed' }
} finally {
    $env:TEMP = $priorTemp
    $env:TMP = $priorTmp
    Pop-Location
}
