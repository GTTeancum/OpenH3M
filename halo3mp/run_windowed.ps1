param(
    [switch]$SmokeTest,
    [switch]$SplitScreenStress
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

if ($SmokeTest -and $SplitScreenStress) {
    throw "Choose either -SmokeTest or -SplitScreenStress, not both."
}

$zanzibarSmokeRoute = @(
    "30596:UP+146",
    "32830:UP+64",
    "34631:A+238",
    "41918:A+82",
    "55366:LSRIGHT+90",
    "55456:BACK+154",
    "55756:RB+129",
    "56769:B+131",
    "57289:LSRIGHT+171",
    "57460:BACK+91",
    "57680:RB+85",
    "57990:A+150",
    "58384:Y+220",
    "58621:BACK+47",
    "124304:LSUP+148",
    "124548:RB+110",
    "125572:B+168",
    "126606:LSRIGHT+132",
    "127011:A+88",
    "128091:LSDOWN+190",
    "128173:A+155",
    "130226:LSDOWN+125",
    "130758:LSRIGHT+127",
    "131138:LSLEFT+40",
    "131331:A+194",
    "132139:RB+151",
    "132901:A+85",
    "133179:LSUP+217",
    "133441:RB+127",
    "133568:A+127",
    "133781:LSLEFT+87",
    "133890:LSRIGHT+131",
    "134021:A+104",
    "134256:LSLEFT+149",
    "134405:A+129",
    "134554:LSUP+127",
    "134681:BACK+127",
    "138970:A+169"
)

$customGamesRoute = @(
    "33000:DOWN+120",
    "35000:A+160",
    "47000:A+220"
)

$splitScreenStressRoute = @(
    "78000:LSUP+4500@0",
    "78000:RT+4500@0",
    "78000:RSRIGHT+1500@0",
    "78200:LSRIGHT+4500@1",
    "78200:RT+4500@1",
    "78200:RSLEFT+1500@1",
    "78400:LSDOWN+4500@2",
    "78400:RT+4500@2",
    "78400:RSUP+1500@2",
    "78600:LSLEFT+4500@3",
    "78600:RT+4500@3",
    "78600:RSDOWN+1500@3",
    "84000:LSRIGHT+4500@0",
    "84000:RT+4500@0",
    "84200:LSDOWN+4500@1",
    "84200:RT+4500@1",
    "84400:LSLEFT+4500@2",
    "84400:RT+4500@2",
    "84600:LSUP+4500@3",
    "84600:RT+4500@3",
    "90000:LSLEFT+4500@0",
    "90000:RT+4500@0",
    "90200:LSUP+4500@1",
    "90200:RT+4500@1",
    "90400:LSRIGHT+4500@2",
    "90400:RT+4500@2",
    "90600:LSDOWN+4500@3",
    "90600:RT+4500@3"
)

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
        "--input_script=$($zanzibarSmokeRoute -join ',')",
        "--halo3mp_capture_guest_output_after_ms=152000",
        "--halo3mp_capture_guest_output_path=$capturePath"
    )
}

if ($SplitScreenStress) {
    $capturePath = Join-Path (Split-Path -Parent $exe) "halo3mp_smoke_splitscreen_stress.bmp"
    $script = $customGamesRoute + $splitScreenStressRoute
    $args += @(
        "--keyboard_controller=false",
        "--keyboard_controller_log=false",
        "--xam_local_user_count=4",
        "--halo3mp_log_fps=true",
        "--input_script=$($script -join ',')",
        "--halo3mp_capture_guest_output_after_ms=98000",
        "--halo3mp_capture_guest_output_path=$capturePath"
    )
}

Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory (Split-Path -Parent $exe)
