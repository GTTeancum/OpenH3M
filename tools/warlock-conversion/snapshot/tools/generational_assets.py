"""Explicit Halo Generational Combat -> stock Halo 3 gameplay equivalents.

Map geometry stays authored. Cosmetic faction/gold variants use stock behavior,
as required by the user's Halo 3 asset policy. Unlisted unique objects still
follow normal conversion; no substring matching silently replaces new assets.
"""


def stock_aliases():
    result = {}
    def add(group, source, target, variant=None):
        result[group, source] = group, target, variant
    # Powerhouse/Sky Bridge: use the original H3 Battle Rifle dependency graph.
    # The custom DMR is unsupported; do not import its tuning or HUD labels.
    add('weap', r'priception\objects\weapons\rifle\dmr\dmr',
        r'objects\weapons\rifle\battle_rifle\battle_rifle')
    # Sanctuary renamed Sandbox's multiply-blended Forerunner strip. Keep
    # the original native material instead of rendering its white backing.
    add('rmsh', r'levels\multi\sancr\shaders\decor_strip_long_a',
        r'objects\levels\dlc\sandbox\shaders\decor_strip_long_a')
    # Sanctuary's creek/base-front water cards are renamed campaign waterfalls.
    # Their MCC material adds detail-normal/parallax animation absent from the
    # shipping multiplayer shader. Reuse Valhalla's complete native material,
    # including its alpha mask and scrolling, instead of an opaque fallback.
    for name in ('street_creek', 'frontbase_falls'):
        add('rmsh', 'levels\\multi\\sancr\\shaders\\water\\' + name,
            r'levels\multi\riverworld\shaders\vahalla_waterfall')
    # Powerhouse falling-water sheets use the shipping Valhalla equivalent.
    # Its mask, dual scrolling color layers, bump and alpha blending remain
    # native; only the authored BSP material reference changes. The generic
    # opaque fallback lost blending and every source scrolling animation.
    # Audited active donor parts: riverworld meshes 31/32/33 (1,530 indices).
    # Do not include horizontal water or splash/decal materials in this alias.
    for name in ('settlement_pipe_small_water', 'settlement_pipe_falls',
                 'settlement_waterfall_lower', 'settlement_waterfall',
                 'settlement_waterfall_mid', 'settlement_river_valley_waterfall_a'):
        add('rmsh', 'levels\\multi\\s3d_powerhouse\\shaders\\' + name,
            r'levels\multi\riverworld\shaders\vahalla_waterfall')
    # Assembly's animated sky water_edges is NOT a matching splash equivalent:
    # its native base/detail textures are green industrial liquid. Keep the
    # Powerhouse splash separate until its authored white foam can be retained.
    # See work/powerhouse/native-foam-color-audit-50.json (rejected candidate50).
    # 3longation ambient-creature death dependencies: original Cold Storage's
    # native Flood-clump family supplies debris without the MCC depth-fade
    # shader permutation. Keep effect timing/emitters; use stock H3 visuals.
    add('prt3', r'fx\particles\models\debris\flood_clumps\flood_clumps_charred',
        r'fx\particles\models\debris\flood_clumps\flood_clumps_opaque')
    add('prt3', r'objects\characters\ambient_life\lod_phantom\fx\lod_firing_bolt',
        r'objects\characters\ambient_life\lod_hornet\fx\lod_firing_bolt')
    # Powerhouse's turbine sample is absent from all 298 installed bank indices.
    # Last Resort provides an original H3 environmental turbine loop.
    add('snd!', r'priception\sound\levels\multi\s3d_powerhouse\m30_turbine\m30_turbine',
        r'sound\levels\zanzibar\zanzibar_base_turbine_close\turbine_close\loop')
    # Powerhouse ambient samples are absent from installed FMOD banks. Use
    # original H3 environmental loops by purpose; keep source placement/looping.
    for source, target in {
        r'comp_garble_loop\comp_garble': r'dlc\bunkerworld\sound_scenery\computer_telemetry\computer_telemetry\loop',
        r'comp_whirry\comp_whirry': r'dlc\space_camp\sound_scenery\comp_whirry\comp_whirry\loop',
        r'computer_server_lp2\computer_server_lp2': r'dlc\bunkerworld\sound_scenery\h_server_loop\h_server_loop\loop',
        r'electric_hum\electric_hum': r'dlc\docks\sound_scenery\electric_hum_human\electric_hum\loop',
        r'electric_hum_human\electric_hum': r'dlc\docks\sound_scenery\electric_hum_human\electric_hum\loop',
        r'dam_waterfall_close\dam_waterfall_close': r'riverworld\sound_scenery\riverworld_waterfall_close\riverworld_waterfall_close\loop',
        r'riverworld_rapids\riverworld_rapids': r'riverworld\sound_scenery\waterfall_close_churning\waterfall_close_churning\loop',
        r'water_in_pipes\water_in_pipes': r'dlc\docks\sound_scenery\pressure_in_pipes\pressure_in_pipes\loop',
        r'water_brook\water_brook': r'riverworld\sound_scenery\water_brook\water_brook\loop',
        r'water_creek\water_creek': r'riverworld\sound_scenery\water_creek\water_creek\loop',
        r'water_small_stream\water_small_stream': r'riverworld\sound_scenery\water_brook\water_brook\loop',
        r'waterfall_off_the_edge\off_the_edge': r'riverworld\sound_scenery\waterfall_far\waterfall_far\loop',
    }.items():
        add('snd!', 'priception\\sound\\levels\\multi\\s3d_powerhouse\\' + source,
            'sound\\levels\\' + target)
    for source, target in {
        r'levels\solo\010_jungle\fx\waterfall_stream\particles\rolling_mist_depth_fade': 'rolling_mist',
        r'levels\solo\100_citadel\fx\waterfall\particles\rolling_mist': 'rolling_mist',
        r'levels\solo\100_citadel\fx\waterfall\particles\water_spray': 'water_spray',
        r'levels\solo\100_citadel\fx\waterfall\particles\mist': 'mist',
    }.items():
        add('prt3', source, 'levels\\multi\\riverworld\\fx\\waterfall\\particles\\' + target)
    # Remember Reach H3 pack: original H3 gameplay equivalents are mandatory.
    # Original-disc Valhalla supplies the equivalent waterfall spray, including
    # native shader/blending and texture dependencies (particle-donors audit).
    add('prt3', r'fx\particles\atmospheric\soft_smoke\soft_smoke_waterfall_add_01',
        r'levels\multi\riverworld\fx\waterfall\particles\mist')
    add('prt3', r'fx\particles\atmospheric\soft_smoke\soft_smoke_waterfall_add',
        r'levels\multi\riverworld\fx\waterfall\particles\mist')
    for particle in ('fluid_spray_xlarge', 'fluid_spray_xlarge_01'):
        add('prt3', 'levels\\multi\\s3d_powerhouse\\fx\\particles\\' + particle,
            r'levels\multi\riverworld\fx\waterfall\particles\water_spray')
    add('prt3', r'levels\multi\s3d_powerhouse\fx\particles\water_spray',
        r'levels\multi\riverworld\fx\waterfall\particles\water_spray')
    add('prt3', r'fx\particles\material\water\water_spray',
        r'levels\multi\riverworld\fx\waterfall\particles\water_spray')
    add('prt3', r'levels\solo\010_jungle\fx\waterfall_stream\particles\rolling_mist',
        r'levels\multi\riverworld\fx\waterfall\particles\rolling_mist')
    add('prt3', r'levels\solo\010_jungle\fx\waterfall_stream\particles\water_spray',
        r'levels\multi\riverworld\fx\waterfall\particles\water_spray')
    add('vehi', r'reach\objects\vehicles\covenant\ghost\ghost', r'objects\vehicles\ghost\ghost')
    add('vehi', r'reach\objects\vehicles\human\mongoose\mongoose', r'objects\vehicles\mongoose\mongoose')
    add('vehi', r'reach\objects\vehicles\human\turrets\machinegun\machinegun',
        r'objects\weapons\turret\machinegun_turret\machinegun_turret')
    add('weap', r'reach\objects\vehicles\human\turrets\machinegun\weapon\machinegun_turret\machinegun_turret',
        r'objects\weapons\turret\machinegun_turret\machinegun_turret')
    add('weap', r'h2\objects\weapons\rifle\battle_rifle\battle_rifle',
        r'objects\weapons\rifle\battle_rifle\battle_rifle')
    for source, target in {
        r'rifle\smg_silenced\smg_silenced': r'rifle\smg\smg',
        r'pistol\automag\automag': r'pistol\magnum\magnum',
        r'rifle\plasma_rifle_red\plasma_rifle_red': r'rifle\plasma_rifle\plasma_rifle',
        r'pistol\needler\needler_dual': r'pistol\needler\needler',
        r'support_high\rocket_launcher\rocket_launcher_track': r'support_high\rocket_launcher\rocket_launcher',
    }.items():
        add('weap', 'objects\\weapons\\' + source, 'objects\\weapons\\' + target)
    for source, target in {
        'h2a_powerup_active_camo': 'powerup_blue',
        'h2a_powerup_overshield': 'powerup_red',
    }.items():
        add('eqip', f'objects\\multi\\powerups\\{source}\\{source}',
            f'objects\\multi\\powerups\\{target}\\{target}')
    add('rmsh', r'custom\levels\multiplayer\shaders\invisible',
        r'objects\multi\shaders\invisible')
    for source, target in {
        r'custom\vehicles\tgof_hce_banshee\hce_banshee': 'banshee',
        r'custom\vehicles\tgof_hce_banshee\brute_variant\brute_banshee': 'banshee',
        r'custom\vehicles\hce_ghost\hce_ghost': 'ghost',
        r'custom\vehicles\hce_ghost\zealot_variant\zealot_ghost': 'ghost',
        r'custom\vehicles\hce_ghost\ultra_variant\ultra_ghost': 'ghost',
        r'custom\vehicles\hce_ghost\schism_variant\schism_ghost': 'ghost',
        r'custom\vehicles\hce_ghost\brute_variant\brute_ghost': 'ghost',
        r'custom\vehicles\tgof_hce_scorpion\hce_scorpion': 'scorpion',
        r'custom\vehicles\hce_shade\hce_shade': 'shade',
        r'custom\vehicles\tgof_hce_warthog\warthog': 'warthog',
        r'custom\vehicles\tgof_hce_dewhog\tgof_hce_dewhog': 'warthog',
        r'custom\vehicles\tgof_hce_wraith\tgof_hce_wraith': 'wraith',
    }.items():
        add('vehi', source, 'objects\\vehicles\\'+target+'\\'+target)
    add('vehi', r'custom\vehicles\tgof_hce_wraith\tgof_hce_aawraith',
        r'objects\vehicles\wraith\wraith', 'anti_air')
    for source, target in {
        r'tgof_hce_assault_rifle\hce_ar': r'rifle\assault_rifle\assault_rifle',
        r'tgof_hce_assault_rifle\gold_variant\gold_ar': r'rifle\assault_rifle\assault_rifle',
        r'tgof_hce_magnum\hce_magnum': r'pistol\magnum\magnum',
        r'tgof_hce_magnum\gold_variant\gold_magnum': r'pistol\magnum\magnum',
        r'hce_sword\hce_sword': r'melee\energy_blade\energy_blade',
        r'tgof_hce_fuel_rod\hce_fuel': r'support_high\flak_cannon\flak_cannon',
        r'hce_flamethrower\hce_flamethrower': r'turret\flamethrower\flamethrower',
        r'hce_needler\hce_needler': r'pistol\needler\needler',
        r'hce_pp\hce_pp': r'pistol\plasma_pistol\plasma_pistol',
        r'hce_pr\hce_pr': r'rifle\plasma_rifle\plasma_rifle',
        r'tgof_hce_plasma_rifle\brute_variant\brute_hce_pr': r'rifle\plasma_rifle\plasma_rifle',
        r'tgof_hce_rpg\hce_rockets': r'support_high\rocket_launcher\rocket_launcher',
        r'hce_shotty\hce_shotgun': r'rifle\shotgun\shotgun',
        r'tgof_shotgun\gold_variant\shotgun_gold': r'rifle\shotgun\shotgun',
        r'hce_sniper\hce_sniper': r'rifle\sniper_rifle\sniper_rifle',
    }.items():
        add('weap', 'custom\\weapons\\hce\\'+source, 'objects\\weapons\\'+target)
    add('weap', r'custom\weapons\other\tgof_h2_battle_rifle\battle_rifle',
        r'objects\weapons\rifle\battle_rifle\battle_rifle')
    add('weap', r'custom\vehicles\hce_warthog\weapon\warthog_horn',
        r'objects\vehicles\warthog\weapon\warthog_horn')
    for source, target in {
        r'custom\weapons\hce\hce_frag\frag_grenade': r'objects\weapons\grenade\frag_grenade\frag_grenade',
        r'custom\weapons\hce\hce_plasma\plasma_grenade': r'objects\weapons\grenade\plasma_grenade\plasma_grenade',
        r'custom\powerups\hce_camo\hce_camo': r'objects\multi\powerups\powerup_blue\powerup_blue',
        r'custom\powerups\hce_overshield\hce_overshield': r'objects\multi\powerups\powerup_red\powerup_red',
    }.items():
        add('eqip', source, target)
    return result
