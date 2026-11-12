param([switch]$Visuals)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
Set-Location -LiteralPath $repo
$mode = if ($Visuals) { 'application-visuals' } else { 'application' }
$out = Join-Path $repo "work/halo4-to-h3/haven/foundry-1.9.19/$mode"
$kit = Join-Path $repo 'work/editing-kits/h4ek'
$blender = Join-Path $repo 'work/halo4-to-h3/upstream/blender-5.2.3-windows-x64/blender.exe'
foreach ($suffix in @('temp','profile/roaming','profile/local','profile/blender')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $out $suffix) | Out-Null
}
$env:TEMP = Join-Path $out 'temp'
$env:TMP = $env:TEMP
$env:APPDATA = Join-Path $out 'profile/roaming'
$env:LOCALAPPDATA = Join-Path $out 'profile/local'
$env:BLENDER_USER_CONFIG = Join-Path $out 'profile/blender'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUNBUFFERED = '1'
$arguments = @('--factory-startup','--python-exit-code','1','--python',
    (Join-Path $PSScriptRoot 'run_initialized_halo4_import.py'),'--','--foundry-release')
if ($Visuals) { $arguments += '--source-visuals' }
$started = [DateTime]::UtcNow
$process = Start-Process -FilePath $blender -ArgumentList $arguments -WorkingDirectory $kit -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $out 'import.stdout.log') `
    -RedirectStandardError (Join-Path $out 'import.stderr.log') -PassThru
if (-not $process.WaitForExit(180000)) {
    # Only this launched process and its children belong to the timeout scope.
    & taskkill.exe /PID $process.Id /T /F | Out-Null
    throw 'H4 import exceeded its 180-second watchdog'
}
if ($process.ExitCode -ne 0) { throw "Blender exited $($process.ExitCode)" }
$reportPath = Join-Path $out 'haven-geometry-import-report.json'
$reportFile = Get-Item -LiteralPath $reportPath
if ($reportFile.LastWriteTimeUtc -lt $started) { throw 'Import did not produce a fresh result' }
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if ($report.status -ne 'operator_finished' -or -not $report.source_tags_unchanged) {
    throw "Source import rejected: $($report.status); source tags unchanged=$($report.source_tags_unchanged)"
}
if (-not (Test-Path -LiteralPath (Join-Path $out 'haven-source-geometry.blend'))) {
    throw 'Import report passed but the saved scene is absent'
}
$report | Select-Object status,objects,mesh_objects,polygons,light_objects,source_tags_unchanged,seconds
