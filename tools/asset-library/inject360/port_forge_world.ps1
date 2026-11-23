# Ports Forge World's own DMR (Ryno's "Forge World - Halo 3", H3 MCC) into a copy of the
# original Xbox 360 Sandbox map. Reads the MCC map and the stock 360 maps; writes only inside this repository.
#   -Out    result map (default: work\asset-library\_work\inject360\fw\sandbox.map)
#   -Extra  additional Inject360 port arguments
param(
    [string]$Out = 'C:\Programming\GitHub\OpenH3M\work\asset-library\_work\inject360\fw\sandbox.map',
    [string[]]$Extra = @()
)
$ErrorActionPreference = 'Stop'
$x = 'C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\bin\Release\net48\Inject360.exe'
$fw = 'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map'
$maps = 'C:\X360\ISOs\H3M\maps'
$dir = Split-Path $Out
New-Item -ItemType Directory -Force $dir | Out-Null

# The Forge World object ported: the DMR.
# User decision 2026-11-20: the Falcon and Revenant are dropped; their faults (no Falcon gun, Hornet prompts, slow rotors,
# seat height and so on) are in Forge World's own tags. To port either again, add its tag to $roots and a --retarget line.
#   Revenant in Forge World's Forge menu = objects/vehicles/reverant/reverant (NOT covenant/revenant/revenant, a leftover).
#   Falcon = objects/vehicles/falcon_2.0/falcon_2.0.
$roots = @('dw3\r3ach\objects\weapons\rifle\dmr\dmr')

# 1. Shader templates Sandbox lacks: the same template, or failing that the closest one, from whichever stock
#    360 map has it, copied unchanged (with its compiled shaders) into the working copy.
$plan = & $x templates $fw "$maps\sandbox.map" $maps @roots
$plan | Select-String '^templates needed'
$grafts = @{}
foreach ($line in $plan) {
    $f = "$line".Split("`t")
    if ($f[0] -ne 'GRAFT') { continue }
    if (-not $grafts.ContainsKey($f[1])) { $grafts[$f[1]] = New-Object System.Collections.Generic.List[string] }
    if (-not $grafts[$f[1]].Contains($f[2])) { $grafts[$f[1]].Add($f[2]) }
}
$cur = "$maps\sandbox.map"; $i = 0
foreach ($donor in ($grafts.Keys | Sort-Object)) {
    $next = "$dir\_stage$i.map"
    & $x graft $donor $cur $next @($grafts[$donor]) | Select-String '^copied|Exception'
    if ($LASTEXITCODE -ne 0) { throw "graft from $donor failed" }
    if ($i -gt 0) { Remove-Item $cur }
    $cur = $next; $i++
}

# 2. The port. Sounds: copied unchanged from the Reach Xbox 360 game where it has the sound under the same name
#    (user instruction 2026-11-20); anything else is decoded from the MCC sound bank.
#    Stand-in placements on Sandbox: Battle Rifle and Assault Rifle -> DMR.
& $x port $fw $cur $Out @roots `
    --retarget 'weap:objects\weapons\rifle\battle_rifle\battle_rifle=dw3\r3ach\objects\weapons\rifle\dmr\dmr' `
    --retarget 'weap:objects\weapons\rifle\assault_rifle\assault_rifle=dw3\r3ach\objects\weapons\rifle\dmr\dmr' `
    --sound-donor 'C:\X360\ISOs\Halo Reach\maps\forge_halo.map' --sound-donor-prefix 'dw3\r3ach\' `
    @Extra 2>&1 | Select-String 'translated|injected|retargeted|moved|after finalize|Exception|MISSING|substitute'
if ($i -gt 0) { Remove-Item $cur }
