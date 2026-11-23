"""Reach DMR -> H3 tags, staged. Usage: python build.py <stage>

  bitmaps   Reach DMR textures (official HREK export-bitmap-tga) -> 512px TIFF -> H3 tool bitmaps;
            normal map re-imported as a normal map with tool patch-tag-field + bitmap_single
  shaders   copy stock battle_rifle shaders to reach_dmr names, swap DMR base/bump maps (ManagedBlam)
  jms       rig Reach DMR onto stock battle_rifle (3p, reduced) and fp_battle_rifle (fp, full) skeletons
  render    tool.exe render (draft) for both; compare compiled nodes with stock
  objects   model / weapon / projectile / damage effect from stock BR copies + Reach DMR values
"""
import json, sys
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import kit, blender_env

BS = chr(92)
def wp(*p): return BS.join(p)
R = wp('objects', 'weapons', 'rifle', 'reach_dmr')
FP = wp(R, 'fp_reach_dmr')
BR = wp('objects', 'weapons', 'rifle', 'battle_rifle')
P = 'Struct:render_method[0]/'
W = kit.WORK / 'reach_dmr'
TEX = 512  # stock H3 360 weapon texture size (battle_rifle / magnum bitmaps are 512x512)


def bitmaps():
    tga = W / 'tga'
    data = kit.DATA / R / 'bitmaps'; data.mkdir(parents=True, exist_ok=True)
    d = Image.open(tga / 'dmr_diffusedmr_diffuse_00_00.tga').convert('RGBA').resize((TEX, TEX), Image.LANCZOS)
    d.save(data / 'reach_dmr_diffuse.tif', compression='tiff_lzw')
    n = Image.open(tga / 'dmr_normaldmr_normal_00_00.tga').convert('RGB').resize((TEX, TEX), Image.LANCZOS)
    # Reach stores a two-channel (DXN) normal; rebuild Z for an RGB normal image.
    import numpy as np
    a = np.asarray(n).astype(np.float32) / 127.5 - 1.0
    z = np.sqrt(np.clip(1.0 - a[..., 0] ** 2 - a[..., 1] ** 2, 0, 1))
    a[..., 2] = z
    Image.fromarray(np.clip((a + 1.0) * 127.5 + 0.5, 0, 255).astype(np.uint8)).save(data / 'reach_dmr_normal.tif', compression='tiff_lzw')
    rc, out = kit.htool('bitmaps', wp(R, 'bitmaps'), log=W / 'bitmaps.log', timeout=600)
    print(rc, out[-600:])
    tag = wp(R, 'bitmaps', 'reach_dmr_normal.bitmap')
    rc, out = kit.htool('patch-tag-field', tag, 'bitmap_block_struct[0].Usage', 'ZBrush Bump Map (from Bump Map)', log=W / 'normal-patch.log')
    print('patch', rc, out.strip()[-200:])
    rc, out = kit.htool('bitmap_single', str(Path(R) / 'bitmaps' / 'reach_dmr_normal.tif'), log=W / 'normal-reimport.log')
    print('reimport', rc, out.strip()[-300:])
    x = kit.to_xml(tag, W / 'reach_dmr_normal.bitmap.xml').read_text(errors='replace')
    import re
    print('NORMAL', re.findall(r'name="(Usage|format|width|height)" value="([^"]*)"', x)[:6])


def param_index(dump, name):
    for l in Path(dump).read_text().splitlines():
        if l.startswith(P + 'Block:parameters[') and '/parameter name\t' in l and l.endswith('\t' + name):
            return int(l.split('Block:parameters[')[1].split(']')[0])
    raise KeyError(name)


