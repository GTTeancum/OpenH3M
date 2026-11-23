"""Reach Falcon / Revenant -> H3 tags, staged. Usage: python build.py <falcon|revenant> <stage>

  bitmaps   Reach textures (official HREK export-bitmap-tga) -> TIFF at H3 donor-class sizes -> H3 tool bitmaps;
            normal maps re-imported as normal maps (tool patch-tag-field + bitmap_single)
  shaders   stock H3 donor shaders copied to new names, Reach bitmaps swapped in (ManagedBlam)
  jms       Foundry scene -> H3 render/collision/physics JMS on the exact stock donor skeleton
  compile   tool render (draft) / collision / physics; compare compiled nodes with the donor
  objects   donor .model/.vehicle copied, pointed at the new render/collision/physics models
"""
import json, re, sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import kit, blender_env

BS = chr(92)
def wp(*p): return BS.join(p)
P = 'Struct:render_method[0]/'
HORNET = wp('objects', 'vehicles', 'hornet'); GHOST = wp('objects', 'vehicles', 'ghost')

V = {
 'falcon': dict(
    root=wp('objects', 'vehicles', 'reach_falcon'), name='reach_falcon', donor=HORNET, donor_name='hornet',
    work=kit.WORK / 'reach_falcon',
    textures=[  # tga stem, output tif, size, normal?
        ('falcon1_diffusefalcon1_diffuse', 'reach_falcon1_diffuse', 512, False),
        ('falcon1_normalfalcon1_normal', 'reach_falcon1_normal', 512, True),
        ('falcon2_diffusefalcon2_diffuse', 'reach_falcon2_diffuse', 512, False),
        ('falcon2_normalfalcon2_normal', 'reach_falcon2_normal', 512, True),
        ('falcon_screenfalcon_screen', 'reach_falcon_screen', None, False),
        ('falcon_decalsfalcon_decals', 'reach_falcon_decals', None, False),
        ('cargo_netting_tiled_diffcargo_netting_tiled_diff', 'reach_falcon_netting', None, False)],
    shaders=[  # name, donor shader, option changes, {param: bitmap stem}
        ('reach_falcon_hull_1', 'hornet_metal', {}, {'base_map': 'reach_falcon1_diffuse', 'bump_map': 'reach_falcon1_normal'}),
        ('reach_falcon_hull_2', 'hornet_metal', {}, {'base_map': 'reach_falcon2_diffuse', 'bump_map': 'reach_falcon2_normal'}),
        ('reach_falcon_glass', 'hornet_glass', {}, {}),
        ('reach_falcon_decals', 'hornet_blur', {}, {'base_map': 'reach_falcon_decals'}),
        ('reach_falcon_netting', 'hornet_blur', {}, {'base_map': 'reach_falcon_netting'}),
        ('reach_falcon_illum', 'hornet_thrust', {}, {'self_illum_map': 'reach_falcon_screen'})],
    material_map={'falcon_hull_1': 'reach_falcon_hull_1', 'falcon_hull_2': 'reach_falcon_hull_2', 'falcon_blades': 'reach_falcon_hull_1',
                  'falcon_illum_spotlight': 'reach_falcon_hull_1', 'falcon_glass': 'reach_falcon_glass', 'sabre_glass_opaque': 'reach_falcon_glass',
                  'falcon_decals': 'reach_falcon_decals', 'unsc_decals': 'reach_falcon_decals', 'falcon_cargo_netting': 'reach_falcon_netting',
                  'falcon_illum': 'reach_falcon_illum', 'falcon_console': 'reach_falcon_illum', 'falcon_illum_thruster': 'reach_falcon_illum',
                  'falcon_illum_green': 'reach_falcon_illum', 'falcon_illum_red': 'reach_falcon_illum',
                  # damage permutations: Reach damaged hull shaders -> the hull shaders; damage-only materials -> stock hornet damage shader copy
                  'falcon_hull_1_damaged': 'reach_falcon_hull_1', 'falcon_hull_2_damaged': 'reach_falcon_hull_2', 'falcon_glass_damage': 'reach_falcon_glass_damage',
                  'falcon_engine': 'reach_falcon_damage', 'cov_damage_charred_hole_01': 'reach_falcon_damage', 'cov_damage_charred_hole_02': 'reach_falcon_damage',
                  'cov_damage_charred_hole_02_noparalax': 'reach_falcon_damage', 'hum_damage_ripped_open_tech_03': 'reach_falcon_damage',
                  'hum_damage_streak': 'reach_falcon_damage'},
    bone_map={'b_pedestal': 'hornet', 'b_aim_yaw': 'hornet', 'b_aim_pitch': 'hornet', 'b_hull': 'hull', 'b_seat_right_front': 'hull',
              'b_seat_left_front': 'hull', 'b_seat_right_rear': 'hull', 'b_seat_left_rear': 'hull', 'b_seat_middle': 'hull',
              'b_rapel_left': 'hull', 'b_rapel_right': 'hull', 'b_landing_gear': 'hull', 'b_landing_skid_left': 'hull',
              'b_landing_skid_right': 'hull', 'b_controls': 'hull', 'b_yoke': 'hull', 'b_canopy1': 'hull', 'b_canopy2': 'hull',
              'b_engine_left': 'thrust_l', 'b_engine_right': 'thrust_r', 'b_blades_left': 'rotor_l', 'b_blades_right': 'rotor_r'},
    pivot_bones={'b_blades_left': 'rotor_l', 'b_blades_right': 'rotor_r'},
    collision_skip_bones=['b_blades_left', 'b_blades_right'],  # flat rotor-blade outlines cannot form closed H3 collision shells
    pivot_follow={'b_engine_left': 'b_blades_left', 'b_engine_right': 'b_blades_right'},
    # default + Reach damaged ('major') and destroyed permutations (switched by the model's damage states)
    render_regions=['canopy:default', 'hull:default', 'interior:default', 'props:default', 'tail:default', 'wing_left:default', 'wing_right:default',
                    'canopy:major', 'hull:major', 'hull:destroyed', 'tail:major', 'wing_left:major', 'wing_right:major'],
    # own collision material names (= Reach materials), mapped to the Reach damage sections in damage_setup.py
    collision_material={'canopy': 'canopy', 'hull': 'hull', 'tail': 'tail', 'wing_left': 'wing_left', 'wing_right': 'wing_right'},
    physics_material='hard_metal_thick_hum_hornet',  # stock global material (hornet physics model)
    markers={'hornet_d': {'from_object': 'falcon_d'}, 'hornet_d_enter': {'from_object': 'falcon_d_enter'},
             'hornet_b_d_l': {'from_object': 'falcon_b_d_l'}, 'hornet_b_d_l_enter': {'from_object': 'falcon_b_d_l_enter'},
             'hornet_b_d_r': {'from_object': 'falcon_b_d_r'}, 'hornet_b_d_r_enter': {'from_object': 'falcon_b_d_r_enter'},
             'hornet_b_d_enter': {'from_object': 'falcon_d_enter'},
             'hornet_p_l': {'from_object': 'falcon_p_l1'}, 'hornet_p_l_enter': {'from_object': 'falcon_p_l1_enter'},
             'hornet_p_l_camera': {'from_object': 'falcon_p_l1_camera'},
             'hornet_p_r': {'from_object': 'falcon_p_r1'}, 'hornet_p_r_enter': {'from_object': 'falcon_p_r1_enter'},
             'hornet_p_r_camera': {'from_object': 'falcon_p_r1_camera'},
             'primary_trigger': {'from_object': 'turret'}, 'thrust': {'from_object': 'thrust'}, 'turret': {'from_object': 'turret'},
             'left_hand': {'from_object': 'd_left_hand'}, 'right_hand': {'from_object': 'd_right_hand'}},
 ),
 'revenant': dict(
    root=wp('objects', 'vehicles', 'reach_revenant'), name='reach_revenant', donor=GHOST, donor_name='ghost',
    work=kit.WORK / 'reach_revenant',
    textures=[('revenant_diffuserevenant_diffuse', 'reach_revenant_diffuse', 512, False),
              ('revenant_normalrevenant_normal', 'reach_revenant_normal', 768, True),
              ('revenant_illumrevenant_illum', 'reach_revenant_illum', None, False),
              ('covenant_decals01covenant_decals01', 'reach_revenant_decals', None, False)],
    shaders=[('reach_revenant_shell', 'ghost_shell', {}, {'base_map': 'reach_revenant_diffuse', 'bump_map': 'reach_revenant_normal', 'self_illum_map': 'reach_revenant_illum'}),
             ('reach_revenant_metal', 'ghost_metal', {}, {'base_map': 'reach_revenant_diffuse', 'bump_map': 'reach_revenant_normal', 'self_illum_map': 'reach_revenant_illum'}),
             ('reach_revenant_glass', wp('..', '..', 'hornet', 'shaders', 'hornet_glass'), {}, {}),
             ('reach_revenant_illum', 'plasma_vent', {}, {}),
             ('reach_revenant_decals', wp('..', '..', 'hornet', 'shaders', 'hornet_blur'), {}, {'base_map': 'reach_revenant_decals'})],
    halograms=[('revenant_zcam', 'ghost_dash_zcam')],
    material_map={'revenant_shell': 'reach_revenant_shell', 'revenant_seat_shell': 'reach_revenant_shell', 'revenant_metal': 'reach_revenant_metal',
                  'revenant_matte': 'reach_revenant_metal', 'revenant_glass': 'reach_revenant_glass', 'revenant_illum': 'reach_revenant_illum',
                  'covenant_decals01': 'reach_revenant_decals', 'covenant_decals01_variant': 'reach_revenant_decals', 'revenant_zcam': 'revenant_zcam',
                  **{k: 'reach_revenant_damage' for k in ('cov_damage_charred_hole_01', 'cov_damage_charred_hole_02', 'cov_damage_ripped_hex_cage_01',
                     'cov_damage_ripped_open_tech_01', 'cov_damage_ripped_open_tech_02', 'cov_damage_ripped_open_tech_03', 'hum_damage_streak')}},
    bone_map={'b_pedestal': 'hull', 'b_aim_yaw': 'hull', 'b_aim_pitch': 'hull', 'b_chassis': 'hull', 'b_seats': 'hull',
              'b_wing_left': 'left_flap', 'b_wing_right': 'right_flap', 'b_steering': 'hull'},
    pivot_bones={},
    pivot_follow={},
    render_regions=['back_left:default', 'back_right:default', 'front_left:default', 'front_right:default', 'hull:default', 'interior:default',
                    'back_left:major', 'back_right:major', 'front_left:medium', 'front_left:major', 'front_right:medium', 'front_right:major',
                    'hull:major', 'hull:destroyed'],
    collision_material={'back_left': 'back_left', 'back_right': 'back_right', 'front_left': 'front_left', 'front_right': 'front_right', 'hull': 'hull'},
    physics_material='hard_metal_thick_cov_ghost',  # stock global material (ghost physics model)
    markers={'driver': {'from_object': 'revenant_d'}, 'driver_enter': {'from_object': 'revenant_d_enter'},
             'driver_brute': {'from_object': 'revenant_b_d'}, 'camera_driver': {'from_object': 'revenant_d_camera'},
             'passenger': {'from_object': 'revenant_p', 'node': 'seat'}, 'passenger_enter': {'from_object': 'revenant_p_enter', 'node': 'seat'},
             'passenger_camera': {'from_object': 'revenant_p_camera', 'node': 'seat'}, 'primary_trigger': {'from_object': 'turret'},
             'engine': {'from_object': 'engine'}},
 ),
}


