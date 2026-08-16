param(
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $projectRoot "out\build\win-amd64-release\halo3mp.exe"
$gameDataRoot = Join-Path $projectRoot "..\work\gamedata"

if (-not (Test-Path -LiteralPath $exe)) {
    throw "Missing executable: $exe. Build first with: cmake --build --preset win-amd64-release"
}

if (-not (Test-Path -LiteralPath $gameDataRoot)) {
    throw "Missing game data root: $gameDataRoot"
}

$args = @(
    "--game_data_root", $gameDataRoot,
    "--gpu_plugin", "xenos",
    "--no-fullscreen",
    "--window_width", "1280",
    "--window_height", "720",
    "--gpu_allow_invalid_fetch_constants=true"
)

if ($SmokeTest) {
    $args += @(
        "--input_script=45000:UP,46200:UP,48000:A,56000:A,64000:A,72000:A",
        "--input_script_hold=260"
    )
}

Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory (Split-Path -Parent $exe)
