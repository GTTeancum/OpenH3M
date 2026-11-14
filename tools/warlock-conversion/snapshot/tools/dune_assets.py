"""Exact-purpose native H3 assets, without replacing Dune's animated structures."""
SCENARIO = r'levels\multi\dune\dune'
LIFT = r'objects\gear\covenant\military\cov_watchtower\fx\gravlift\gravlift'
SOURCES = (
    r'levels\objects\covenant\military\cov_lookout_tower\effects\gravlift',
    r'h2\scenarios\objects\covenant\military\cov_lookout_tower\effects\gravlift',
)
LIFT_DIFFERENCE = {
    'policy': 'Native H3 Covenant watchtower light-volume replaces the H2 port visual, not shader-equivalent',
    'donor': 'snowbound.map',
    'source': {'brightness_ratio': 1.0, 'blend': 'additive',
               'profile_constants': [2, 0, 0, 2, 1, 0, 0, 8]},
    'native': {'brightness_ratio': 2.0, 'blend': 'add_src_times_srcalpha',
               'profile_constants': [4, 0, 2, 2.5, 0, 0, 0, 1]},
    'preserved': 'Source animated machine geometry, placement, attachment markers and parent effect timing/envelope',
}

TURRET_SOURCE = r'objects\vehicles\c_turret_ap\weapon\projectile'
TURRET_TARGET = r'objects\vehicles\shade\fx\weapon\projectile'
TURRET_DIFFERENCE = {
    'policy': 'Native H3 Shade plasma-turret projectile light-volume, not a shader-equivalent',
    'donor': 'guardian.map',
    'source': {'brightness_ratio':3.0, 'blend':'additive', 'profile_constants':[1.5,0,32,0.15,0,0,1,0]},
    'native': {'brightness_ratio':3.333329916, 'blend':'add_src_times_srcalpha', 'profile_constants':[1.5,-1,32,0.15,0,0,1,0]},
    'preserved':'Custom Creep projectile damage/physics and weapon timing; only light-volume visual uses native Shade counterpart',
}


def visual_difference(key):
    return TURRET_DIFFERENCE if key==('ltvl',TURRET_SOURCE) else LIFT_DIFFERENCE


def native_aliases(source):
    if [source.name(k) for k, t in source.tags.items() if t['group'] == 'scnr'] != [SCENARIO]:
        return {}
    result = {('ltvl', name): ('ltvl', LIFT, None) for name in SOURCES}
    result['ltvl',TURRET_SOURCE]=('ltvl',TURRET_TARGET,None)
    return result
