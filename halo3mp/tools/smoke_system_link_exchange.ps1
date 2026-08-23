param(
    [ValidateRange(70, 900)]
    [int]$HostDurationSec = 160,
    [ValidateRange(70, 900)]
    [int]$FindDurationSec = 86,
    [ValidateRange(60, 300)]
    [int]$FindStartDelaySec = 67
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runScript = Join-Path $projectRoot "run_windowed.ps1"
$analyzer = Join-Path $projectRoot "tools\analyze_system_link_exchange.ps1"
if (Get-Process halo3mp -ErrorAction SilentlyContinue) {
    throw "Refusing to start while halo3mp is already running."
}

$hostArguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"' + $runScript + '"'),
    "-SystemLinkProbe",
    "-SystemLinkProbeRole", "Host",
    "-SystemLinkProbeDurationSec", "$HostDurationSec",
    "-Headless",
    "-NoCapture"
)
$hostRunner = Start-Process powershell.exe -ArgumentList $hostArguments `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

try {
    Start-Sleep -Seconds $FindStartDelaySec
    & $runScript -SystemLinkProbe -SystemLinkProbeRole Find `
        -SystemLinkProbeDurationSec $FindDurationSec -Headless -NoCapture
    $hostRunner.WaitForExit()
    if ($hostRunner.ExitCode -ne 0) {
        throw "System Link host probe failed with exit code $($hostRunner.ExitCode)."
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $analyzer
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    if (-not $hostRunner.HasExited) {
        $hostRunner.WaitForExit()
    }
}
