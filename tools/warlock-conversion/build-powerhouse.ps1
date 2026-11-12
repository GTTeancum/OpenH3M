param(
 [string]$OutputMap = 'work/powerhouse/zanzibar-01.map',
 [string]$Report = 'work/powerhouse/build-01.json',
 [ValidateRange(0,8)][int]$AmbientQuarterStops = 0,
 [ValidateSet(0,0.125,0.25,0.5)][double]$RoomFill = 0
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$oldTemp = $env:TEMP
$oldTmp = $env:TMP
$oldWaterShaders = $env:OPENH3M_POWERHOUSE_WATER_SHADER_DIR
$oldSplashShaders = $env:OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR
$oldConcreteShaders = $env:OPENH3M_POWERHOUSE_CONCRETE_SHADER_DIR
$oldGrateShaders = $env:OPENH3M_POWERHOUSE_GRATE_SHADER_DIR
$oldWindowShaders = $env:OPENH3M_POWERHOUSE_WINDOW_SHADER_DIR
$oldOpaqueGrateShaders = $env:OPENH3M_POWERHOUSE_OPAQUE_GRATE_SHADER_DIR
$oldCorrugatedShaders = $env:OPENH3M_POWERHOUSE_CORRUGATED_SHADER_DIR
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$python = 'C:\Users\smmel\AppData\Local\Programs\Python\Python312\python.exe'
$pack = 'D:/SteamLibrary/steamapps/workshop/content/976730/3003239190'
try {
 if (-not $env:OPENH3M_POWERHOUSE_WATER_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse water shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_WATER_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-water-shaders'
 }
if (-not $env:OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind splash
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse splash shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-splash-shaders'
 }
 if (-not $env:OPENH3M_POWERHOUSE_CONCRETE_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind concrete
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse concrete shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_CONCRETE_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-concrete-shaders'
 }
 if (-not $env:OPENH3M_POWERHOUSE_GRATE_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind grate
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse grate shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_GRATE_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-grate-shaders'
 }
 if (-not $env:OPENH3M_POWERHOUSE_WINDOW_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind window
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse window shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_WINDOW_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-window-shaders'
 }
 if (-not $env:OPENH3M_POWERHOUSE_OPAQUE_GRATE_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind opaque-grate
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse opaque grate shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_OPAQUE_GRATE_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-opaque-grate-shaders'
 }
 if (-not $env:OPENH3M_POWERHOUSE_CORRUGATED_SHADER_DIR) {
  & $python -B tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind corrugated
  if ($LASTEXITCODE -ne 0) { throw 'Powerhouse corrugated shader preparation failed; see compiler output.' }
  $env:OPENH3M_POWERHOUSE_CORRUGATED_SHADER_DIR = Join-Path $repo 'work/powerhouse/native-corrugated-shaders'
 }
 & $python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
 --project C:/X360/ISOs/H3M --slot zanzibar `
 --powerhouse-ambient-quarter-stops $AmbientQuarterStops `
 --powerhouse-room-fill $RoomFill `
 --mcc-shared "$pack/halo3/maps/shared.map" --source "$pack/maps/s3d_powerhouse.map" `
 --basis C:/X360/ISOs/H3M/maps/zanzibar.map --xex C:/X360/ISOs/H3M/default.xex `
 --sound-bank "$pack/halo3/fmod/pc/sfx.fsb" `
 --additional-sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
 --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe `
 --output $OutputMap --report $Report
 $buildExitCode = $LASTEXITCODE
} finally {
 $env:OPENH3M_POWERHOUSE_WATER_SHADER_DIR = $oldWaterShaders
 $env:OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR = $oldSplashShaders
 $env:OPENH3M_POWERHOUSE_CONCRETE_SHADER_DIR = $oldConcreteShaders
 $env:OPENH3M_POWERHOUSE_GRATE_SHADER_DIR = $oldGrateShaders
 $env:OPENH3M_POWERHOUSE_WINDOW_SHADER_DIR = $oldWindowShaders
 $env:OPENH3M_POWERHOUSE_OPAQUE_GRATE_SHADER_DIR = $oldOpaqueGrateShaders
 $env:OPENH3M_POWERHOUSE_CORRUGATED_SHADER_DIR = $oldCorrugatedShaders
 $env:TEMP = $oldTemp
 $env:TMP = $oldTmp
}
exit $buildExitCode
