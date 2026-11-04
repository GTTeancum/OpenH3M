param([string]$Map = 'C:/X360/ISOs/H3M/maps/bunkerworld.map')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$auditRoot = Join-Path $repo 'work/stock-h3-audit'
$env:TEMP = Join-Path $auditRoot 'temp'
$env:TMP = $env:TEMP
$env:DOTNET_ROLL_FORWARD = 'Major'
$tool = Join-Path $auditRoot 'bin/TagTool.exe'
$before = (Get-FileHash -LiteralPath $Map -Algorithm SHA256).Hash
& $tool $Map ListTags *> (Join-Path $auditRoot 'standoff-all-tags.txt')
if ($LASTEXITCODE -ne 0) { throw 'TagTool ListTags failed' }
# EditTag opens a read context; this command file has no SaveChanges or mutations.
& $tool $Map RunCommands tools/stock-h3-audit/palette.commands *> (Join-Path $auditRoot 'standoff-forge-palette.txt')
if ($LASTEXITCODE -ne 0) { throw 'TagTool palette query failed' }
$after = (Get-FileHash -LiteralPath $Map -Algorithm SHA256).Hash
if ($before -ne $after) { throw 'Stock map hash changed' }
@{map=$Map; before_sha256=$before; after_sha256=$after; unchanged=$true} |
    ConvertTo-Json | Set-Content (Join-Path $auditRoot 'stock-map-integrity.json')
python -B tools/stock-h3-audit/summarize.py
if ($LASTEXITCODE -ne 0) { throw 'Report formatting failed' }
