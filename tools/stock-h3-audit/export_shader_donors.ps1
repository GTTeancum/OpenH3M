# Read stock H3 authoring tags using the official editing kit command.
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$audit = Join-Path $repo 'work/stock-h3-audit'
$kit = Join-Path $repo 'work/editing-kits/h3ek'
$destination = Join-Path $audit 'h3-shader-xml'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$env:APPDATA = Join-Path $audit 'profile/roaming'
$env:LOCALAPPDATA = Join-Path $audit 'profile/local'
$env:TEMP = Join-Path $audit 'temp'
$env:TMP = $env:TEMP
$evidence = @()
Push-Location $kit
try {
    foreach ($donor in (Import-Csv (Join-Path $audit 'surface-donor-candidates.csv'))) {
        $source = Join-Path (Join-Path $kit 'tags') $donor.stock_tag
        $before = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $name = [IO.Path]::GetFileName($donor.stock_tag)
        $xml = Join-Path $destination ($name + '.xml')
        & .\tool.exe export-tag-to-xml $source $xml *> (Join-Path $destination ($name + '.log'))
        if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $xml)) {
            throw "Official XML export failed: $($donor.stock_tag)"
        }
        $after = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        if ($before -ne $after) { throw "Stock source changed: $source" }
        # Tool emits an unescaped resource placeholder. Escape only that token
        # in the inspection copy; retain Tool's file verbatim, never reimport it.
        $inspectionText = (Get-Content -LiteralPath $xml -Raw).Replace('<unavailable>', '&lt;unavailable&gt;')
        try { $parsed = [xml]$inspectionText }
        catch { throw "Could not inspect official XML for $source : $($_.Exception.GetType().Name)" }
        if (!$parsed.DocumentElement) { throw "Official XML export produced no document: $source" }
        $evidence += [pscustomobject]@{ tag=$donor.stock_tag; sha256=$before; xml=$xml; root=$parsed.DocumentElement.Name }
    }
} finally { Pop-Location }
$evidence | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $audit 'h3-shader-xml-evidence.json')
Write-Output "H3_STOCK_SHADER_XML_EXPORTED $($evidence.Count)"