def bitmaps(v):
    c = V[v]; data = kit.DATA / c['root'] / 'bitmaps'; data.mkdir(parents=True, exist_ok=True); tga = c['work'] / 'tga'
    for stem, out, size, normal in c['textures']:
        im = Image.open(tga / (stem + '_00_00.tga'))
        if size: im = im.resize((size, int(size * im.size[1] / im.size[0])), Image.LANCZOS)
        if normal:
            a = np.asarray(im.convert('RGB')).astype(np.float32) / 127.5 - 1.0
            a[..., 2] = np.sqrt(np.clip(1.0 - a[..., 0] ** 2 - a[..., 1] ** 2, 0, 1))
            im = Image.fromarray(np.clip((a + 1.0) * 127.5 + 0.5, 0, 255).astype(np.uint8))
        im.save(data / (out + '.tif'), compression='tiff_lzw')
    rc, out = kit.htool('bitmaps', wp(c['root'], 'bitmaps'), log=c['work'] / 'bitmaps.log', timeout=900)
    print('bitmaps rc', rc, re.findall(r"imported as '([^']+)' \(in-game size: (\d+)", out))
    for stem, outn, size, normal in c['textures']:
        if not normal: continue
        tag = wp(c['root'], 'bitmaps', outn + '.bitmap')
        kit.htool('patch-tag-field', tag, 'bitmap_block_struct[0].Usage', 'ZBrush Bump Map (from Bump Map)', log=c['work'] / (outn + '-patch.log'))
        rc, out = kit.htool('bitmap_single', wp(c['root'], 'bitmaps', outn + '.tif'), log=c['work'] / (outn + '-reimport.log'))
        print('normal', outn, rc, out.strip()[-120:])


