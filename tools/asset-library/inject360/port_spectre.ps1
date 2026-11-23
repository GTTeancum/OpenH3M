# Ports the Spectre from "Ultimate Forge 2.0" (H3 MCC, Steam Workshop 2933266434, map mombasa_sandbox.map)
# onto an original Xbox 360 map (by default the DMR build made by port_forge_world.ps1).
# Reads the MCC map and the stock 360 maps; writes only inside this repository.
#   -Base   the 360 map to add it to
#   -Out    result map
#   -Extra  additional Inject360 port arguments
# Donor chosen by the user 2026-11-20. objects\vehicles\spectre\spectre is the tag the map's Forge menu spawns
# ("spectre"). It uses stock seat poses (ghost_d, warthog_p) and the stock Ghost gun; its turret, engine sounds,
# camera track and prompt strings are its own.
param(
    [string]$Base = 'C:\Programming\GitHub\OpenH3M\work\asset-library\_work\inject360\fw\sandbox.map',
    [string]$Out = 'C:\Programming\GitHub\OpenH3M\work\asset-library\_work\inject360\spectre\sandbox.map',
    [string[]]$Extra = @()
)
$ErrorActionPreference = 'Stop'
$x = 'C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\bin\Release\net48\Inject360.exe'
$mcc = 'D:\SteamLibrary\steamapps\workshop\content\976730\2933266434\maps\mombasa_sandbox.map'
$maps = 'C:\X360\ISOs\H3M\maps'
$dir = Split-Path $Out
New-Item -ItemType Directory -Force $dir | Out-Null
$roots = @('objects\vehicles\spectre\spectre')

# 1. Shader templates the base lacks: the same template, or failing that the closest one, from whichever stock 360 map has it.
$plan = & $x templates $mcc $Base $maps @roots
$plan | Select-String '^templates needed'
$grafts = @{}
foreach ($line in $plan) {
    $f = "$line".Split("`t")
    if ($f[0] -ne 'GRAFT') { continue }
    if (-not $grafts.ContainsKey($f[1])) { $grafts[$f[1]] = New-Object System.Collections.Generic.List[string] }
    if (-not $grafts[$f[1]].Contains($f[2])) { $grafts[$f[1]].Add($f[2]) }
}
$cur = $Base; $i = 0
foreach ($donor in ($grafts.Keys | Sort-Object)) {
    $next = "$dir\_stage$i.map"
    & $x graft $donor $cur $next @($grafts[$donor]) | Select-String '^copied|Exception'
    if ($LASTEXITCODE -ne 0) { throw "graft from $donor failed" }
    if ($i -gt 0) { Remove-Item $cur }
    $cur = $next; $i++
}

# 2. The port. Stand-in placement on Sandbox: Mongoose -> Spectre (one moved onto the flat by the base).
#    Prompt strings as the MCC map has them (the 360 map has no Spectre text).
& $x port $mcc $cur $Out @roots `
    --retarget 'vehi:objects\vehicles\mongoose\mongoose=objects\vehicles\spectre\spectre' `
    --move 'Vehicles:12=5.5,-27.2,-22.6,0' `
    --add-string 'spectre_drive=ghost_enter|Hold \uE45E to drive Spectre' `
    --add-string 'spectre_enter_passenger=ghost_enter|Hold \uE445 to sit in Spectre' `
    --add-string 'spectre_board=ghost_enter|Hold \uE445 to board enemy Spectre' `
    --add-string 'spectre_flip=ghost_enter|Hold \uE445 to flip Spectre' `
    --add-string 'spectre_enter_gunner=ghost_enter|Hold \uE445 to operate Spectre turret' `
    @Extra 2>&1 | Select-String 'translated|injected|retargeted|moved|after finalize|Exception|MISSING|string'
if ($i -gt 0) { Remove-Item $cur }
