"""Write the MaterialSwap build-shader plan for Tombstone's sky (Halo 2 highplains sky materials on Halo 3 options).
Usage: tombstone_sky_shaders.py <plan.json> [dome glow intensity]"""
import json, sys
BS = chr(92)
B = BS.join(['levels', 'test', 'tombstone', 'sky', 'bitmaps', ''])
S = BS.join(['levels', 'test', 'tombstone', 'sky', 'shaders', ''])
BLACK = BS.join(['shaders', 'default_bitmaps', 'bitmaps', 'color_black.bitmap'])
ABLACK = BS.join(['shaders', 'default_bitmaps', 'bitmaps', 'alpha_black.bitmap'])
D = BS.join(['shaders', 'shader.render_method_definition'])
GLOW = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
ILLUM = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]   # self-lit, opaque (sky dome)
CLOUD = [0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0]   # lit, alpha blend (as Last Resort's sky clouds)
plan = [
    {'tag': S + 'highplains_sky_dome.shader', 'definition': D, 'options': ILLUM, 'params': [
        {'name': 'base_map', 'bitmap': BLACK}, {'name': 'self_illum_map', 'bitmap': B + 'tombstone_sky_dome.bitmap'},
        {'name': 'self_illum_color', 'color': [1, 1, 1]}, {'name': 'self_illum_intensity', 'real': GLOW}]},
    {'tag': S + 'highplains_clouds_low.shader', 'definition': D, 'options': CLOUD, 'params': [
        {'name': 'base_map', 'bitmap': B + 'highplains_clouds_low_mask.bitmap'},
        {'name': 'detail_map', 'bitmap': B + 'nm_clouds.bitmap', 'scale_x': 5, 'scale_y': 5}]},
    {'tag': S + 'highplains_skysmoke.shader', 'definition': D, 'options': CLOUD, 'params': [
        {'name': 'base_map', 'bitmap': B + 'skysmoke.bitmap'},
        {'name': 'detail_map', 'bitmap': B + 'ec_clouds2.bitmap', 'scale_x': 2, 'scale_y': 2}]},
    {'tag': S + 'highplains_ruins.shader', 'definition': D, 'options': CLOUD, 'params': [
        {'name': 'base_map', 'bitmap': B + 'highplains_ruined_city.bitmap'}]},
    {'tag': S + 'highplains_ruins_backing.shader', 'definition': D, 'options': CLOUD, 'params': [
        {'name': 'base_map', 'bitmap': B + 'highplains_ruined_city_backing.bitmap'}]},
    {'tag': S + 'lightning_c.shader', 'definition': D, 'options': CLOUD, 'params': [{'name': 'base_map', 'bitmap': ABLACK}]},
]
json.dump(plan, open(sys.argv[1], 'w'), indent=1)
print('planned', len(plan))