def param_index(dump, name):
    for l in Path(dump).read_text().splitlines():
        if l.startswith(P + 'Block:parameters[') and '/parameter name\t' in l and l.endswith('\t' + name):
            return int(l.split('Block:parameters[')[1].split(']')[0])
    raise KeyError(name)


def shaders(v):
    c = V[v]; ops = []
    for name, donor, opts, params in c['shaders']:
        src = BS.join(_norm(wp(c['donor'], 'shaders', donor + '.shader').split(BS)))
        dump = kit.dump(src)
        tag = wp(c['root'], 'shaders', name + '.shader')
        ops.append({'op': 'copy', 'from': src, 'to': tag})
        for i, val in opts.items(): ops.append({'op': 'set', 'tag': tag, 'field': P + 'Block:options[%d]/short' % i, 'value': str(val)})
        for pn, bmp in params.items():
            ops.append({'op': 'set', 'tag': tag, 'field': P + 'Block:parameters[%d]/bitmap' % param_index(dump, pn),
                        'value': wp(c['root'], 'bitmaps', bmp + '.bitmap')})
    for name, donor in c.get('halograms', []):
        ops.append({'op': 'copy', 'from': wp(c['donor'], 'shaders', donor + '.shader_halogram'), 'to': wp(c['root'], 'shaders', name + '.shader_halogram')})
    print(kit.edit(ops, v + '_shaders'))


