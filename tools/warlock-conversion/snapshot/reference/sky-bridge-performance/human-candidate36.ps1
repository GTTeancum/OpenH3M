# Normal shared game; user controls it. No input harness, captures, or shutdown timer.
param([switch]$Run)
$ErrorActionPreference = 'Stop'
$repo = 'C:/X360/ISOs/H3M/.local/OpenH3M-source'
Push-Location -LiteralPath $repo
try {
    if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { throw 'A game is already running.' }
    $record = Get-Content -Raw tools/warlock-conversion/snapshot/reference/sky-bridge-performance/candidate36-install-result.json | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $record.target).Hash.ToLowerInvariant() -ne $record.sha256) { throw 'Sky Bridge candidate changed.' }
    foreach ($entry in $record.runtime_hashes.PSObject.Properties) {
        if ((Get-FileHash -LiteralPath $entry.Name).Hash.ToLowerInvariant() -ne $entry.Value) { throw 'Runtime or bootstrap changed; review before launch.' }
    }
    if (-not $Run) { Write-Output 'Candidate 36 and shared runtime verified; no game launched.'; return }
    $runDir = Join-Path $repo ('work/sky-bridge/human-candidate36-' + (Get-Date -Format yyyyMMdd-HHmmss))
    New-Item -ItemType Directory -Path $runDir | Out-Null
    $logPath = Join-Path $runDir 'runtime.log'
    $arguments = @("--log_file=$logPath",'--log_level=info','--log_max_file_size_mb=20','--log_max_files=12',
        '--d3d12_log_present_timing=true','--d3d12_present_timing_end_ms=3600000')
    $oldTemp = $env:TEMP; $oldTmp = $env:TMP
    try {
        $env:TEMP = Join-Path $repo '.local/build-temp'; $env:TMP = $env:TEMP
        $child = Start-Process -FilePath C:/X360/ISOs/H3M/OpenH3M.exe -ArgumentList $arguments -WorkingDirectory $repo -WindowStyle Hidden -PassThru
        $launch = [ordered]@{pid=$child.Id; executable='C:/X360/ISOs/H3M/OpenH3M.exe'; arguments=$arguments;
            map_sha256=$record.sha256; started_utc=(Get-Date).ToUniversalTime().ToString('o');
            mode='Human controls; no harness/captures/shutdown timer'; log=$logPath}
        $launch | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runDir 'launch.json')
        $launch | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath work/sky-bridge/candidate36-human-latest.json
        Write-Output "Candidate 36 launched in shared game: PID $($child.Id). No automatic shutdown. Log: $logPath"
    } finally { $env:TEMP=$oldTemp; $env:TMP=$oldTmp }
} finally { Pop-Location }
