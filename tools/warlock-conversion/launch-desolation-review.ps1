# Manual review only: normal controls, no replay and no shutdown timer.
# The user launches this when ready; all writable paths stay in the repository.
param([switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$runtime = Join-Path $repo 'work/desolation/candidate3-run/runtime'
$bundle = Join-Path $repo 'work/desolation/candidate3-dlc'
$manifest = Get-Content -LiteralPath (Join-Path $bundle 'bundle.json') -Raw | ConvertFrom-Json
$preparation = Get-Content -LiteralPath (Join-Path $repo 'work/desolation/candidate3-run/preparation.json') -Raw | ConvertFrom-Json
$package = (Resolve-Path -LiteralPath $manifest.package).Path
if (-not $package.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Package must stay inside the repository'
}
if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $manifest.sha256) {
    throw 'Review package hash changed'
}
foreach ($property in $preparation.runtime_hashes.PSObject.Properties) {
    $path = Join-Path $runtime $property.Name
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $property.Value) {
        throw "Review runtime hash changed: $($property.Name)"
    }
}
$exe = Join-Path $runtime 'OpenH3M.exe'
if ($ValidateOnly) {
    Write-Output 'Review package and seven runtime hashes verified. No game launched.'
    return
}
if (Get-CimInstance Win32_Process -Filter "Name='OpenH3M.exe'" | Where-Object { $_.ExecutablePath -eq $exe }) {
    throw 'This review runtime is already running'
}
$review = Join-Path $repo 'work/desolation/manual-review'
foreach ($name in @('', 'profile', 'temp')) {
    New-Item -ItemType Directory -Path (Join-Path $review $name) -Force | Out-Null
}
$cache = Join-Path $repo 'work/desolation/candidate3-run/cache'
$arguments = @(
    '--game_data_root="C:/X360/ISOs/H3M"',
    ('--user_data_root="' + (Join-Path $review 'profile') + '"'),
    ('--cache_root="' + $cache + '"'),
    ('--log_file="' + (Join-Path $review 'runtime.log') + '"'),
    ('--halo3mp_install_content="' + $package + '"'),
    '--input_script_button_state=false',
    '--input_script_keystrokes=false',
    '--log_level=info'
)
$oldEnvironment = @{}
foreach ($key in @('TEMP','TMP','APPDATA','LOCALAPPDATA')) {
    $oldEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
    $directory = if ($key -in @('TEMP','TMP')) { 'temp' } else { 'profile' }
    [Environment]::SetEnvironmentVariable($key, (Join-Path $review $directory), 'Process')
}
try {
    $process = Start-Process -FilePath $exe -WorkingDirectory $review -ArgumentList $arguments -PassThru
    Write-Output "Desolation review started (PID $($process.Id)). Select Desolation in the map list. Normal controls; no shutdown timer."
} finally {
    foreach ($key in $oldEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $oldEnvironment[$key], 'Process')
    }
}
