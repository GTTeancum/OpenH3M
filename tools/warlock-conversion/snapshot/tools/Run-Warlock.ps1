[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$runRoot = Join-Path $projectRoot '.local\load-check'
$gameRoot = Join-Path $projectRoot '.local\test-game'
$exe = 'D:\Programming\GitHub\H3M\OpenH3M.exe'
if (Get-Process -Name OpenH3M -ErrorAction SilentlyContinue) {
    throw 'Close the existing OpenH3M instance first.'
}
foreach ($path in @($exe, (Join-Path $gameRoot 'maps\lockout.map'))) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing: $path" }
}
foreach ($name in @('temp', 'profile')) {
    New-Item -ItemType Directory -Path (Join-Path $runRoot $name) -Force | Out-Null
}
& python -B (Join-Path $PSScriptRoot 'diagnose_loading.py')
if ($LASTEXITCODE -ne 0) { throw 'Loading preflight failed.' }
$env:TEMP = Join-Path $runRoot 'temp'
$env:TMP = $env:TEMP
$env:LOCALAPPDATA = Join-Path $runRoot 'profile'
$env:APPDATA = $env:LOCALAPPDATA
$arguments = @("--game_data_root=$gameRoot", "--user_data_root=$runRoot",
    "--cache_root=$runRoot\cache", "--log_file=$runRoot\manual.log")
Write-Host 'Select Custom Games > Blackout > Slayer. Blackout is the Warlock test slot.'
Write-Host 'Recognizable Warlock proof verified in first-person Slayer; visual fidelity remains approximate.'
Write-Host 'Visuals are unfinished; this is not a fidelity-complete conversion.'
Write-Host 'Original OpenH3M binary; no scripted input or screenshots in this launcher.'
Write-Host "Logs: $runRoot\manual.log"
Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $runRoot
