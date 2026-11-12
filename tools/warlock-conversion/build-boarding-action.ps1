param([string]$OutputMap='work/boarding-action/zanzibar-02.map', [string]$Report='work/boarding-action/build-02.json')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$python = 'C:\Users\smmel\AppData\Local\Programs\Python\Python312\python.exe'
$pack = 'D:/SteamLibrary/steamapps/workshop/content/976730/2962955878'
& $python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
 --project C:/X360/ISOs/H3M --slot zanzibar `
 --source "$pack/maps/boardingaction.map" `
 --basis C:/X360/ISOs/H3M/maps/zanzibar.map --xex C:/X360/ISOs/H3M/default.xex `
 --sound-bank "$pack/halo3/fmod/pc/sfx.fsb" `
 --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe `
 --output $OutputMap --report $Report
exit $LASTEXITCODE
