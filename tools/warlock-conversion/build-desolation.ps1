param([ValidateRange(1,9999)][int]$Candidate = 1)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$python = 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe'
$sourcePack = Join-Path $repo 'work/desolation/source/Halo 3 Desolation/halo3'
$candidatePath = Join-Path $repo ".local/desolation/candidate$Candidate"
& $python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
 --project $repo --desolation --slot zanzibar `
 --source "$sourcePack/maps/s3d_waterfall.map" `
 --basis C:/X360/ISOs/H3M/maps/zanzibar.map --xex C:/X360/ISOs/H3M/default.xex `
 --disc-maps C:/X360/ISOs/H3M/maps --sound-bank "$sourcePack/fmod/pc/sfx.fsb" `
 --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe `
 --output "$candidatePath/zanzibar.map" --report "$candidatePath/build.json"
exit $LASTEXITCODE
