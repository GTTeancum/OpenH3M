"""Turn the Halo 2 Tombstone material inventory into a Halo 3 material plan for MaterialSwap build-shader.
Each Halo 2 template is mapped to the closest stock Halo 3 shader option set (original Xbox 360 options only).
Cube maps are dropped in favour of Halo 3's dynamic environment mapping.
Usage: tombstone_shader_plan.py <inventory.json> <plan.json>"""
import json, sys
BS = chr(92)
inv = json.load(open(sys.argv[1]))
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
}
# Halo 2 parameter -> Halo 3 parameter (bitmaps)
RENAME = {'base_map': 'base_map', 'detail_map': 'detail_map', 'secondary_detail_map': 'detail_map2',
          'bump_map': 'bump_map', 'self_illum_map': 'self_illum_map', 'alpha_test_map': 'alpha_test_map'}


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
    return 'levels\\test\\tombstone\\bitmaps\\' + path.split(BS)[-1] + '.bitmap'


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
        params.append(q)
    if tpl == 'sky_two_alpha_clouds' and P.get('cloud_mask'):
        params.append({'name': 'base_map', 'bitmap': h3_bitmap(P['cloud_mask']['bitmap'])})
    if tpl == 'one_alpha_env' and P.get('alpha_blend_map'):
        params.append({'name': 'base_map', 'bitmap': h3_bitmap(P['alpha_blend_map']['bitmap'])})
    opts = TEMPLATES[tpl]
    if opts[6]:   # self-illumination: colour and strength from Halo 2's emissive values
        c = P.get('self_illum_color') or P.get('emissive_color')
        params.append({'name': 'self_illum_color', 'color': color(c['color']) if c and c.get('color') else [1, 1, 1]})
        # bloom template (stadium/wall lights) glows hard enough to bloom, as in Halo 2
        params.append({'name': 'self_illum_intensity', 'real': 6.0 if tpl == 'tex_bump_illum_bloom' else 1.0})
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
    plan.append({'tag': 'levels\\test\\tombstone\\shaders\\' + name + '.shader', 'definition': 'shaders\\shader.render_method_definition',
                 'options': opts, 'params': params})
json.dump(plan, open(sys.argv[2], 'w'), indent=1)
print('materials planned', len(plan), 'not planned', skipped)
