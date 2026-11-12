$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$python = 'C:\Users\smmel\AppData\Local\Programs\Python\Python312\python.exe'
& $python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
 --project C:/X360/ISOs/H3M --slot zanzibar `
 --source D:/SteamLibrary/steamapps/workshop/content/976730/2898979693/maps/lockoutfix.map `
 --basis C:/X360/ISOs/H3M/maps/zanzibar.map --xex C:/X360/ISOs/H3M/default.xex `
 --sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
 --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe `
 --output work/lockout/zanzibar-01.map --report work/lockout/build-01.json
exit $LASTEXITCODE
