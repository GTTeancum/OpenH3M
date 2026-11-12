$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$python = 'C:\Users\smmel\AppData\Local\Programs\Python\Python312\python.exe'
$pack = 'D:/SteamLibrary/steamapps/workshop/content/976730/3500400217'
& $python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
 --project C:/X360/ISOs/H3M --slot zanzibar `
 --mcc-shared "$pack/halo3/maps/shared.map" --source "$pack/maps/rodentia.map" `
 --basis C:/X360/ISOs/H3M/maps/zanzibar.map --xex C:/X360/ISOs/H3M/default.xex `
 --sound-bank "$pack/halo3/fmod/pc/sfx.h2maps.fsb" `
 --additional-sound-bank "$pack/halo3/fmod/pc/sfx.js_kestrel.fsb" `
 --additional-sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
 --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe `
 --output work/rodentia/zanzibar-01.map --report work/rodentia/build-01.json
exit $LASTEXITCODE
