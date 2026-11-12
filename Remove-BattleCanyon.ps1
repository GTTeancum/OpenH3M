# Removes the verified Battle Canyon cleanup targets. Does not launch the game.
# Run normally to delete; add -WhatIf to preview. Requires no administrator rights.
# Shared tools, other maps, original game assets and Git history are preserved.
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'C:\X360\ISOs\H3M\.local\OpenH3M-source'
$comparison = [StringComparison]::OrdinalIgnoreCase
if (-not [IO.Path]::GetFullPath($PSScriptRoot).Equals($repo, $comparison)) {
    throw "Keep this script in its repository: $repo"
}

# Frozen, literal targets: no wildcard deletions or discovery-based removal.
$relativeTargets = @'
.local\battle-canyon-fresh
.local\retired-battle-canyon
work\editing-kits\h3ek\data\levels\custom\battle_canyon_fresh
work\editing-kits\h3ek\data\levels\custom\battle_canyon_rebuild
work\editing-kits\h3ek\data\levels\custom\bc_collision_workflow_probe
work\editing-kits\h3ek\data\levels\custom\bc_lighting_workflow_probe
work\editing-kits\h3ek\data\levels\custom\bc_render_bsp_probe_160
work\editing-kits\h3ek\data\levels\custom\bc_render_bsp_probe_261
work\editing-kits\h3ek\data\levels\custom\bc_render_bsp_probe_339
work\editing-kits\h3ek\data\levels\custom\bc_render_bsp_probe_53
work\editing-kits\h3ek\data\levels\custom\bc_water_workflow_probe
work\editing-kits\h3ek\data\levels\custom\bc_world_collision_probe
work\editing-kits\h3ek\reports\battle_canyon_fresh
work\editing-kits\h3ek\tags\levels\custom\battle_canyon_audit
work\editing-kits\h3ek\tags\levels\custom\battle_canyon_fresh
work\editing-kits\h3ek\tags\levels\custom\battle_canyon_rebuild
work\editing-kits\h3ek\tags\levels\custom\bc_collision_workflow_probe
work\editing-kits\h3ek\tags\levels\custom\bc_lighting_workflow_probe
work\editing-kits\h3ek\tags\levels\custom\bc_render_bsp_probe_160
work\editing-kits\h3ek\tags\levels\custom\bc_render_bsp_probe_261
work\editing-kits\h3ek\tags\levels\custom\bc_render_bsp_probe_339
work\editing-kits\h3ek\tags\levels\custom\bc_render_bsp_probe_53
work\editing-kits\h3ek\tags\levels\custom\bc_water_workflow_probe
work\editing-kits\h3ek\tags\levels\custom\bc_world_collision_probe
work\stock-h3-audit\arch_rock-family
work\stock-h3-audit\box_cardboard-family
work\stock-h3-audit\bunker_ceiling-family
work\stock-h3-audit\bunker_tech_computer-family
work\stock-h3-audit\ca_bcreek_cliff_boulders-trial
work\stock-h3-audit\ca_bcreek_cliff_rock_skybox-trial
work\stock-h3-audit\ca_bcreek_cliff_skybox-trial
work\stock-h3-audit\ca_bcreek_ramps-trial
work\stock-h3-audit\cache-build-2026110401
work\stock-h3-audit\cache-build-2026110402
work\stock-h3-audit\caustics-family
work\stock-h3-audit\circle_panels-family
work\stock-h3-audit\deadlock_light_warm_illum-family
work\stock-h3-audit\deco_trim-family
work\stock-h3-audit\default-corrections
work\stock-h3-audit\dirty_glass-family
work\stock-h3-audit\draft-lighting-2026110401
work\stock-h3-audit\forerunner_metal-family
work\stock-h3-audit\forge_panel-family
work\stock-h3-audit\giant_bark-family
work\stock-h3-audit\glass_exterior-family
work\stock-h3-audit\glass_interior-family
work\stock-h3-audit\glass-channel-preparation
work\stock-h3-audit\guardian_int_light_cool-family
work\stock-h3-audit\inherited_cook_metal-family
work\stock-h3-audit\inherited_tech_bank-family
work\stock-h3-audit\light_techbit_cool-family
work\stock-h3-audit\light-gel-pixels
work\stock-h3-audit\lights-family
work\stock-h3-audit\metal_detail-family
work\stock-h3-audit\monitor_base-family
work\stock-h3-audit\monitor_innards-family
work\stock-h3-audit\panel_detail-family
work\stock-h3-audit\prop_health_cabinet-family
work\stock-h3-audit\prop_health_pack-family
work\stock-h3-audit\prop_health_rubber-family
work\stock-h3-audit\prop_light_strips-family
work\stock-h3-audit\prop_unsc_decal-family
work\stock-h3-audit\road-family
work\stock-h3-audit\rock_small-family
work\stock-h3-audit\sentinel_metal-family
work\stock-h3-audit\sky_clouds_plasma-family
work\stock-h3-audit\sky_clouds_soft-family
work\stock-h3-audit\sky_gradient-family
work\stock-h3-audit\sky_halo-family
work\stock-h3-audit\sky_lightning-family
work\stock-h3-audit\sky_moon-family
work\stock-h3-audit\sky_mountains-family
work\stock-h3-audit\sky_panel-family
work\stock-h3-audit\sky_stars-family
work\stock-h3-audit\sky_sun_flare-family
work\stock-h3-audit\sky_white-family
work\stock-h3-audit\smooth_cook-family
work\stock-h3-audit\smooth_phong-family
work\stock-h3-audit\terrain_arch-family
work\stock-h3-audit\terrain_boulders-family
work\stock-h3-audit\terrain_cliffs-family
work\stock-h3-audit\terrain_ground-family
work\stock-h3-audit\terrain_tunnels-family
work\stock-h3-audit\terrain-normal-verification
work\stock-h3-audit\terrain-scalar-inputs
work\stock-h3-audit\terrain-trial
work\stock-h3-audit\unlit_sky-family
work\stock-h3-audit\wall-detail-trial
work\stock-h3-audit\wall-family
work\stock-h3-audit\water-bitmap-pixels
work\stock-h3-audit\water-family
work\stock-h3-audit\wip
tools\stock-h3-audit\build_360_draft.py
tools\stock-h3-audit\export_360_collision_draft.py
tools\stock-h3-audit\launch_360_draft.ps1
tools\stock-h3-audit\package_360_draft.py
tools\stock-h3-audit\Trim360InitialStarts.cs
tools\stock-h3-audit\verify_360_collision_draft.py
work\editing-kits\h3ek\maps\battle_canyon_fresh.map
work\stock-h3-audit\battle-canyon-360-draft.blend
work\stock-h3-audit\battle-canyon-360-draft.blend1
work\stock-h3-audit\battle-canyon-360-planar-draft.blend
work\stock-h3-audit\battle-canyon-h3-authoring.blend
work\stock-h3-audit\battle-canyon-h3-materials.blend
work\stock-h3-audit\battle-canyon-h3-sky.blend
work\stock-h3-audit\battle-canyon-h3-structure-design.blend
work\stock-h3-audit\battle-canyon-original-sky.blend
work\stock-h3-audit\boulder-batch-before-battle-canyon-h3-authoring.blend
work\stock-h3-audit\boulder-batch-before-battle-canyon-h3-materials.blend
work\stock-h3-audit\render-bsp-before-battle-canyon-h3-authoring.blend
work\stock-h3-audit\render-bsp-before-battle-canyon-h3-materials.blend
work\stock-h3-audit\to-do-battle-canyon-only.patch
'@ -split '\r?\n' | Where-Object { $_.Trim().Length -gt 0 }

