# Shared installation, normal user controls, native captures only.
param([int]$Candidate=3,[switch]$ValidateOnly)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $repo
$draft=Join-Path $repo ".local/battle-canyon-fresh/candidate$Candidate"
$bundle=Get-Content -LiteralPath (Join-Path $draft 'dlc/bundle.json') -Raw | ConvertFrom-Json
$package=(Resolve-Path -LiteralPath $bundle.package).Path
if(-not $package.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Package outside repository'}
if((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $bundle.sha256){throw 'Package changed'}
$install='C:/X360/ISOs/H3M'
$exe=Join-Path $install 'OpenH3M.exe'
$userRoot=Join-Path $repo 'work/dlc/installed-corrections'
if($ValidateOnly){Write-Output 'Fresh package verified for shared installation. No process launched.';return}
if(Get-CimInstance Win32_Process -Filter "Name='OpenH3M.exe' OR Name='halo3mp.exe'"){throw 'Game is already running; retain user control and wait for it to close'}
$review=Join-Path $draft 'review'
foreach($name in @('','temp','profile/roaming','profile/local','captures')){New-Item -ItemType Directory -Force -Path (Join-Path $review $name) | Out-Null}
$env:TEMP=Join-Path $review 'temp';$env:TMP=$env:TEMP
$env:APPDATA=Join-Path $review 'profile/roaming';$env:LOCALAPPDATA=Join-Path $review 'profile/local'
$arguments=@(
 '--game_data_root="C:/X360/ISOs/H3M"',
 ('--user_data_root="'+$userRoot+'"'),
 ('--cache_root="'+(Join-Path $repo 'work/dlc/cache')+'"'),
 ('--log_file="'+(Join-Path $review 'runtime.log')+'"'),
 ('--halo3mp_install_content="'+$package+'"'),
 '--input_script_button_state=false','--input_script_keystrokes=false',
 '--halo3mp_capture_guest_output_times_ms=30000,90000,150000',
 ('--halo3mp_capture_guest_output_path="'+(Join-Path $review 'captures/native.png')+'"'),
 '--halo3mp_log_fps=true','--log_level=info'
)
# A visible game window is expressly requested; no remote input or harness.
$process=Start-Process -FilePath $exe -WorkingDirectory $repo -ArgumentList $arguments -PassThru
@{pid=$process.Id;exe=$exe;user_root=$userRoot;package=$package;arguments=$arguments;started_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $review 'launch.json') -Encoding utf8
Write-Output "Shared Halo 3 launched, PID $($process.Id). Normal user controls; no shutdown timer."
