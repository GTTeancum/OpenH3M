# Rebuild the host runtime only; uses the shared game executable and map cache.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$sdk = Join-Path $repo 'work/rexglue-sdk'
if (-not (Test-Path (Join-Path $sdk '.git'))) { throw 'SDK source checkout is missing; see FRAME-PACING.md.' }
$sdkCommit = git -C $sdk rev-parse HEAD
if ($sdkCommit -ne 'c94f5ebdcb3c9d1a460ca48e04f9758448f8d518') { throw 'Unexpected SDK revision.' }
$oldTemp = $env:TEMP; $oldTmp = $env:TMP; $oldPath = $env:PATH
Push-Location $repo
try {
    $env:TEMP = Join-Path $repo 'work/build-temp'
    $env:TMP = $env:TEMP
    New-Item -ItemType Directory -Force $env:TEMP | Out-Null
    $env:PATH = 'C:\Program Files\LLVM\bin;C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;' + $oldPath
    $patches = @('d3d12-index-buffer-cache', 'd3d12-vertex-residency', 'input-script',
        'local-users', 'local-user-direct', 'memexport-performance', 'presenter-host-tools',
        'windows-mspack-path', 'host-frame-pacing')
    foreach ($name in $patches) {
        $patch = Join-Path $repo "halo3mp/patches/rexglue-sdk-$name.patch"
        git -C $sdk apply --ignore-space-change --reverse --check $patch 2>$null
        if ($LASTEXITCODE -ne 0) {
            git -C $sdk apply --ignore-space-change --check $patch
            if ($LASTEXITCODE -ne 0) { throw "Cannot apply $name to SDK checkout." }
            git -C $sdk apply --ignore-space-change $patch
            if ($LASTEXITCODE -ne 0) { throw "Failed applying $name." }
        }
    }
    cmake -S $sdk -B "$sdk/out/pacing-release" -G Ninja -DCMAKE_BUILD_TYPE=Release `
        -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ `
        -DCMAKE_C_FLAGS=-march=x86-64-v2 -DCMAKE_CXX_FLAGS=-march=x86-64-v2 `
        -DREXGLUE_ENABLE_TRACY=OFF -DREXGLUE_BUILD_TESTS=OFF -DREXGLUE_USE_VULKAN=ON `
        -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON "-DCMAKE_INSTALL_PREFIX=$sdk/out/install-pacing" `
        *> work/runtime-configure.log
    if ($LASTEXITCODE -ne 0) { throw 'Configuration failed; see work/runtime-configure.log.' }
    cmake --build "$sdk/out/pacing-release" --target rexruntime --parallel 4 *> work/runtime-build.log
    if ($LASTEXITCODE -ne 0) { throw 'Build failed; see work/runtime-build.log.' }
} finally {
    $env:TEMP = $oldTemp; $env:TMP = $oldTmp; $env:PATH = $oldPath
    Pop-Location
}
