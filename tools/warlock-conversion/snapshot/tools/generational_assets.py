"""Explicit Halo Generational Combat -> stock Halo 3 gameplay equivalents.

Map geometry stays authored. Cosmetic faction/gold variants use stock behavior,
as required by the user's Halo 3 asset policy. Unlisted unique objects still
follow normal conversion; no substring matching silently replaces new assets.
"""


def stock_aliases():
    result = {}
    def add(group, source, target, variant=None):
        result[group, source] = group, target, variant
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
