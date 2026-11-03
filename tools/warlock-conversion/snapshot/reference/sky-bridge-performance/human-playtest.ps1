# Validate by default. -Run starts a manual-input test with a 170-second watchdog.
param([switch]$Run)
$ErrorActionPreference = 'Stop'
$repo = 'C:/X360/ISOs/H3M/.local/OpenH3M-source'
$python = 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe'
$oldTemp = $env:TEMP; $oldTmp = $env:TMP
Push-Location -LiteralPath $repo
try {
    $env:TEMP = Join-Path $repo '.local/build-temp'
    $env:TMP = $env:TEMP
    if (Get-Process halo3mp -ErrorAction SilentlyContinue) { throw 'Close the existing game before this bounded test.' }
    $manifest = Get-Content -Raw 'work/sky-bridge/deferred-timing-build/after-hashes.json' | ConvertFrom-Json
    foreach ($entry in $manifest) {
        $binary = Join-Path $repo ('work/rexglue-sdk/out/win-amd64/' + [IO.Path]::GetFileName($entry.Path))
        if ((Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash -ne $entry.Hash) {
            throw "Runtime changed: $binary"
        }
    }
    $payload = Join-Path $repo 'work/sky-bridge/payload-29'
    $verification = Get-Content -Raw 'work/sky-bridge/live-candidate-29/verification.json' | ConvertFrom-Json
    foreach ($entry in $verification.payload_files) {
        if ((Get-FileHash -LiteralPath (Join-Path $payload $entry.name) -Algorithm SHA256).Hash -ne $entry.sha256) {
            throw "Payload changed: $($entry.name)"
        }
    }
    $arguments = @('-B', 'tools/warlock-conversion/snapshot/tools/trace_loading.py',
        '--project', 'C:/X360/ISOs/H3M',
        '--exe', (Join-Path $repo 'work/rexglue-sdk/out/win-amd64/halo3mp.exe'),
        '--expected-exe-sha256', 'a90c7d1d10ec7833e58df4f72ba96a7c65ebab5567cd7ba1032b69f1dd0621ad',
        '--game', (Join-Path $repo 'work/sky-bridge/performance-candidate29-01/game'),
        '--cache-root', (Join-Path $repo 'work/sky-bridge/performance-candidate29-01/cache'),
        '--dlc-payload', $payload, '--dlc-map', 'sky_bridge', '--slot', 'zanzibar',
        '--seconds', '170', '--manual-input', '--sample-observer', '--quiet-timing')
    Write-Output 'Validated candidate 29 payload and runtime. No captures or automated input.'
    Write-Output 'Manual route: Custom Games -> Sky Bridge -> Slayer -> start game.'
    Write-Output 'Check indoor/courtyard/left-corridor panels, transparency, screen animation, exposure/bloom, and audio.'
    Write-Output 'Report each location as fixed, still defective, or not reached. The game closes after 170 seconds.'
    if ($Run) {
        & $python @arguments
        if ($LASTEXITCODE -ne 0) { throw "Bounded playtest returned $LASTEXITCODE" }
    } else {
        Write-Output 'Preparation only; no process started. Use -Run when ready for manual play.'
    }
} finally {
    $env:TEMP = $oldTemp; $env:TMP = $oldTmp
    Pop-Location
}
