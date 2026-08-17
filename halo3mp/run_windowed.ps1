param(
    [switch]$SmokeTest,
    [switch]$OnePlayerStress,
    [switch]$SplitScreenStress,
    [switch]$Capture,
    [switch]$NoCapture,
    [switch]$TraceXamUser,
    [switch]$CleanSmokeUserData,
    [int]$CaptureAfterMs = 0,
    [ValidateRange(640, 8192)]
    [int]$VideoModeWidth = 1280,
    [ValidateRange(480, 8192)]
    [int]$VideoModeHeight = 720,
    [ValidateRange(-1, 5)]
    [int]$AnisotropicOverride = 3,
    [ValidateRange(1, 4)]
    [int]$SplitPlayers = 4,
    [switch]$NoJoinStarts,
    [switch]$FastLocalUserState,
    [switch]$FastLocalUserStateCompare,
    [string]$LaunchRouteOverride = "",
    [string[]]$ExtraArgs = @()
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

if ((@($SmokeTest, $OnePlayerStress, $SplitScreenStress) | Where-Object { $_ }).Count -gt 1) {
    throw "Choose only one of -SmokeTest, -OnePlayerStress, or -SplitScreenStress."
}

$freshCustomGamesRoute = @(
    "46000:A+250",
    "63000:A+250"
)

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
    "45000:DOWN+220",
    "46000:A+250",
    "68000:A+250"
)

$splitCustomGamesRoute = @(
    "45000:DOWN+220",
    "46000:A+250",
    "68000:A+250"
)

