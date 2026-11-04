# Run Install/Restore only after user authorizes this one shared DLL replacement.
param([ValidateSet('Validate','Install','Restore','Launch','Arm')][string]$Action='Validate', [switch]$PixelProbe)
$ErrorActionPreference='Stop'
$repo='C:/X360/ISOs/H3M/.local/OpenH3M-source'
Push-Location -LiteralPath $repo
try {
    $reference='tools/warlock-conversion/snapshot/reference/sky-bridge-performance'
    $manifest=if ($PixelProbe) { 'sky-pixel-probe-build.json' } else { 'sky-draw-trace-build.json' }
    $record=Get-Content -Raw "$reference/$manifest" | ConvertFrom-Json
    $build=Join-Path $repo $(if ($PixelProbe) { 'work/sky-bridge/pixel-probe-build' } else { 'work/sky-bridge/draw-trace-build' })
    $installed=$record.installed_path
    function Hash($path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
    if ((Hash "$build/original-rexgpu-xenos.dll") -ne $record.original_sha256) { throw 'Backup changed' }
    if ((Hash "$build/trace-rexgpu-xenos.dll") -ne $record.diagnostic_sha256) { throw 'Diagnostic changed' }
    $current=Hash $installed
    if ($current -notin @($record.original_sha256,$record.diagnostic_sha256)) { throw 'Shared DLL changed independently' }
    if ($Action -eq 'Validate') { Write-Output 'Backup and diagnostic hashes verified; shared DLL recognized. No changes.'; return }
    if ($Action -in @('Install','Restore','Launch') -and (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue)) { throw 'Game is running; leave human session alone' }
    if ($Action -in @('Install','Restore')) {
        $source=if ($Action -eq 'Install') { "$build/trace-rexgpu-xenos.dll" } else { "$build/original-rexgpu-xenos.dll" }
        $expected=Hash $source
        Copy-Item -LiteralPath $source -Destination $installed
        if ((Hash $installed) -ne $expected) { throw 'Replacement verification failed' }
        Write-Output "$Action verified: $installed"; return
    }
    if ($Action -eq 'Arm') {
        $launch=Get-Content -Raw "$build/latest-launch.json" | ConvertFrom-Json
        $process=Get-Process -Id $launch.pid -ErrorAction Stop
        if ($process.Path -ne 'C:\X360\ISOs\H3M\OpenH3M.exe') { throw 'Target process changed' }
        if ($process.StartTime.ToUniversalTime().Ticks -ne ([datetime]$launch.process_start_utc).ToUniversalTime().Ticks) { throw 'PID was reused' }
        New-Item -ItemType File -Path (Join-Path $launch.trace_directory 'arm') | Out-Null
        Write-Output 'Trace armed. Recording stops automatically; game stays open.'; return
    }
    if ($current -ne $record.diagnostic_sha256) { throw 'Diagnostic is not installed' }
    $baseline=Get-Content -Raw work/sky-bridge/candidate32-install.json | ConvertFrom-Json
    if ((Hash $baseline.map) -ne $baseline.sha256) { throw 'Sky Bridge map changed' }
    foreach ($entry in $baseline.runtime_hashes.PSObject.Properties) {
        if ([IO.Path]::GetFileName($entry.Name) -eq 'rexgpu-xenos.dll') { continue }
        if ((Hash $entry.Name) -ne $entry.Value) { throw "Runtime changed: $($entry.Name)" }
    }
    if ((Hash 'C:/X360/ISOs/H3M/OpenH3M.bootstrap.toml') -ne $baseline.bootstrap_sha256) { throw 'Bootstrap changed' }
    $run=Join-Path $repo ('work/sky-bridge/' + $(if ($PixelProbe) { 'pixel-probe-' } else { 'draw-trace-' }) + (Get-Date -Format yyyyMMdd-HHmmss))
    New-Item -ItemType Directory -Path $run | Out-Null
    $oldTemp=$env:TEMP; $oldTmp=$env:TMP; $oldTrace=$env:OPENH3M_SKY_TRACE_DIR
    $oldProbe=$env:OPENH3M_SKY_PIXEL_PROBE_DIR; $oldTargets=$env:OPENH3M_SKY_TRACE_TARGETS
    try {
        $env:TEMP=Join-Path $repo '.local/build-temp'; $env:TMP=$env:TEMP
        $env:OPENH3M_SKY_TRACE_DIR=$run
        if ($PixelProbe) { $env:OPENH3M_SKY_PIXEL_PROBE_DIR=$run; $env:OPENH3M_SKY_TRACE_TARGETS='1' }
        else { $env:OPENH3M_SKY_PIXEL_PROBE_DIR=$null; $env:OPENH3M_SKY_TRACE_TARGETS=$null }
        $arguments=@("--log_file=$run/runtime.log",'--log_level=info','--log_max_file_size_mb=20','--log_max_files=12')
        $child=Start-Process -FilePath C:/X360/ISOs/H3M/OpenH3M.exe -WorkingDirectory $repo -ArgumentList $arguments -WindowStyle Hidden -PassThru
        [ordered]@{pid=$child.Id; process_start_utc=$child.StartTime.ToUniversalTime().ToString('o');
            trace_directory=$run; dll_sha256=$current; map_sha256=$baseline.sha256;
            mode='Normal human controls, no shutdown timer, no captures; recording waits for arm file'} |
            ConvertTo-Json | Set-Content -LiteralPath "$build/latest-launch.json"
        Write-Output "Game launched, PID $($child.Id). Recording is not armed yet."
    } finally { $env:TEMP=$oldTemp; $env:TMP=$oldTmp; $env:OPENH3M_SKY_TRACE_DIR=$oldTrace; $env:OPENH3M_SKY_PIXEL_PROBE_DIR=$oldProbe; $env:OPENH3M_SKY_TRACE_TARGETS=$oldTargets }
} finally { Pop-Location }