function Assert-ConfinedPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($repo + '\', $comparison)) {
        throw "Target escapes repository: $full"
    }
    # Check every ancestor, including the repository, for junctions/symlinks.
    $cursor = $full
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Refusing linked path: $cursor"
            }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    return $full
}

function Assert-NoLinkedDescendants([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) { return }
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($Path)
    while ($pending.Count -gt 0) {
        foreach ($child in Get-ChildItem -LiteralPath $pending.Pop() -Force) {
            if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Refusing linked descendant: $($child.FullName)"
            }
            if ($child.PSIsContainer) { $pending.Push($child.FullName) }
        }
    }
}

# Finish path validation before changing anything.
$targets = @($relativeTargets | ForEach-Object {
    Assert-ConfinedPath (Join-Path $repo $_)
} | Sort-Object -Unique)
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target) { Assert-NoLinkedDescendants $target }
}

# Refuse to remove a live map. No process termination or interactive input.
if (Get-Process -Name OpenH3M, halo3mp -ErrorAction SilentlyContinue) {
    throw 'Close the game, then run this script again.'
}

# Remove only the two Battle Canyon registration lines, preserving other edits.
$patchSpecs = @(
    @{
        Path = 'tools\warlock-conversion\snapshot\tools\build_dlc_payload.py'
        Pattern = "(?m)^[ \t]*\('zanzibar', 'battle_canyon', 'Battle Canyon', 1733\),[ \t]*\r?\n"
    },
    @{
        Path = 'tools\warlock-conversion\snapshot\tools\build_dlc_previews.py'
        Pattern = "(?m)^[ \t]*'battle_canyon': '3575686579/images/large_beaver\.png',[ \t]*\r?\n"
    }
)
$patches = @()
$utf8 = [Text.UTF8Encoding]::new($false, $true)
foreach ($spec in $patchSpecs) {
    $path = Assert-ConfinedPath (Join-Path $repo $spec.Path)
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $before = [IO.File]::ReadAllBytes($path)
    $text = $utf8.GetString($before)
    $after = [regex]::Replace($text, $spec.Pattern, '')
    if ($after -match '(?m)^[^#\r\n]*[''"]battle_canyon[''"]') {
        throw "Battle Canyon registration format changed; refusing to guess: $path"
    }
    if ($after -cne $text) {
        $patches += @{ Path = $path; Before = $before; After = $utf8.GetBytes($after) }
    }
}