def shaders():
    diff = wp(R, 'bitmaps', 'reach_dmr_diffuse.bitmap'); norm = wp(R, 'bitmaps', 'reach_dmr_normal.bitmap')
    specs = [  # name, stock donor, option changes, {param: bitmap}
        ('reach_dmr_metal', 'battle_rifle_metal', {6: 0}, {'base_map': diff, 'bump_map': norm}),
        ('reach_dmr_metal_shiny', 'battle_rifle_metal', {6: 0}, {'base_map': diff, 'bump_map': norm}),
        ('reach_dmr_rubber', 'battle_rifle_rubber', {}, {'base_map': diff, 'bump_map': norm}),
        ('reach_dmr_lens', 'battle_rifle_lens', {}, {'base_map': diff}),
        ('ones', 'ones', {}, {}),  # unchanged stock ammo-counter digits; copied because tool only searches the model's own shader folder
        ('tens', 'tens', {}, {}),
    ]
    ops = []
    for name, donor, opts, params in specs:
        dump = kit.dump(wp(BR, 'shaders', donor + '.shader'))
        tag = wp(R, 'shaders', name + '.shader')
        ops.append({'op': 'copy', 'from': wp(BR, 'shaders', donor + '.shader'), 'to': tag})
        for i, v in opts.items():
            ops.append({'op': 'set', 'tag': tag, 'field': P + 'Block:options[%d]/short' % i, 'value': str(v)})
        for pname, bmp in params.items():
            ops.append({'op': 'set', 'tag': tag, 'field': P + 'Block:parameters[%d]/bitmap' % param_index(dump, pname), 'value': bmp})
    print(kit.edit(ops, 'dmr_shaders'))


MATERIALS = {  # Reach DMR shader -> H3 shader (new copies, or stock reused unchanged)
    'dmr_metal': 'reach_dmr_metal', 'dmr_composite': 'reach_dmr_metal', 'dmr_metal_shiny': 'reach_dmr_metal_shiny',
    'dmr_rubber': 'reach_dmr_rubber', 'dmr_lens': 'reach_dmr_lens', 'dmr_lens_glass': 'reach_dmr_lens',
    'ones_dmr': 'ones', 'tens_dmr': 'tens', 'unsc_decals_fp': 'reach_dmr_metal',
}


def jms(which):
    stock = wp(BR, 'battle_rifle.render_model') if which == '3p' else wp(BR, 'fp_battle_rifle', 'fp_battle_rifle.render_model')
    donor = kit.to_xml(stock, kit.WORK / 'donor-xml' / (stock.split(BS)[-1] + '.xml'))
    cfg = dict(donor_xml=str(donor), foundry_transform=True, mesh_objects=['default:default'],
               group_map={'b_gun': 'gun', 'b_magazine': 'magazine', 'b_ophandle': 'ophandle', 'b_safety': 'safety'},
               material_map=MATERIALS, object_name='reach_dmr', precise=True, reach_face_flags=True, region='standard', permutation='standard',
               align={'source_armature': 'dmr', 'source_bone': 'b_gun', 'donor_node': 'gun'},
               markers={'flashlight': {'from_object': 'flashlight'}, 'left_hand': {'from_object': 'left_hand'},
                        'muzzle_flash': {'from_object': 'muzzle_flash'}, 'primary_ejection': {'from_object': 'primary_ejection'},
                        'primary_trigger': {'from_object': 'primary_trigger'}})
    if which == '3p':
        cfg['markers']['weapon_stow_anchor'] = {'from_object': 'weapon_stow_anchor'}
        cfg.update(drop_detail_close=True, decimate_ratio=0.48, out_jms=str(kit.DATA / R / 'render' / 'reach_dmr.jms'), out_blend=str(W / 'reach_dmr-3p-rigged.blend'))
    else:
        cfg.update(out_jms=str(kit.DATA / FP / 'render' / 'fp_reach_dmr.jms'), out_blend=str(W / 'reach_dmr-fp-rigged.blend'))
    cp = W / ('rig-%s.json' % which); cp.write_text(json.dumps(cfg, indent=1))
    rc, out = blender_env.run(HERE.parent / 'build_rigged_jms.py', cp, blend=W / 'dmr-source.blend', log=W / ('rig-%s.log' % which))
    print('\n'.join(l for l in out.splitlines() if l.startswith(('RIGGED_JMS', 'ALIGN', 'DECIMATED', 'Error', 'Traceback', '  File', 'SystemExit', 'KeyError'))))
    if rc: print(out[-3000:]); raise SystemExit(rc)


def nodes_of(xml_path):
    x = kit.parse_xml(xml_path)
    return [(f['name'], f['parent node'].split(',')[-1], f['default translation'], f['default rotation'])
            for f in (kit.fields(e) for e in x.find("./block[@name='nodes']"))]


def render():
    for rel, stock in [(R, 'battle_rifle.render_model'), (FP, 'fp_battle_rifle.render_model')]:
        name = rel.split(BS)[-1]
        rc, out = kit.htool('render', rel, 'draft', log=W / ('render-%s.log' % name), timeout=900)
        print(name, 'rc', rc, *[l for l in out.splitlines() if 'triangles' in l or 'ERROR' in l or ('WARNING' in l and 'leaking' not in l)][-12:], sep='\n  ')
        tag = wp(rel, name + '.render_model')
        if not (kit.TAGS / tag).exists(): print(out[-3000:]); raise SystemExit('no render model')
        mine = nodes_of(kit.to_xml(tag, W / (name + '.render_model.xml'))); ref = nodes_of(kit.WORK / 'donor-xml' / (stock + '.xml'))
        print('  NODES_MATCH' if [m[:2] for m in mine] == [s[:2] for s in ref] else '  NODE_LIST_DIFFERS')
        for m, s in zip(mine, ref): print('   ', m[0], 'T', m[2], '| stock', s[2], ' R', m[3], '| stock', s[3])


# Reach DMR values (official HREK tags: dmr.weapon, dmr_bullet.projectile, dmr_bullet.damage_effect).
REACH = dict(damage=17.5, rounds_per_second=3.0, recovery=0.33, soft_recovery=0.2, error_angle=(0.15, 2.0),
             loaded=15, total_initial=45, total_max=75, zoom=3.0, velocity=3000.0, max_range=250.0,
             air_range=(0.0, 40.0), water_range=(0.0, 10.0), autoaim_angle=2.25, autoaim_range=20.0,
             autoaim_falloff=10.0, magnetism_angle=5.0, magnetism_range=20.0)
STRINGS = dict(pickup='dmr_pickup', swap='dmr_swap')


