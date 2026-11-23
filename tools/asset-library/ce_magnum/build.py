"""CE Magnum -> H3 tags, staged. Usage: python build.py <stage> [...]

Stages (each drives official tools only):
  shaders   copy stock magnum shaders to ce_magnum names, swap CE base maps (ManagedBlam)
  jms3p     rig CE 3rd-person mesh onto stock magnum skeleton, export JMS (Blender + General-101)
  jmsfp     rig CE 1st-person mesh onto stock fp_magnum skeleton, export JMS
  render    tool.exe render for both models, then compare compiled nodes with stock
  objects   model / weapon / projectile / damage effect tags from stock copies + CE values
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import kit, blender_env

R = 'objects\\weapons\\pistol\\ce_magnum'
FP = R + '\\fp_ce_magnum'
MAG = 'objects\\weapons\\pistol\\magnum'
P = 'Struct:render_method[0]/'
W = kit.WORK / 'ce_magnum'


def param_index(dump, name):
    for l in Path(dump).read_text().splitlines():
        if l.startswith(P + 'Block:parameters[') and '/parameter name\t' in l and l.endswith('\t' + name):
            return int(l.split('Block:parameters[')[1].split(']')[0])
    raise KeyError(name)


def shaders():
    dm = kit.dump(MAG + '\\shaders\\magnum.shader'); dd = kit.dump(MAG + '\\shaders\\magnum_dull.shader')
    specs = [('ce_magnum_silver', 'magnum', dm, {1: 0, 6: 0}, R + '\\bitmaps\\ce_magnum.bitmap'),
             ('ce_magnum_black', 'magnum_dull', dd, {1: 0, 3: 0}, R + '\\bitmaps\\ce_magnum.bitmap'),
             ('ce_magnum_bullet', 'magnum_dull', dd, {1: 0, 3: 0}, R + '\\bitmaps\\ce_magnum_bullet.bitmap')]
    ops = []
    for name, donor, dump, opts, bmp in specs:
        tag = R + '\\shaders\\' + name + '.shader'
        ops.append({'op': 'copy', 'from': MAG + '\\shaders\\' + donor + '.shader', 'to': tag})
        for i, v in opts.items():
            ops.append({'op': 'set', 'tag': tag, 'field': P + 'Block:options[%d]/short' % i, 'value': str(v)})
        ops.append({'op': 'set', 'tag': tag, 'field': P + 'Block:parameters[%d]/bitmap' % param_index(dump, 'base_map'), 'value': bmp})
    print(kit.edit(ops, 'ce_shaders'))
    for name, *_ in specs:
        d = kit.dump(R + '\\shaders\\' + name + '.shader').read_text().splitlines()
        print(name, 'options', [l.split('\t')[2] for l in d if 'Block:options[' in l],
              [l.split('\t')[2] for l in d if l.split('\t')[0].endswith('/bitmap') and l.split('\t')[2]])


def jms(which, quat_mode='as_is'):
    donor = kit.to_xml(MAG + ('\\magnum.render_model' if which == '3p' else '\\fp_magnum\\fp_magnum.render_model'),
                       kit.WORK / 'donor-xml' / ('magnum.render_model.xml' if which == '3p' else 'fp_magnum.render_model.xml'))
    common_groups = {'frame gun': 'gun', 'frame magazine': 'magazine', 'frame slide': 'slide',
                     'frame chamber_button': 'slide', 'frame slide_release': 'gun', 'frame trigger': 'gun'}
    if which == '3p':
        cfg = dict(source_blend=str(W / 'ce-3p-inspect.blend'), mesh_objects=['unnamed base superhigh'],
                   group_map=common_groups, material_map={'silver': 'ce_magnum_silver', 'black': 'ce_magnum_black'},
                   markers={'flashlight': {}, 'left_hand': {}, 'magazine': {}, 'weapon_stow_anchor': {},
                            'primary_trigger': {'from_object': '#primary trigger'},
                            'primary_ejection': {'from_object': '#primary ejection'}},
                   out_jms=str(kit.DATA / R / 'render' / 'ce_magnum.jms'), out_blend=str(W / 'ce_magnum-3p-rigged.blend'))
    else:
        g = dict(common_groups); g['frame bullet'] = 'slide'
        cfg = dict(source_blend=str(W / 'ce-fp-inspect.blend'), mesh_objects=['unnamed pistol fp superhigh'],
                   group_map=g, material_map={'silver': 'ce_magnum_silver', 'black': 'ce_magnum_black', 'bullet': 'ce_magnum_bullet'},
                   markers={'flashlight': {}, 'left_hand': {}, 'magazine': {},
                            'primary_trigger': {'from_object': '#primary trigger'},
                            'primary_ejection': {'from_object': '#primary ejection'}},
                   out_jms=str(kit.DATA / FP / 'render' / 'fp_ce_magnum.jms'), out_blend=str(W / 'ce_magnum-fp-rigged.blend'))
    cfg.update(donor_xml=str(donor), quat_mode=quat_mode, object_name='ce_magnum', precise=True, region='gun', permutation='base',
               align={'source_armature': 'Armature', 'source_bone': 'frame gun', 'donor_node': 'gun'})
    cp = W / ('rig-%s.json' % which); cp.write_text(json.dumps(cfg, indent=1))
    rc, out = blender_env.run(HERE.parent / 'build_rigged_jms.py', cp, blend=cfg['source_blend'], log=W / ('rig-%s.log' % which))
    print('\n'.join(l for l in out.splitlines() if l.startswith(('RIGGED_JMS', 'ALIGN', 'Error', 'Traceback', '  File', 'SystemExit', 'WARNING'))))
    if rc: print(out[-3000:]); raise SystemExit(rc)


def nodes_of(xml_path):
    x = kit.parse_xml(xml_path)
    return [(f['name'], f['parent node'].split(',')[-1], f['default translation'], f['default rotation'])
            for f in (kit.fields(e) for e in x.find("./block[@name='nodes']"))]


def render():
    for rel, donor in [(R, MAG + '\\magnum.render_model'), (FP, MAG + '\\fp_magnum\\fp_magnum.render_model')]:
        name = rel.split('\\')[-1]
        rc, out = kit.htool('render', rel, 'draft', log=W / ('render-%s.log' % name), timeout=900)
        tris = [l for l in out.splitlines() if 'triangles' in l or 'WARNING' in l or 'ERROR' in l or 'shader' in l.lower()]
        print(name, 'rc', rc, *tris[-12:], sep='\n  ')
        tag = rel + '\\' + name + '.render_model'
        if not (kit.TAGS / tag).exists():
            print(out[-3000:]); raise SystemExit('no render model')
        mine = nodes_of(kit.to_xml(tag, W / (name + '.render_model.xml')))
        stock = nodes_of(kit.WORK / 'donor-xml' / (donor.split('\\')[-1] + '.xml'))
        print('  NODES_MATCH' if [m[:2] for m in mine] == [s[:2] for s in stock] else '  NODE_LIST_DIFFERS')
        for m, s in zip(mine, stock):
            print('   ', m[0], 'T', m[2], '| stock', s[2], ' R', m[3], '| stock', s[3])


# CE values read from the official HCEEK tags (General-101 reader; JSON under _work/ce_magnum/ce-tags).
CE = dict(damage=25.0, rate_of_fire=3.5, error_angle=(0.2, 2.0), error_accel=0.5, error_decel=0.2,
          loaded=12, total_initial=60, reserve_max=120, zoom=2.0, velocity=300.0, max_range=40.0,
          air_range=(0.0, 100.0), water_range=(0.0, 10.0), autoaim_angle=3.0, autoaim_range=30.0,
          magnetism_angle=6.0, magnetism_range=30.0)
STRINGS = dict(pickup='ce_mp_pickup', swap='ce_mp_swap', dual='ce_mp_dual', dual_swap='ce_mp_dual_swap')


def objects():
    de = R + '\\ce_magnum_bullet.damage_effect'
    pr = R + '\\ce_magnum_bullet.projectile'
    md = R + '\\ce_magnum.model'
    wp = R + '\\ce_magnum.weapon'
    B = 'Block:barrels[0]/'
    ops = [
        {'op': 'copy', 'from': MAG + '\\damage_effects\\magnum_bullet.damage_effect', 'to': de},
        {'op': 'set', 'tag': de, 'field': 'damage lower bound', 'value': str(CE['damage'])},
        {'op': 'set', 'tag': de, 'field': 'damage upper bound', 'value': '%s,%s' % (CE['damage'], CE['damage'])},
        {'op': 'copy', 'from': MAG + '\\projectiles\\magnum_bullet.projectile', 'to': pr},
        {'op': 'set', 'tag': pr, 'field': 'impact damage', 'value': de},
        {'op': 'set', 'tag': pr, 'field': 'initial velocity', 'value': str(CE['velocity'])},
        {'op': 'set', 'tag': pr, 'field': 'final velocity', 'value': str(CE['velocity'])},
        {'op': 'set', 'tag': pr, 'field': 'maximum range', 'value': str(CE['max_range'])},
        {'op': 'set', 'tag': pr, 'field': 'air damage range', 'value': '%s,%s' % CE['air_range']},
        {'op': 'set', 'tag': pr, 'field': 'water damage range', 'value': '%s,%s' % CE['water_range']},
        {'op': 'copy', 'from': MAG + '\\magnum.model', 'to': md},
        {'op': 'set', 'tag': md, 'field': 'render model', 'value': R + '\\ce_magnum.render_model'},
        {'op': 'set', 'tag': md, 'field': 'lod_render_model', 'value': ''},
        {'op': 'copy', 'from': MAG + '\\magnum.weapon', 'to': wp},
        {'op': 'set', 'tag': wp, 'field': 'Struct:item[0]/Struct:object[0]/model', 'value': md},
        {'op': 'set', 'tag': wp, 'field': 'Struct:player interface[0]/Block:first person[0]/first person model', 'value': FP + '\\fp_ce_magnum.render_model'},
        {'op': 'set', 'tag': wp, 'field': 'Struct:player interface[0]/Block:first person[1]/first person model', 'value': FP + '\\fp_ce_magnum.render_model'},
        {'op': 'set', 'tag': wp, 'field': B + 'projectile', 'value': pr},
        {'op': 'set', 'tag': wp, 'field': B + 'Struct:firing[0]/fire recovery time', 'value': str(round(1.0 / CE['rate_of_fire'], 6))},
        {'op': 'set', 'tag': wp, 'field': B + 'error angle', 'value': '%s,%s' % CE['error_angle']},
        {'op': 'set', 'tag': wp, 'field': B + 'Struct:firing error[0]/acceleration time', 'value': str(CE['error_accel'])},
        {'op': 'set', 'tag': wp, 'field': B + 'Struct:firing error[0]/deceleration time', 'value': str(CE['error_decel'])},
        {'op': 'set', 'tag': wp, 'field': 'Block:magazines[0]/rounds loaded maximum', 'value': str(CE['loaded'])},
        {'op': 'set', 'tag': wp, 'field': 'Block:magazines[0]/rounds reloaded', 'value': str(CE['loaded'])},
        {'op': 'set', 'tag': wp, 'field': 'Block:magazines[0]/rounds total initial', 'value': str(CE['total_initial'])},
        {'op': 'set', 'tag': wp, 'field': 'Block:magazines[0]/rounds total maximum', 'value': str(CE['reserve_max'] + CE['loaded'])},
        {'op': 'set', 'tag': wp, 'field': 'magnification levels', 'value': '1'},
        {'op': 'set', 'tag': wp, 'field': 'magnification range', 'value': '%s,%s' % (CE['zoom'], CE['zoom'])},
        {'op': 'set', 'tag': wp, 'field': 'zoom-in sound', 'value': 'sound\\weapons\\battle_rifle\\battle_rifle_zoom_in.sound'},
        {'op': 'set', 'tag': wp, 'field': 'zoom-out sound', 'value': 'sound\\weapons\\battle_rifle\\battle_rifle_zoom_out.sound'},
        {'op': 'set', 'tag': wp, 'field': 'weapon zoom time', 'value': '0.2'},
        {'op': 'set', 'tag': wp, 'field': 'Struct:weapon aim assist[0]/autoaim angle', 'value': str(CE['autoaim_angle'])},
        {'op': 'set', 'tag': wp, 'field': 'Struct:weapon aim assist[0]/autoaim range', 'value': str(CE['autoaim_range'])},
        {'op': 'set', 'tag': wp, 'field': 'Struct:weapon aim assist[0]/magnetism angle', 'value': str(CE['magnetism_angle'])},
        {'op': 'set', 'tag': wp, 'field': 'Struct:weapon aim assist[0]/magnetism range', 'value': str(CE['magnetism_range'])},
        {'op': 'set', 'tag': wp, 'field': 'flags', 'value': 'weapon uses old dual fire error code'},
        {'op': 'set', 'tag': wp, 'field': 'Struct:item[0]/pickup message', 'value': STRINGS['pickup']},
        {'op': 'set', 'tag': wp, 'field': 'Struct:item[0]/swap message', 'value': STRINGS['swap']},
        {'op': 'set', 'tag': wp, 'field': 'Struct:item[0]/pickup message (dual)', 'value': STRINGS['dual']},
        {'op': 'set', 'tag': wp, 'field': 'Struct:item[0]/swap message (dual)', 'value': STRINGS['dual_swap']},
    ]
    print(kit.edit(ops, 'ce_objects'))
    for t in (de, pr, md, wp):
        kit.dump(t, W / ('final-' + t.split('\\')[-1] + '.txt'))


if __name__ == '__main__':
    if sys.argv[1] == 'objects': objects(); raise SystemExit(0)
    stage = sys.argv[1]
    if stage == 'shaders': shaders()
    elif stage == 'jms3p': jms('3p', *(sys.argv[2:3]))
    elif stage == 'jmsfp': jms('fp', *(sys.argv[2:3]))
    elif stage == 'render': render()
    else: raise SystemExit('unknown stage')