def _norm(parts):
    out = []
    for p in parts:
        if p == '..': out.pop()
        else: out.append(p)
    return out


def jms(v):
    c = V[v]
    donor = kit.to_xml(wp(c['donor'], c['donor_name'] + '.render_model'), kit.WORK / 'donor-xml' / (c['donor_name'] + '.render_model.xml'))
    cfg = dict(donor_xml=str(donor), bone_map=c['bone_map'], pivot_bones=c['pivot_bones'], pivot_follow=c['pivot_follow'],
               render_regions=c['render_regions'], collision=True, physics=True, material_map=c['material_map'],
               collision_material=c['collision_material'], physics_material=c['physics_material'], markers=c['markers'],
               out_dir=str(kit.DATA / c['root']), name=c['name'], out_blend=str(c['work'] / (c['name'] + '-rigged.blend')))
    cp = c['work'] / 'rig.json'; cp.write_text(json.dumps(cfg, indent=1))
    rc, out = blender_env.run(HERE.parent / 'build_vehicle_jms.py', cp, blend=c['work'] / 'source.blend', log=c['work'] / 'rig.log', timeout=1800)
    print('\n'.join(l for l in out.splitlines() if l.startswith(('PIVOT', 'RENDER_PARTS', 'COLLISION', 'EXPORTED', 'Error', 'Traceback', '  File', 'SystemExit', 'KeyError', 'Assert'))))
    if rc: print(out[-2500:]); raise SystemExit(rc)


def compile_(v):
    c = V[v]
    for verb in ('render', 'collision', 'physics'):
        args = (verb, c['root'], 'draft') if verb == 'render' else (verb, c['root'])
        rc, out = kit.htool(*args, log=c['work'] / ('compile-%s.log' % verb), timeout=1800)
        keep = [l.strip() for l in out.replace(chr(13), chr(10)).splitlines() if re.search(r'ERROR|vertices, |triangles|regions|permutations|rigid|shape|WARNING', l) and 'leaking' not in l]
        print(verb, 'rc', rc, *keep[:14], sep='\n  ')