def objects():
    de = wp(R, 'reach_dmr_bullet.damage_effect'); pr = wp(R, 'reach_dmr_bullet.projectile')
    md = wp(R, 'reach_dmr.model'); wpn = wp(R, 'reach_dmr.weapon')
    B = 'Block:barrels[0]/'; V = REACH
    ops = [
        {'op': 'copy', 'from': wp(BR, 'damage_effects', 'battle_rifle_bullet.damage_effect'), 'to': de},
        {'op': 'set', 'tag': de, 'field': 'damage lower bound', 'value': str(V['damage'])},
        {'op': 'set', 'tag': de, 'field': 'damage upper bound', 'value': '%s,%s' % (V['damage'], V['damage'])},
        {'op': 'copy', 'from': wp(BR, 'projectiles', 'battle_rifle_bullet.projectile'), 'to': pr},
        {'op': 'set', 'tag': pr, 'field': 'impact damage', 'value': de},
        {'op': 'set', 'tag': pr, 'field': 'initial velocity', 'value': str(V['velocity'])},
        {'op': 'set', 'tag': pr, 'field': 'final velocity', 'value': str(V['velocity'])},
        {'op': 'set', 'tag': pr, 'field': 'maximum range', 'value': str(V['max_range'])},
        {'op': 'set', 'tag': pr, 'field': 'air damage range', 'value': '%s,%s' % V['air_range']},
        {'op': 'set', 'tag': pr, 'field': 'water damage range', 'value': '%s,%s' % V['water_range']},
        {'op': 'copy', 'from': wp(BR, 'battle_rifle.model'), 'to': md},
        {'op': 'set', 'tag': md, 'field': 'render model', 'value': wp(R, 'reach_dmr.render_model')},
        {'op': 'set', 'tag': md, 'field': 'lod_render_model', 'value': ''},
        {'op': 'copy', 'from': wp(BR, 'battle_rifle.weapon'), 'to': wpn},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:item[0]/Struct:object[0]/model', 'value': md},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:player interface[0]/Block:first person[0]/first person model', 'value': wp(FP, 'fp_reach_dmr.render_model')},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:player interface[0]/Block:first person[1]/first person model', 'value': wp(FP, 'fp_reach_dmr.render_model')},
        {'op': 'set', 'tag': wpn, 'field': 'Block:new triggers[0]/behavior', 'value': 'latch'},
        {'op': 'set', 'tag': wpn, 'field': B + 'projectile', 'value': pr},
        {'op': 'set', 'tag': wpn, 'field': B + 'Struct:firing[0]/rounds per second', 'value': '%s,%s' % (V['rounds_per_second'], V['rounds_per_second'])},
        {'op': 'set', 'tag': wpn, 'field': B + 'Struct:firing[0]/shots per fire', 'value': '1,1'},
        {'op': 'set', 'tag': wpn, 'field': B + 'Struct:firing[0]/fire recovery time', 'value': str(V['recovery'])},
        {'op': 'set', 'tag': wpn, 'field': B + 'Struct:firing[0]/soft recovery fraction', 'value': str(V['soft_recovery'])},
        {'op': 'set', 'tag': wpn, 'field': B + 'error angle', 'value': '%s,%s' % V['error_angle']},
        {'op': 'set', 'tag': wpn, 'field': 'Block:magazines[0]/rounds loaded maximum', 'value': str(V['loaded'])},
        {'op': 'set', 'tag': wpn, 'field': 'Block:magazines[0]/rounds reloaded', 'value': str(V['loaded'])},
        {'op': 'set', 'tag': wpn, 'field': 'Block:magazines[0]/rounds total initial', 'value': str(V['total_initial'])},
        {'op': 'set', 'tag': wpn, 'field': 'Block:magazines[0]/rounds total maximum', 'value': str(V['total_max'])},
        {'op': 'set', 'tag': wpn, 'field': 'Block:magazines[0]/Block:magazines[0]/rounds', 'value': str(2 * V['loaded'])},
        {'op': 'set', 'tag': wpn, 'field': 'magnification range', 'value': '%s,%s' % (V['zoom'], V['zoom'])},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:weapon aim assist[0]/autoaim angle', 'value': str(V['autoaim_angle'])},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:weapon aim assist[0]/autoaim range', 'value': str(V['autoaim_range'])},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:weapon aim assist[0]/autoaim falloff range', 'value': str(V['autoaim_falloff'])},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:weapon aim assist[0]/magnetism angle', 'value': str(V['magnetism_angle'])},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:weapon aim assist[0]/magnetism range', 'value': str(V['magnetism_range'])},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:item[0]/pickup message', 'value': STRINGS['pickup']},
        {'op': 'set', 'tag': wpn, 'field': 'Struct:item[0]/swap message', 'value': STRINGS['swap']},
    ]
    print(kit.edit(ops, 'dmr_objects'))
    for t in (de, pr, md, wpn): kit.dump(t, W / ('final-' + t.split(BS)[-1] + '.txt'))


if __name__ == '__main__':
    {'bitmaps': bitmaps, 'shaders': shaders, 'jms3p': lambda: jms('3p'), 'jmsfp': lambda: jms('fp'),
     'render': render, 'objects': objects}[sys.argv[1]]()
