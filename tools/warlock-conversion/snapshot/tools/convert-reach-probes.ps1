param([Parameter(Mandatory)][string]$InputJson,
      [Parameter(Mandatory)][string]$OutputJson)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
foreach ($candidate in @($InputJson, $OutputJson)) {
    $full = [IO.Path]::GetFullPath($candidate)
    if (-not $full.StartsWith($repo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Probe artifacts must remain inside the repository'
    }
}
$env:TEMP = Join-Path $repo '.local/build-temp'
$env:TMP = $env:TEMP
$dll = Join-Path $repo 'work/forge-world/tools/tagtool/TagTool.dll'
$null = [Reflection.Assembly]::LoadFrom($dll)
$rows = Get-Content -LiteralPath $InputJson -Raw | ConvertFrom-Json
$result = foreach ($row in $rows) {
    if ($row.terms.Count -ne 16) { throw 'Expected 16 half-precision VMF terms' }
    $probe = [TagTool.Tags.Definitions.DualVmfLightProbe]::new()
    $probe.VmfTerms = [ushort[]]$row.terms
    $probe.AnalyticalLightIndex = [uint32]$row.analytical_light_index
    $converted = [TagTool.Lighting.VmfConversion]::ConvertHalfLightprobe($probe)
    # Original H3 sLdT probe layout: direction at0, intensity at8,
    # three nine-term color arrays at16; 72 bytes including padding.
    $words = @($converted.DominantLightDirection) + @(0) +
             @($converted.DominantLightIntensity) + @(0) +
             @($converted.SHRed) + @($converted.SHGreen) + @($converted.SHBlue) + @(0)
    if ($words.Count -ne 36) { throw 'Unexpected native probe layout' }
    $bytes = [byte[]]::new(72)
    for ($i=0; $i -lt 36; $i++) {
        $word = [uint16]$words[$i]
        if (($word -band 0x7c00) -eq 0x7c00) { throw 'Nonfinite native lighting coefficient' }
        $bytes[2*$i] = [byte]($word -shr 8)
        $bytes[2*$i+1] = [byte]($word -band 255)
    }
    [ordered]@{kind=$row.kind; index=$row.index;
        source_prefix_hex=$row.source_prefix_hex;
        analytical_light_index=$row.analytical_light_index;
        native_probe_hex=[Convert]::ToHexString($bytes).ToLowerInvariant()}
}
# Preserve the source analytical-light field separately: its interpretation
# must be resolved before a caller installs these probes into a native map.
@{converter_sha256=(Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash;
  probes=@($result)} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputJson
