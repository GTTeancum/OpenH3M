param(
    [ValidateRange(1, 4)]
    [int]$SplitPlayers = 4,
    [switch]$FastLocalUserState,
    [switch]$FastLocalUserStateCompare,
    [switch]$TraceXamUser,
    [switch]$NoJoinStarts,
    [ValidateRange(640, 8192)]
    [int]$VideoModeWidth = 1280,
    [ValidateRange(480, 8192)]
    [int]$VideoModeHeight = 720,
    [int]$RunSeconds = 152,
    [string[]]$ExtraArgs = @()
)

$ErrorActionPreference = "Stop"

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsRoot
$buildRoot = Join-Path $projectRoot "out\build\win-amd64-release"
$runner = Join-Path $projectRoot "run_windowed.ps1"
$analyzer = Join-Path $toolsRoot "analyze_smoke_log.ps1"
$preflightCapture = Join-Path $buildRoot "halo3mp_smoke_splitscreen_stress.png"

function Stop-Halo3mp {
    Get-Process halo3mp -ErrorAction SilentlyContinue | Stop-Process -Force
}

function Wait-ForFile {
    param(
        [string]$Path,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $Path) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
    throw "Timed out waiting for capture: $Path"
}

function Get-SelectedMainMenuRow {
    param([string]$Path)

    Add-Type -AssemblyName System.Drawing
    $bitmap = [System.Drawing.Bitmap]::new($Path)
    try {
        $rows = [ordered]@{
            Matchmaking = 416
            CustomGames = 449
            Forge = 474
            Theater = 499
        }

        $scores = @{}
        foreach ($row in $rows.GetEnumerator()) {
            $score = 0
            for ($y = $row.Value - 10; $y -le $row.Value + 10; ++$y) {
                for ($x = 72; $x -le 386; $x += 2) {
                    $pixel = $bitmap.GetPixel($x, $y)
                    if ($pixel.R -gt 60 -and $pixel.G -gt 30 -and $pixel.G -lt 170 -and
                        $pixel.B -lt 140 -and $pixel.R -gt ($pixel.B + 20) -and
                        $pixel.G -gt ($pixel.B + 5)) {
                        ++$score
                    }
                }
            }
            $scores[$row.Name] = $score
        }

        $best = $scores.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1
        if (-not $best -or $best.Value -lt 50) {
            $summary = ($scores.GetEnumerator() | Sort-Object Name | ForEach-Object {
                "{0}={1}" -f $_.Name, $_.Value
            }) -join " "
            throw "Could not identify highlighted main-menu row from $Path ($summary)"
        }

        return $best.Name
    } finally {
        $bitmap.Dispose()
    }
}

function Get-CustomGamesRouteForRow {
    param([string]$Row)

    switch ($Row) {
        "Matchmaking" { return @("45000:DOWN+220", "46000:A+250", "68000:A+250") }
        "CustomGames" { return @("46000:A+250", "68000:A+250") }
        "Forge" { return @("45000:UP+220", "46000:A+250", "68000:A+250") }
        "Theater" { return @("45000:UP+220", "45500:UP+220", "46000:A+250", "68000:A+250") }
        default { throw "No route for main-menu row: $Row" }
    }
}

Stop-Halo3mp
Remove-Item -LiteralPath $preflightCapture -Force -ErrorAction SilentlyContinue

$preflightArgs = @{
    SplitScreenStress = $true
    Capture = $true
    CaptureAfterMs = 44000
    SplitPlayers = $SplitPlayers
    VideoModeWidth = $VideoModeWidth
    VideoModeHeight = $VideoModeHeight
    LaunchRouteOverride = "90000:A+1"
}
& $runner @preflightArgs
Start-Sleep -Seconds 48
Stop-Halo3mp
Wait-ForFile -Path $preflightCapture

$selectedRow = Get-SelectedMainMenuRow -Path $preflightCapture
$route = Get-CustomGamesRouteForRow -Row $selectedRow
$routeText = $route -join ","
Write-Host "PreflightSelectedRow=$selectedRow"
Write-Host "LaunchRoute=$routeText"

$runArgs = @{
    SplitScreenStress = $true
    Capture = $true
    SplitPlayers = $SplitPlayers
    VideoModeWidth = $VideoModeWidth
    VideoModeHeight = $VideoModeHeight
    LaunchRouteOverride = $routeText
}
if ($FastLocalUserState) { $runArgs.FastLocalUserState = $true }
if ($FastLocalUserStateCompare) { $runArgs.FastLocalUserStateCompare = $true }
if ($TraceXamUser) { $runArgs.TraceXamUser = $true }
if ($NoJoinStarts) { $runArgs.NoJoinStarts = $true }
if ($ExtraArgs.Count -gt 0) { $runArgs.ExtraArgs = $ExtraArgs }

$before = Get-ChildItem -Path (Join-Path $buildRoot "logs") -Filter "halo3mp_*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
Write-Host "BeforeLog=$($before.Name)"

& $runner @runArgs
Start-Sleep -Seconds $RunSeconds
Stop-Halo3mp

$latest = Get-ChildItem -Path (Join-Path $buildRoot "logs") -Filter "halo3mp_*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
Write-Host "LatestLog=$($latest.FullName)"
& $analyzer -LogPath $latest.FullName
