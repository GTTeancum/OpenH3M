param([Parameter(Mandatory)][string]$InputDirectory)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$inputRoot = [IO.Path]::GetFullPath($InputDirectory)
if (-not $inputRoot.StartsWith($repo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Lightmap artifacts must remain inside the repository'
}
Set-Location -LiteralPath $repo
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$dll = Join-Path $repo 'work/forge-world/tools/tagtool/TagTool.dll'
$null = [Reflection.Assembly]::LoadFrom($dll)
Add-Type -Path (Join-Path $PSScriptRoot 'ReachMccLightmapBridge.cs') -ReferencedAssemblies @(
    $dll, (Join-Path $PSHOME 'ref/System.Collections.dll'),
    (Join-Path $PSHOME 'ref/System.Console.dll')) -CompilerOptions '/unsafe','/nowarn:1701'
$meta = Get-Content (Join-Path $inputRoot 'input.json') -Raw | ConvertFrom-Json
$direction = [IO.File]::ReadAllBytes((Join-Path $inputRoot 'direction.bc5'))
$intensity = [IO.File]::ReadAllBytes((Join-Path $inputRoot 'intensity.bc3'))
$timer = [Diagnostics.Stopwatch]::StartNew()
$result = [ReachMccLightmapBridge]::Convert($direction, $intensity, $meta.width, $meta.height, $meta.brightness)
[IO.File]::WriteAllBytes((Join-Path $inputRoot 'linear-sh.bc3'), $result.LinearSH)
[IO.File]::WriteAllBytes((Join-Path $inputRoot 'dominant-intensity.bc3'), $result.Intensity)
$report = [ordered]@{
    source=$meta.source; width=$result.Width; height=$result.Height; max_l=$result.MaxLs;
    linear_sh_bytes=$result.LinearSH.Length; intensity_bytes=$result.Intensity.Length;
    linear_sh_sha256=(Get-FileHash (Join-Path $inputRoot 'linear-sh.bc3')).Hash;
    intensity_sha256=(Get-FileHash (Join-Path $inputRoot 'dominant-intensity.bc3')).Hash;
    converter_sha256=(Get-FileHash $dll).Hash; elapsed_seconds=$timer.Elapsed.TotalSeconds;
    scope='Reference VMF-to-SH conversion and compression; linear BC3 arrays not yet installed/tiled into native map'
}
$report | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $inputRoot 'conversion.json')
$report | ConvertTo-Json -Depth 5