function Clear-SmokeUserDataRoot {
    param([string]$Path)

    $buildRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $exe)).Path
    if (Test-Path -LiteralPath $Path) {
        $resolved = (Resolve-Path -LiteralPath $Path).Path
        if (-not $resolved.StartsWith($buildRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean smoke user data outside build root: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$splitScreenJoinInGameRoute = @(
    "95000:START+260@1",
    "95200:START+260@2",
    "95400:START+260@3"
)

$splitScreenStressRoute = @(
    "121000:LSUP+4500@0",
    "121000:RT+4500@0",
    "121000:RSRIGHT+1500@0",
    "121200:LSRIGHT+4500@1",
    "121200:RT+4500@1",
    "121200:RSLEFT+1500@1",
    "121400:LSDOWN+4500@2",
    "121400:RT+4500@2",
    "121400:RSUP+1500@2",
    "121600:LSLEFT+4500@3",
    "121600:RT+4500@3",
    "121600:RSDOWN+1500@3",
    "127000:LSRIGHT+4500@0",
    "127000:RT+4500@0",
    "127200:LSDOWN+4500@1",
    "127200:RT+4500@1",
    "127400:LSLEFT+4500@2",
    "127400:RT+4500@2",
    "127600:LSUP+4500@3",
    "127600:RT+4500@3",
    "133000:LSLEFT+4500@0",
    "133000:RT+4500@0",
    "133200:LSUP+4500@1",
    "133200:RT+4500@1",
    "133400:LSRIGHT+4500@2",
    "133400:RT+4500@2",
    "133600:LSDOWN+4500@3",
    "133600:RT+4500@3"
)

$onePlayerStressRoute = @(
    "97000:LSUP+4500@0",
    "97000:RT+4500@0",
    "97000:RSRIGHT+1500@0",
    "103000:LSRIGHT+4500@0",
    "103000:RT+4500@0",
    "109000:LSLEFT+4500@0",
    "109000:RT+4500@0"
)

function Select-RouteForPlayers {
    param(
        [string[]]$Route,
        [int]$PlayerCount
    )

    @($Route | Where-Object {
        if ($_ -match "@([0-3])(?:\\+\\d+)?$") {
            return ([int]$Matches[1]) -lt $PlayerCount
        }
        return $true
    })
}

function Get-LaunchRoute {
    param([string[]]$DefaultRoute)

    if (-not [string]::IsNullOrWhiteSpace($LaunchRouteOverride)) {
        return @($LaunchRouteOverride -split "," | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    }

    return $DefaultRoute
}

$args = @(
    "--game_data_root", $gameDataRoot,
    "--gpu_plugin", "xenos",
    "--no-fullscreen",
    "--window_width", "1280",
    "--window_height", "720",
    "--video_mode_width", "$VideoModeWidth",
    "--video_mode_height", "$VideoModeHeight",
    "--anisotropic_override=$AnisotropicOverride",
    "--render_target_path_d3d12=rtv",
    "--gamma_render_target_as_unorm16=false",
    "--readback_memexport=false",
    "--gpu_allow_invalid_fetch_constants=true",
    "--halo3mp_title_fps=true",
    "--keyboard_controller=true",
    "--keyboard_controller_log=true"
)

if ($CleanSmokeUserData -and ($SmokeTest -or $OnePlayerStress -or $SplitScreenStress)) {
    $smokeUserDataRoot = Join-Path (Split-Path -Parent $exe) "smoke_user_data"
    Clear-SmokeUserDataRoot -Path $smokeUserDataRoot
    $args += @("--user_data_root=$smokeUserDataRoot")
}

if ($SmokeTest) {
    $capturePath = Join-Path (Split-Path -Parent $exe) "halo3mp_smoke_zanzibar.png"
    $effectiveCaptureAfterMs = if ($CaptureAfterMs -gt 0) { $CaptureAfterMs } else { 152000 }
    $args += @(
        "--keyboard_controller=false",
        "--keyboard_controller_log=false",
        "--input_script_button_state=true",
        "--input_script_keystrokes=true",
        "--input_script_keystrokes_until_ms=65000",
        "--xgi_session_log=true",
        "--halo3mp_log_fps=true",
        "--halo3mp_smoke_route=custom-games-zanzibar-smoke",
        "--halo3mp_smoke_expected_state=custom_games_gameplay_zanzibar",
        "--halo3mp_smoke_players=1",
        "--input_script=$($zanzibarSmokeRoute -join ',')"
    )

    if ($Capture -and -not $NoCapture) {
        $args += @(
            "--halo3mp_capture_guest_output_after_ms=$effectiveCaptureAfterMs",
            "--halo3mp_capture_guest_output_path=$capturePath"
        )
    }
}

if ($OnePlayerStress) {
    $capturePath = Join-Path (Split-Path -Parent $exe) "halo3mp_smoke_oneplayer_stress.png"
    $effectiveCaptureAfterMs = if ($CaptureAfterMs -gt 0) { $CaptureAfterMs } else { 111000 }
    $captureTimesMs = if ($CaptureAfterMs -gt 0) { @("$CaptureAfterMs") } else { @("44000", "55000", "70000", "84000", "111000") }
    $launchRoute = Get-LaunchRoute -DefaultRoute $(if ($CleanSmokeUserData) { $freshCustomGamesRoute } else { $customGamesRoute })
    $script = $launchRoute + $onePlayerStressRoute
    $args += @(
        "--keyboard_controller=false",
        "--keyboard_controller_log=false",
        "--input_script_button_state=true",
        "--input_script_keystrokes=true",
        "--input_script_keystrokes_until_ms=65000",
        "--xgi_session_log=true",
        "--halo3mp_log_fps=true",
        "--halo3mp_smoke_route=one-player-stress",
        "--halo3mp_smoke_expected_state=custom_games_gameplay_zanzibar_one_player_moving_firing",
        "--halo3mp_smoke_players=1",
        "--input_script=$($script -join ',')"
    )

    if ($Capture -and -not $NoCapture) {
        $args += @(
            "--halo3mp_capture_guest_output_after_ms=$effectiveCaptureAfterMs",
            "--halo3mp_capture_guest_output_times_ms=$($captureTimesMs -join ',')",
            "--halo3mp_capture_guest_output_path=$capturePath"
        )
    }
}

if ($SplitScreenStress) {
    $capturePath = Join-Path (Split-Path -Parent $exe) "halo3mp_smoke_splitscreen_stress.png"
    $effectiveCaptureAfterMs = if ($CaptureAfterMs -gt 0) { $CaptureAfterMs } else { 130000 }
    $captureTimesMs = if ($CaptureAfterMs -gt 0) { @("$CaptureAfterMs") } else { @("44000", "55000", "70000", "84000", "102000", "130000") }
    $routeName = "{0}-player-splitscreen-stress" -f $SplitPlayers
    $launchRoute = Get-LaunchRoute -DefaultRoute $(if ($CleanSmokeUserData) { $freshCustomGamesRoute } else { $splitCustomGamesRoute })
    $joinRoute = if ($NoJoinStarts) { @() } else {
        Select-RouteForPlayers -Route $splitScreenJoinInGameRoute -PlayerCount $SplitPlayers
    }
    $script = $launchRoute +
        $joinRoute +
        (Select-RouteForPlayers -Route $splitScreenStressRoute -PlayerCount $SplitPlayers)
    $activationMs = @("0", "90000", "90200", "90400") | Select-Object -First $SplitPlayers
    $args += @(
        "--keyboard_controller=false",
        "--keyboard_controller_log=false",
        "--input_script_button_state=true",
        "--input_script_keystrokes=true",
        "--input_script_keystrokes_until_ms=65000",
        "--xam_local_user_count=$SplitPlayers",
        "--xam_local_user_activation_ms=$($activationMs -join ',')",
        "--xgi_session_log=true",
        "--halo3mp_log_fps=true",
        "--halo3mp_smoke_route=$routeName",
        "--halo3mp_smoke_expected_state=custom_games_gameplay_zanzibar_$($SplitPlayers)_players_moving_firing",
        "--halo3mp_smoke_players=$SplitPlayers",
        "--input_script=$($script -join ',')"
    )

    if ($Capture -and -not $NoCapture) {
        $args += @(
            "--halo3mp_capture_guest_output_after_ms=$effectiveCaptureAfterMs",
            "--halo3mp_capture_guest_output_times_ms=$($captureTimesMs -join ',')",
            "--halo3mp_capture_guest_output_path=$capturePath"
        )
    }
}

if ($TraceXamUser) {
    $args += @("--xam_user_summary_interval_ms=1000")
}

if ($FastLocalUserState) {
    $args += @("--halo3mp_fast_local_user_state=true")
}

if ($FastLocalUserStateCompare) {
    $args += @("--halo3mp_fast_local_user_state_compare=true")
}

$args += $ExtraArgs

$startProcessArgs = @{
    FilePath = $exe
    ArgumentList = $args
    WorkingDirectory = (Split-Path -Parent $exe)
    PassThru = $true
}
if ($SmokeTest -or $OnePlayerStress -or $SplitScreenStress) {
    $startProcessArgs.WindowStyle = "Hidden"
}

$process = Start-Process @startProcessArgs
$process.PriorityClass = "Normal"
