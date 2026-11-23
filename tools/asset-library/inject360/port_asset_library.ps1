# Port the four asset-library objects (CE Magnum, Reach DMR, Falcon, Revenant) from the MCC test map into a copy
# of the original 360 Sandbox, for testing in the private game folder. Nothing installed or on the disc is written.
#   powershell -File C:\Programming\GitHub\OpenH3M\tools\asset-library\inject360\port_asset_library.ps1 [-Out <map>]
param(
    [string]$Out = 'C:\Programming\GitHub\OpenH3M\.local\inject360-game\maps\sandbox.map',
    [string[]]$Extra = @()
)
$exe = 'C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\bin\Release\net48\Inject360.exe'
$mcc = 'C:\Programming\GitHub\OpenH3M\.local\asset-kit-h3\maps\asset_library_test.map'
$x360 = 'C:\X360\ISOs\H3M\maps\sandbox.map'
$falcon = 'vehi:objects\vehicles\reach_falcon\reach_falcon'
$revenant = 'vehi:objects\vehicles\reach_revenant\reach_revenant'
$guns = 'objects\vehicles\reach_falcon\turrets'
$RB = '\uE445'
$args2 = @(
    'port', $mcc, $x360, $Out,
    'objects\weapons\pistol\ce_magnum\ce_magnum', 'objects\weapons\rifle\reach_dmr\reach_dmr',
    'objects\vehicles\reach_falcon\reach_falcon', 'objects\vehicles\reach_revenant\reach_revenant',
    # test placement: the player spawns with the CE magnum; DMRs, Falcons and Revenants replace stock items on the map
    '--retarget', 'weap:objects\weapons\rifle\assault_rifle\assault_rifle=objects\weapons\pistol\ce_magnum\ce_magnum',
    '--retarget', 'weap:objects\weapons\pistol\magnum\magnum=objects\weapons\pistol\ce_magnum\ce_magnum',
    '--retarget', 'weap:objects\weapons\rifle\battle_rifle\battle_rifle=objects\weapons\rifle\reach_dmr\reach_dmr',
    '--retarget', 'vehi:objects\vehicles\warthog\warthog=objects\vehicles\reach_falcon\reach_falcon',
    '--retarget', 'vehi:objects\vehicles\mongoose\mongoose=objects\vehicles\reach_revenant\reach_revenant',
    # pickup prompts: the original 360 font has no DMR / CE magnum icon, so the stock BR / magnum prompt (and icon) is reused
    # the original 360 font has no DMR picture, so the DMR prompts are text only (U+E45D = hold-RB glyph)
    '--add-string', 'dmr_pickup=br_pickup|Hold \uE45D to pick up\u000D\u000ADMR', '--add-string', 'dmr_swap=br_swap|Hold \uE45D to swap for\u000D\u000ADMR',
    '--add-string', 'dmr_picked_up=br_picked_up|Picked up a DMR',
    '--set-string', 'weap:objects\weapons\rifle\reach_dmr\reach_dmr/Picked Up Message=dmr_picked_up',
    '--add-string', 'ce_mp_pickup=mp_pickup|', '--add-string', 'ce_mp_swap=mp_swap|',
    '--add-string', 'ce_mp_dual=mp_dual|', '--add-string', 'ce_mp_dual_swap=mp_dual_swap|',
    '--add-string', 'ce_mp_picked_up=mp_picked_up|Picked up a CE Magnum',
    '--set-string', 'weap:objects\weapons\pistol\ce_magnum\ce_magnum/Picked Up Message=ce_mp_picked_up',
    # pickup icon index on 360 (MCC dropped this field): same as the stock weapon each one stands in for
    '--set', 'weap:objects\weapons\rifle\reach_dmr\reach_dmr/OLD Message Index=4',
    '--set', 'weap:objects\weapons\pistol\ce_magnum\ce_magnum/OLD Message Index=6',
    # vehicle seat prompts: the tags were built from stock Ghost / Hornet / Warthog copies
    '--add-string', "revenant_enter=ghost_enter|Hold $RB to drive Revenant",
    '--add-string', "revenant_ride=ghost_enter|Hold $RB to ride in Revenant",
    '--add-string', "revenant_board=ghost_board|Hold $RB to board enemy Revenant",
    '--set-string', "$revenant/Seats[0]/Enter Seat String=revenant_enter",
    '--set-string', "$revenant/Seats[1]/Enter Seat String=revenant_ride",
    '--set-string', "$revenant/Seats[2]/Enter Seat String=revenant_board",
    '--set-string', "$revenant/Seats[3]/Enter Seat String=revenant_board",
    '--add-string', "falcon_enter=hornet_d_enter|Hold $RB to pilot Falcon",
    '--add-string', "falcon_ride=hornet_p_enter|Hold $RB to ride in Falcon",
    '--add-string', "falcon_board=hornet_board|Hold $RB to board enemy Falcon",
    '--add-string', "falcon_gunner=warthog_enter_gunner|Hold $RB to operate Falcon turret",
    '--set-string', "$falcon/Seats[0]/Enter Seat String=falcon_enter",
    '--set-string', "$falcon/Seats[1]/Enter Seat String=falcon_ride",
    '--set-string', "$falcon/Seats[2]/Enter Seat String=falcon_ride",
    '--set-string', "$falcon/Seats[3]/Enter Seat String=falcon_board",
    '--set-string', "$falcon/Seats[4]/Enter Seat String=falcon_board",
    '--set-string', "$falcon/Seats[5]/Enter Seat String=falcon_ride",
    '--set-string', "$falcon/Seats[6]/Enter Seat String=falcon_ride",
    '--set-string', "vehi:$guns\falcon_side_gun_left\falcon_side_gun_left/Seats[0]/Enter Seat String=falcon_gunner",
    '--set-string', "vehi:$guns\falcon_side_gun_right\falcon_side_gun_right/Seats[0]/Enter Seat String=falcon_gunner",
    '--set-string', "vehi:$guns\falcon_side_gun_left\falcon_side_gun_left/Seats[1]/Enter Seat String=falcon_board",
    '--set-string', "vehi:$guns\falcon_side_gun_right\falcon_side_gun_right/Seats[1]/Enter Seat String=falcon_board"
) + $Extra
& $exe @args2
