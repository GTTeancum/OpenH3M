# Narrow authoring trial: stock Standoff foliage shader + original Reach image.
# Official Tool performs all bitmap import and tag-field writes.
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$audit = Join-Path $repo 'work/stock-h3-audit'
$kit = Join-Path $repo 'work/editing-kits/h3ek'
$env:APPDATA = Join-Path $audit 'profile/roaming'
$env:LOCALAPPDATA = Join-Path $audit 'profile/local'
$env:TEMP = Join-Path $audit 'temp'
$env:TMP = $env:TEMP
$relative = 'levels\custom\battle_canyon_fresh'
$bitmap = "$relative\bitmaps\tree_boreal_leaves_diffuse"
$shader = "$relative\shaders\cex_bc_tree_boreal_leaves.shader_foliage"
$sourceImage = Join-Path $repo 'work/editing-kits/hrek/data/levels/shared/bitmaps/nature/tree/tree_boreal_leaves_diffuse.tiff'
$sourceBitmap = Join-Path $kit 'tags/levels/dlc/bunkerworld/bitmaps/bunker_leaf.bitmap'
$sourceShader = Join-Path $kit 'tags/levels/dlc/bunkerworld/shaders/bunkerworld_treebranch.shader_foliage'
$targetImage = Join-Path $kit "data\$bitmap.tif"
$targetBitmap = Join-Path $kit "tags\$bitmap.bitmap"
$targetShader = Join-Path $kit "tags\$shader"
foreach ($path in @($targetImage,$targetBitmap,$targetShader)) {
    if (Test-Path -LiteralPath $path) { throw "Trial target already exists; inspect before rerun: $path" }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
}
$before = @{}
foreach ($path in @($sourceImage,$sourceBitmap,$sourceShader)) {
    $before[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
}
Copy-Item -LiteralPath $sourceImage -Destination $targetImage
Copy-Item -LiteralPath $sourceBitmap -Destination $targetBitmap
Copy-Item -LiteralPath $sourceShader -Destination $targetShader
Push-Location $kit
try {
    & .\tool.exe bitmap_single "$bitmap.tif" *> (Join-Path $audit 'foliage-trial-bitmap.log')
    if ($LASTEXITCODE -ne 0) { throw 'Official bitmap import failed' }
    foreach ($index in @(0,2)) {
        $field = "shader_foliage_struct_definition[0].render_method[0].parameters[$index].bitmap"
        # References use Tool's path,group representation. A .bitmap suffix
        # reports success without changing the reference; verify exported fields.
        & .\tool.exe patch-tag-field $shader $field "$bitmap,bitm" *> (Join-Path $audit "foliage-trial-field-$index.log")
        if ($LASTEXITCODE -ne 0) { throw "Official bitmap field update failed: $field" }
    }
    & .\tool.exe export-tag-to-xml $targetShader (Join-Path $audit 'foliage-trial.shader_foliage.xml') *> (Join-Path $audit 'foliage-trial-export.log')
    if ($LASTEXITCODE -ne 0) { throw 'Official trial shader XML export failed' }
    & .\tool.exe export-tag-to-xml $targetBitmap (Join-Path $audit 'foliage-trial.bitmap.xml') *> (Join-Path $audit 'foliage-trial-bitmap-export.log')
    if ($LASTEXITCODE -ne 0) { throw 'Official trial bitmap XML export failed' }
    & .\tool.exe export-bitmap-tga $bitmap (Join-Path $audit 'foliage-trial-export') *> (Join-Path $audit 'foliage-trial-pixels.log')
    if ($LASTEXITCODE -ne 0) { throw 'Official bitmap pixel export failed' }
} finally { Pop-Location }
$xmlText = (Get-Content -LiteralPath (Join-Path $audit 'foliage-trial.shader_foliage.xml') -Raw).Replace('<unavailable>', '&lt;unavailable&gt;')
$document = [xml]$xmlText
foreach ($index in @(0,2)) {
    $field = $document.SelectSingleNode("/tag/block[@name='parameters']/element[@index='$index']/field[@name='bitmap']")
    if (!$field -or $field.value -ne "$bitmap,bitm") { throw "Bitmap reference did not change at parameter $index" }
}
foreach ($path in $before.Keys) {
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $before[$path]) { throw "Original changed: $path" }
}
$before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $audit 'foliage-trial-source-hashes.json')
Write-Output 'FOLIAGE_TRIAL_COMMANDS_FINISHED; inspect XML and actual output before acceptance'
