param(
    [string]$Version = "beta-0.8"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $projectRoot
$buildRoot = Join-Path $projectRoot "out\build\win-amd64-release"
$releaseRoot = Join-Path $projectRoot "out\release"
$packageName = "OpenH3M-$Version-win-x64"
$stagingRoot = Join-Path $releaseRoot $packageName
$archivePath = Join-Path $releaseRoot "$packageName.zip"

function Assert-ChildPath {
    param(
        [string]$Path,
        [string]$Parent
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullParent = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    if (-not $fullPath.StartsWith($fullParent, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside the release directory: $fullPath"
    }
}

$runtimeFiles = @(
    "halo3mp_l360.dll",
    "halo3mp_q10.dll",
    "halo3mp_waveshell-xbox.dll",
    "halo3mp_waveslibdll.dll",
    "rexgpu-xenos.dll",
    "rexruntime.dll"
)

$screenshotFiles = @(
    "mythic-menu.png",
    "last-resort-four-player.png",
    "construct-four-player.png"
)

$requiredFiles = @(
    (Join-Path $buildRoot "halo3mp.exe"),
    (Join-Path $repoRoot "OpenH3M.cmd"),
    (Join-Path $repoRoot "README.md"),
    (Join-Path $repoRoot "docs\release-game-folder.txt")
) + @($runtimeFiles | ForEach-Object { Join-Path $buildRoot $_ }) +
    @($screenshotFiles | ForEach-Object { Join-Path $repoRoot "docs\images\$_" })

foreach ($file in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Required release file is missing: $file"
    }
}

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
Assert-ChildPath -Path $stagingRoot -Parent $releaseRoot
Assert-ChildPath -Path $archivePath -Parent $releaseRoot

if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}

$gameFolder = New-Item -ItemType Directory -Path (Join-Path $stagingRoot "game") -Force
$imageFolder = New-Item -ItemType Directory -Path (Join-Path $stagingRoot "docs\images") -Force
Copy-Item -LiteralPath (Join-Path $buildRoot "halo3mp.exe") -Destination (Join-Path $stagingRoot "OpenH3M.exe")
foreach ($file in $runtimeFiles) {
    Copy-Item -LiteralPath (Join-Path $buildRoot $file) -Destination $stagingRoot
}
Copy-Item -LiteralPath (Join-Path $repoRoot "OpenH3M.cmd") -Destination $stagingRoot
Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $stagingRoot
Copy-Item -LiteralPath (Join-Path $repoRoot "docs\release-game-folder.txt") -Destination (Join-Path $gameFolder "PUT_DISC_FILES_HERE.txt")
foreach ($file in $screenshotFiles) {
    Copy-Item -LiteralPath (Join-Path $repoRoot "docs\images\$file") -Destination $imageFolder
}

Compress-Archive -LiteralPath $stagingRoot -DestinationPath $archivePath -CompressionLevel Optimal
$hash = Get-FileHash -LiteralPath $archivePath -Algorithm SHA256

Write-Host "Created $archivePath"
Write-Host "SHA256 $($hash.Hash)"
