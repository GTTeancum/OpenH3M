"""Turn the Halo 2 Tombstone material inventory into a Halo 3 material plan for MaterialSwap build-shader.
Each Halo 2 template is mapped to the closest stock Halo 3 shader option set (original Xbox 360 options only).
Cube maps are dropped in favour of Halo 3's dynamic environment mapping.
Usage: tombstone_shader_plan.py <inventory.json> <plan.json> [map folder under levels\test, default tombstone]
(also used for Beaver Creek: map folder beavercreek)"""
import json, sys
BS = chr(92)
inv = json.load(open(sys.argv[1]))
MAP = sys.argv[3] if len(sys.argv) > 3 else 'tombstone'
H3_SAME = {'objects\\bitmaps\\reflection_maps\\dark_gray', 'shaders\\default_bitmaps\\bitmaps\\alpha_black',
           'shaders\\default_bitmaps\\bitmaps\\color_black'}
# option order: albedo, bump_mapping, alpha_test, specular_mask, material_model, environment_mapping,
#               self_illumination, blend_mode, parallax, misc, distortion, soft_fade, misc_attr_animation
TEMPLATES = {
    'tex_bump_env':             [0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    'tex_bump_env_combined':    [0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    'tex_bump':                 [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'tex_bump_active_camo':     [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'tex_bump_alpha_test':      [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'tex_bump_illum':           [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    'tex_bump_illum_bloom':     [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    'tex_bump_detail_blend':    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'tex_env':                  [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    'tex_illum':                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    'two_add_env_illum_3_channel': [0, 0, 0, 0, 4, 0, 1, 1, 0, 0, 0, 0, 0],
    'sky_two_alpha_clouds':     [0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0],
    'one_alpha_env':            [0, 0, 0, 0, 1, 1, 0, 3, 0, 0, 0, 0, 0],
    # Beaver Creek (2026-11-23)
    # ground: Halo 2 blends blend_detail_map_1/2 by the base map's alpha and multiplies an overlay detail on top; Halo 3's
    # two_detail_overlay albedo (6) is the same formula (albedo_fx.hlsl_include). The original disc has it opaque and
    # diffuse only as _6_2_0_0_0_0_0_0_1_0 (Snowbound rock_cliffs: detail bump, simple parallax); parallax is switched
    # off with height_scale 0 and the bump maps stay flat (Halo 2's ground has no bump map).
    'tex_bump_detail_blend_detail': [6, 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    # leaves and bush vines: stock Halo 3 foliage (disc _0_1_1_0_3_0_0_0_0_2, e.g. 010_jungle foliage_plants_palms on
    # zanzibar.map): foliage material model, alpha test against the base map (user 2026-11-24: leaves looked wrong)
    'tex_bump_alpha_test_single_pass': [0, 1, 1, 0, 3, 0, 0, 0, 0, 2, 0, 0, 0],
    'overlay':                  [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],       # carved overlay: multiply onto the surface (Halo 2 overlay)
    'one_alpha_env_illum':      [0, 0, 0, 0, 0, 0, 1, 3, 0, 0, 0, 0, 0],       # glowing floor arrow: self-illum, alpha blend
    # Elongation (2026-11-26)
    'two_alpha_env_illum':      [0, 0, 0, 0, 1, 1, 0, 3, 0, 0, 0, 0, 0],       # interior glass: as one_alpha_env (env + alpha blend)
    'tex_bump_plasma_one_channel_illum': [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],  # tech rack: plain self-illum; Halo 2's plasma pulse dropped
    'tex_bump_env_alpha_test_combined': [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # rebar debris: as tex_bump_alpha_test (cut-out)
}
# Halo 2 parameter -> Halo 3 parameter (bitmaps)
RENAME = {'base_map': 'base_map', 'detail_map': 'detail_map', 'secondary_detail_map': 'detail_map2',
          'bump_map': 'bump_map', 'self_illum_map': 'self_illum_map', 'alpha_test_map': 'alpha_test_map',
          # tex_bump_detail_blend_detail (two_detail_overlay)
          'blend_detail_map_1': 'detail_map', 'blend_detail_map_2': 'detail_map2', 'overlay_detail_map': 'detail_map_overlay'}


# Halo 2 textures whose exact picture ships on the original Xbox 360 Halo 3 disc under another name
# (found by texture_match.py, correlation 0.998; user decision 2026-11-20: swap exact matches only).
H3_EXACT = {
    r'scenarios\bitmaps\detail_maps\metal\metal_curvedscratch': r'levels\multi\snowbound\bitmaps\detail_metal_scratch_detail',
    r'scenarios\bitmaps\detail_maps\metal\metal_crackle': r'levels\shared\bitmaps\covenant\industrial\metals\metal_crackle_detail',
    r'scenarios\bitmaps\detail_maps\concrete\stucco_rough_a': r'levels\shared\bitmaps\multi\rock_granite_detail',
}


ENV_MAP = BS.join(['objects', 'bitmaps', 'reflection_maps', 'dark_gray.bitmap'])


def h3_bitmap(path):
    if path in H3_EXACT: return H3_EXACT[path] + '.bitmap'
    if path in H3_SAME: return path + '.bitmap'
    return 'levels\\test\\' + MAP + '\\bitmaps\\' + path.split(BS)[-1] + '.bitmap'


def color(text): return [float(x) for x in text.split(',')]


plan = []
skipped = []
for tag, e in inv.items():
    name = tag.split(BS)[-1].rsplit('.', 1)[0]
    tpl = e['template'].split(BS)[-1]
    if tpl not in TEMPLATES: skipped.append((name, tpl)); continue
    P = e['parameters']; params = []
    for h2, h3 in RENAME.items():
        p = P.get(h2)
        if not p or not p.get('bitmap'): continue
        q = {'name': h3, 'bitmap': h3_bitmap(p['bitmap'])}
        if h3 in ('base_map', 'bump_map'): q.update(bitmap_flags=1, filter_mode=4)   # as stock H3 level materials
        a = p.get('animation', {})
        if 'bitmap scale x' in a: q['scale_x'] = a['bitmap scale x'][0]; q['scale_y'] = a.get('bitmap scale y', a['bitmap scale x'])[0]
        # Texture scroll (Halo 2 'bitmap translation x/y' ramp over its time period), e.g. Elongation's conveyor belt:
        # copy stock Halo 3 Longshore's moving-belt scroll function (a linear 0 -> 10 ramp per period, conveyor_belt_2_move
        # base_map) and choose the period so the speed in texture widths per second equals Halo 2's.
        for axis, kind in (('x', 5), ('y', 6)):
            key = 'bitmap translation ' + axis; per = p.get('animation_period', {}).get(key)
            if key in a and per and len(a[key]) == 2 and a[key][1] != a[key][0]:
                rate = (a[key][1] - a[key][0]) / per
                if rate < 0: raise SystemExit(name + ': negative texture scroll not supported yet')
                q['anim_copy'] = {'from': BS.join(['levels', 'dlc', 'docks', 'shaders', 'metals', 'conveyor_belt_2_move.shader']),
                                  'param': 'base_map', 'index': 0, 'type': kind, 'period': round(10.0 / rate, 6)}
        params.append(q)
    if tpl == 'sky_two_alpha_clouds' and P.get('cloud_mask'):
        params.append({'name': 'base_map', 'bitmap': h3_bitmap(P['cloud_mask']['bitmap'])})
    if tpl in ('one_alpha_env', 'one_alpha_env_illum', 'overlay') and P.get('alpha_blend_map'):
        params.append({'name': 'base_map', 'bitmap': h3_bitmap(P['alpha_blend_map']['bitmap'])})
    opts = TEMPLATES[tpl]
    if tpl == 'tex_bump_alpha_test_single_pass' and P.get('base_map', {}).get('bitmap'):
        # Halo 2 alpha-tests against the base map's alpha; Halo 3's alpha test reads alpha_test_map (stock foliage sets
        # it to the base map)
        params.append({'name': 'alpha_test_map', 'bitmap': h3_bitmap(P['base_map']['bitmap'])})
    if tpl == 'tex_bump_detail_blend_detail':
        params.append({'name': 'height_scale', 'real': 0.0})   # parallax off (see TEMPLATES)
    if opts[6]:   # self-illumination: colour and strength from Halo 2's emissive values
        c = P.get('self_illum_color') or P.get('emissive_color')
        params.append({'name': 'self_illum_color', 'color': color(c['color']) if c and c.get('color') else [1, 1, 1]})
        # bloom template (stadium/wall lights) glows hard enough to bloom, as in Halo 2
        # Beaver Creek's Forerunner light panels (same template) burned out to flat white at 6 (survey 2026-11-24): 1.0
        params.append({'name': 'self_illum_intensity', 'real': 6.0 if tpl == 'tex_bump_illum_bloom' and MAP != 'beavercreek' else 1.0})
    if opts[4] == 1:  # cook_torrance: Halo 2 specular colour drives the tint; modest coefficient
        sc = P.get('specular_color')
        if sc and sc.get('color'): params.append({'name': 'specular_tint', 'color': color(sc['color'])})
        # Fixed reflection image like Halo 2 (per-pixel environment map); Tombstone has no baked dynamic cubemaps.
        # Stock H3 objects/bitmaps/reflection_maps/dark_gray (on 25 disc maps): muted, suits the overcast sky.
        # Sun highlights kept low for the cloudy sky (user, 2026-11-20).
        params.append({'name': 'environment_map', 'bitmap': ENV_MAP})
        params.append({'name': 'env_tint_color', 'color': [1, 1, 1]})
        # Halo 2 gave these metals baked-light shine ("default specular" lightmap type); Halo 3's equivalent is
        # specular from the baked lighting (area/analytical contributions). Moderate, broad (overcast sky).
        if e.get('lightmap_type') == 'default specular':
            params += [{'name': 'specular_coefficient', 'real': 0.3}, {'name': 'area_specular_contribution', 'real': 0.5},
                       {'name': 'analytical_specular_contribution', 'real': 0.3}, {'name': 'roughness', 'real': 0.35}]
        else:
            params.append({'name': 'specular_coefficient', 'real': 0.15})
        params.append({'name': 'environment_map_specular_contribution', 'real': (P.get('env_brightness') or {}).get('value') or 0.3})
    plan.append({'tag': 'levels\\test\\' + MAP + '\\shaders\\' + name + '.shader', 'definition': 'shaders\\shader.render_method_definition',
                 'options': opts, 'params': params})
json.dump(plan, open(sys.argv[2], 'w'), indent=1)
print('materials planned', len(plan), 'not planned', skipped)
