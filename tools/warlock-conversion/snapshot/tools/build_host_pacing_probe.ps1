$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$output = Join-Path $repo 'work/pacing-probe'
$temp = Join-Path $output 'temp'
New-Item -ItemType Directory -Force $temp | Out-Null
$sdk = 'C:\Program Files (x86)\Windows Kits\10'
$version = '10.0.26100.0'
$msvc = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\include'
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
Push-Location $repo
try {
    $env:TEMP = $temp
    $env:TMP = $temp
    & 'C:\Program Files\LLVM\bin\clang++.exe' --target=x86_64-pc-windows-msvc `
        -shared -O2 -fno-exceptions -fno-rtti -fno-stack-protector -nostdlib `
        "-I$msvc" "-I$sdk\Include\$version\shared" "-I$sdk\Include\$version\um" `
        "-I$sdk\Include\$version\ucrt" (Join-Path $PSScriptRoot 'host_pacing_probe.cpp') `
        -o (Join-Path $output 'host_pacing_probe.dll') '-Wl,/entry:DllMain' '-Wl,/nodefaultlib' `
        "$sdk\Lib\$version\um\x64\kernel32.lib"
    if ($LASTEXITCODE -ne 0) { throw "Probe build failed: $LASTEXITCODE" }
} finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    Pop-Location
}