$removed = 0
$missing = 0
foreach ($patch in $patches) {
    if ($PSCmdlet.ShouldProcess($patch.Path, 'Remove Battle Canyon registration')) {
        if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($patch.Path)) -cne
            [Convert]::ToBase64String($patch.Before)) {
            throw "File changed during cleanup: $($patch.Path)"
        }
        [IO.File]::WriteAllBytes($patch.Path, $patch.After)
    }
}
foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) { $missing++; continue }
    if ($PSCmdlet.ShouldProcess($target, 'Permanently delete Battle Canyon artifact')) {
        $null = Assert-ConfinedPath $target
        Assert-NoLinkedDescendants $target
        Remove-Item -LiteralPath $target -Recurse -Force -Confirm:$false
        if (Test-Path -LiteralPath $target) { throw "Deletion did not complete: $target" }
        $removed++
    }
}

# The old manual checklist is removed last. Keep this script for repeatable cleanup.
$checklist = Assert-ConfinedPath (Join-Path $repo 'BATTLE-CANYON-DELETE-LIST.md')
if (Test-Path -LiteralPath $checklist) {
    if ($PSCmdlet.ShouldProcess($checklist, 'Delete superseded manual checklist')) {
        Remove-Item -LiteralPath $checklist -Force -Confirm:$false
    }
}
if ($WhatIfPreference) {
    Write-Output "Preview complete: $($targets.Count) literal targets checked. No files changed."
} else {
    Write-Output "Cleanup finished: $removed targets deleted; $missing already absent."
}
Write-Output 'Shared tools, shared diagnostic records, other maps and Git history are retained.'
