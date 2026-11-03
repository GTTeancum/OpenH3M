# Shared installation only. No debugger, input script, replay, or capture harness.
param([switch]$Run, [switch]$Bounded)
$ErrorActionPreference = 'Stop'
$repo = 'C:/X360/ISOs/H3M/.local/OpenH3M-source'
Push-Location -LiteralPath $repo
try {
    if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { throw 'A game is already running.' }
    $record = Get-Content -Raw 'work/sky-bridge/shared-install-coordination.json' | ConvertFrom-Json
    $shared = $record.shared_user_data_root
    $sky = Join-Path $shared '0000000000000000/4D5307E6/00000002/C337EBA990B40F54512D18E8AB31188A2B040540/sky_bridge.map'
    $battle = Join-Path $shared '0000000000000000/4D5307E6/00000002/E3C216511E5A0ED8A2E37F70BC65E407C481C510/battle_canyon.map'
    if ((Get-FileHash -LiteralPath $sky).Hash -ne '506cdc953bed8c2a80c751b8ddbc8422a61549e9143d73446276947707d06e36') { throw 'Sky Bridge changed.' }
    if ((Get-FileHash -LiteralPath $battle).Hash -ne $record.protected_battle_canyon_sha256) { throw 'Battle Canyon changed; coordinate before launching.' }
    Write-Output 'Shared content verified: Sky Bridge and Battle Canyon coexist with the existing maps.'
    if (-not $Run) { Write-Output 'Prepared only; no game launched.'; return }
    foreach ($entry in $record.runtime_comparison) {
        if ((Get-FileHash -LiteralPath $entry.target).Hash -ne $entry.tested_sha256) { throw 'Shared runtime update is pending. Do not substitute a separate test installation.' }
    }
    if ((Get-FileHash -LiteralPath 'C:/X360/ISOs/H3M/OpenH3M.bootstrap.toml').Hash -ne $record.bootstrap_sha256) { throw 'Shared settings changed; review before launching.' }
    $oldTemp = $env:TEMP; $oldTmp = $env:TMP
    try {
        $env:TEMP = Join-Path $repo '.local/build-temp'; $env:TMP = $env:TEMP
        $child = Start-Process -FilePath 'C:/X360/ISOs/H3M/OpenH3M.exe' -WorkingDirectory $repo -WindowStyle Hidden -PassThru
        Write-Output "Shared game started: PID $($child.Id). User controls from startup. No harness."
        if ($Bounded) {
            if (-not $child.WaitForExit(170000)) { Stop-Process -Id $child.Id; $child.WaitForExit(5000) | Out-Null }
        } else {
            Write-Output "No automatic shutdown timer. Close the game when finished."
        }
    } finally { $env:TEMP = $oldTemp; $env:TMP = $oldTmp }
} finally { Pop-Location }
