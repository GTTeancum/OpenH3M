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
    "--render_target_path_d3d12=rov",
    "--gpu_allow_invalid_fetch_constants=true",
    "--halo3mp_title_fps=true",
    "--keyboard_controller=true",
    "--keyboard_controller_log=true"
)

if ($SmokeTest) {
    $capturePath = Join-Path (Split-Path -Parent $exe) "halo3mp_smoke_zanzibar.bmp"
    $args += @(
        "--keyboard_controller=false",
        "--keyboard_controller_log=false",
        "--input_script=30596:UP+146,32830:UP+64,34631:A+238,41918:A+82,55366:LSRIGHT+90,55456:BACK+154,55756:RB+129,56769:B+131,57289:LSRIGHT+171,57460:BACK+91,57680:RB+85,57990:A+150,58384:Y+220,58621:BACK+47,124304:LSUP+148,124548:RB+110,125572:B+168,126606:LSRIGHT+132,127011:A+88,128091:LSDOWN+190,128173:A+155,130226:LSDOWN+125,130758:LSRIGHT+127,131138:LSLEFT+40,131331:A+194,132139:RB+151,132901:A+85,133179:LSUP+217,133441:RB+127,133568:A+127,133781:LSLEFT+87,133890:LSRIGHT+131,134021:A+104,134256:LSLEFT+149,134405:A+129,134554:LSUP+127,134681:BACK+127,138970:A+169",
        "--halo3mp_capture_guest_output_after_ms=152000",
        "--halo3mp_capture_guest_output_path=$capturePath"
    )
}

Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory (Split-Path -Parent $exe)