def objects(v):
    c = V[v]; r, n, d, dn = c['root'], c['name'], c['donor'], c['donor_name']
    md, vh = wp(r, n + '.model'), wp(r, n + '.vehicle')
    ops = [{'op': 'copy', 'from': wp(d, dn + '.model'), 'to': md},
           {'op': 'set', 'tag': md, 'field': 'render model', 'value': wp(r, n + '.render_model')},
           {'op': 'set', 'tag': md, 'field': 'collision model', 'value': wp(r, n + '.collision_model')},
           {'op': 'set', 'tag': md, 'field': 'physics_model', 'value': wp(r, n + '.physics_model')},
           {'op': 'clear', 'tag': md, 'block': 'Block:variants'},
           {'op': 'set', 'tag': md, 'field': 'lod_render_model', 'value': ''},
           {'op': 'copy', 'from': wp(d, dn + '.vehicle'), 'to': vh},
           {'op': 'set', 'tag': vh, 'field': 'Struct:unit[0]/Struct:object[0]/model', 'value': md}]
    print(kit.edit(ops, v + '_objects'))
    for t in (md, vh): kit.dump(t, c['work'] / ('final-' + t.split(BS)[-1] + '.txt'))


FW = kit.WORK / 'forge_world' / 'anims' / 'hornet'
ANIMS = {
 'falcon': dict(animations=[
    {'name': 'any idle', 'action': 'any idle', 'ext': 'JMM'},
    {'name': 'vehicle hover', 'action': 'vehicle hover', 'ext': 'JMM'},
    {'name': 'vehicle landing_gear', 'action': 'vehicle landing_gear', 'ext': 'JMM'},
    {'name': 'vehicle opening', 'action': 'vehicle open_close', 'ext': 'JMM'},
    {'name': 'vehicle closing', 'action': 'vehicle open_close', 'ext': 'JMM', 'reverse': True},
    {'name': 'vehicle rotate_props', 'action': 'vehicle rotate_props', 'ext': 'JMM'},
    {'name': 'vehicle steering', 'action': 'vehicle steering', 'ext': 'JMO'},
    {'name': 'vehicle throttle', 'action': 'vehicle throttle', 'ext': 'JMO'},
    {'name': 'vehicle slide_left', 'action': 'vehicle slide_left', 'ext': 'JMO'},
    {'name': 'vehicle slide_right', 'action': 'vehicle slide_right', 'ext': 'JMO'}],
  lift_aims=[  # stock H3 hornet engine-tilt overlays transferred onto the Falcon's own pivots (as the Forge World port does)
    {'name': 'any any l_lift_aim', 'source_jmo': str(FW / 'any any l_lift_aim.JMO'), 'map': {'engine_l': 'b_engine_left', 'thrust_l': 'b_blades_left'}},
    {'name': 'any any r_lift_aim', 'source_jmo': str(FW / 'any any r_lift_aim.JMO'), 'map': {'engine_r': 'b_engine_right', 'thrust_r': 'b_blades_right'}}]),
 'revenant': dict(animations=[
    {'name': 'any idle', 'action': 'any idle', 'ext': 'JMM'},
    {'name': 'vehicle steering', 'action': 'vehicle steering', 'ext': 'JMO'},
    {'name': 'vehicle acceleration', 'action': 'vehicle acceleration', 'ext': 'JMO'}], lift_aims=[]),
}


def own(v):
    c = V[v]
    cfg = dict(name=c['name'], out_dir=str(kit.DATA / c['root']), out_blend=str(c['work'] / (c['name'] + '-own.blend')),
               render_regions=c['render_regions'], material_map=c['material_map'], collision_material=c['collision_material'],
               physics_material=c['physics_material'], seal_collision=True, collision_skip_bones=c.get('collision_skip_bones', []), **ANIMS[v])
    cp = c['work'] / 'own.json'; cp.write_text(json.dumps(cfg, indent=1))
    rc, out = blender_env.run(HERE.parent / 'build_vehicle_own.py', cp, blend=c['work'] / 'source-anim.blend', log=c['work'] / 'own.log', timeout=1800)
    print(chr(10).join(l for l in out.splitlines() if l.startswith(('RENDER', 'EXPORTED', 'ANIM', 'DONE', 'Error', 'Traceback', '  File', 'SystemExit', 'KeyError', 'Assert'))))
    if rc: print(out[-2500:]); raise SystemExit(rc)


if __name__ == '__main__':
    v, stage = sys.argv[1], sys.argv[2]
    {'bitmaps': bitmaps, 'shaders': shaders, 'jms': jms, 'own': own, 'compile': compile_, 'objects': objects}[stage](v)
