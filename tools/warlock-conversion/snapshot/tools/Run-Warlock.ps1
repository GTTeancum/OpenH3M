[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Exe,
    [string]$Game,
    [ValidateRange(1,3600)][int]$Seconds = 180
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $Project).Path
if (-not $Game) { $Game = Join-Path $projectRoot '.local\warlock-play' }
Push-Location -LiteralPath $projectRoot
try {
    & python -B (Join-Path $PSScriptRoot 'warlock_handoff.py') run --project $projectRoot --game $Game --exe $Exe --seconds $Seconds
    if ($LASTEXITCODE -ne 0) { throw "Warlock launcher failed ($LASTEXITCODE); see .local\warlock-runs." }
} finally { Pop-Location }
