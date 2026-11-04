# Private, bounded, process-local replay; never modifies the shared runtime.
param([Parameter(Mandatory=$true)][string]$RunDirectory,[switch]$StageProbe,[switch]$PresentedProbe,[switch]$RegionProbe,[string]$PixelRegion='0.54,0.255,0.93,0.425')
$ErrorActionPreference='Stop'
$repo='C:/X360/ISOs/H3M/.local/OpenH3M-source'
Set-Location -LiteralPath $repo
$run=(Resolve-Path -LiteralPath $RunDirectory).Path
if (-not $run.StartsWith(($repo.Replace('/','\')+'\work\sky-bridge\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Run is outside Sky Bridge work directory' }
if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { throw 'A game is already running' }
if (Test-Path -LiteralPath (Join-Path $run 'draws.bin')) { throw 'Run already contains evidence' }
$hashes=Get-Content -Raw -LiteralPath (Join-Path $run 'runtime-hashes.json') | ConvertFrom-Json
foreach ($entry in $hashes.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $run ('runtime/'+$entry.Name))).Hash.ToLowerInvariant() -ne $entry.Value) { throw 'Private runtime changed' }
}
$env:TEMP=Join-Path $repo '.local/build-temp';$env:TMP=$env:TEMP
$env:OPENH3M_SKY_REPRO_DIR=$run
$env:OPENH3M_SKY_TRACE_DIR=$run
$env:OPENH3M_SKY_TRACE_TARGETS='1'
$env:OPENH3M_SKY_PIXEL_PROBE_DIR=$run
$env:OPENH3M_SKY_PIXEL_PROBE_REGION=$PixelRegion
if($StageProbe) { $env:OPENH3M_SKY_STAGE_PROBE_DIR=$run }
else { Remove-Item Env:OPENH3M_SKY_STAGE_PROBE_DIR -ErrorAction SilentlyContinue }
if($PresentedProbe) { $env:OPENH3M_SKY_PIXEL_PROBE_PRESENTED='1' }
else { Remove-Item Env:OPENH3M_SKY_PIXEL_PROBE_PRESENTED -ErrorAction SilentlyContinue }
if($RegionProbe) { $env:OPENH3M_SKY_REGION_PROBE_DIR=$run; $env:OPENH3M_SKY_REGION_PROBE_REGION='0.45,0.10,1,0.50' }
else { Remove-Item Env:OPENH3M_SKY_REGION_PROBE_DIR -ErrorAction SilentlyContinue }
& 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B tools/warlock-conversion/snapshot/tools/trace_loading.py `
    --project C:/X360/ISOs/H3M --game C:/X360/ISOs/H3M `
    --exe (Join-Path $run 'runtime/OpenH3M.exe') --expected-exe-sha256 $hashes.'OpenH3M.exe' `
    --slot zanzibar --dlc-payload (Join-Path $repo 'work/sky-bridge/payload-32') --dlc-map sky_bridge `
    --cache-root (Join-Path $run 'cache') --exclusive-input --quiet-timing --seconds 180
if ($LASTEXITCODE -ne 0) { throw 'Private reproduction failed; inspect repository logs' }
