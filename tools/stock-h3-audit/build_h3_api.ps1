# Compile only automation of the installed official H3 API.
param([ValidateSet('ProbeH3Api','ApplyH3ShaderPlan','ApplyH3BitmapPlan','ReadH3ShaderConfigurations','ApplyH3MaterialNames')][string]$Name='ApplyH3ShaderPlan')
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$audit=Join-Path $repo 'work\stock-h3-audit'
$output=Join-Path $audit 'h3-api-probe'
$kit=Join-Path $repo 'work\editing-kits\h3ek'
$env:APPDATA=Join-Path $audit 'profile\roaming'
$env:LOCALAPPDATA=Join-Path $audit 'profile\local'
$env:TEMP=Join-Path $audit 'temp'
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force -Path $output | Out-Null
Copy-Item -LiteralPath (Join-Path $kit 'bin\ManagedBlam.dll') -Destination (Join-Path $output 'ManagedBlam.dll')
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /platform:x64 /highentropyva- /target:exe ('/out:'+(Join-Path $output ($Name+'.exe'))) ('/reference:'+(Join-Path $kit 'bin\ManagedBlam.dll')) /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot ($Name+'.cs'))
if($LASTEXITCODE -ne 0){throw "Official API wrapper compilation failed"}
Write-Output (Join-Path $output ($Name+'.exe'))
