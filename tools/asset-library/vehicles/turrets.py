"""Reach Falcon / Revenant vehicle turrets -> H3 turret vehicles (child objects of the parent vehicle model variant,
the stock H3 pattern used by the Warthog chaingun, Scorpion cannon and Wraith mortar).

Usage: python turrets.py <turret> <stage>      turret: chin | side_l | side_r | mortar | all
  shaders   new H3 shader copies needed by the turrets (stock H3 donors, Reach bitmaps)
  own       Foundry scene (Reach turret .model) -> H3 render/collision/physics JMS on the Reach turret skeleton
  compile   tool render (draft) / collision / physics
  anims     H3 aim grids composed from the original Reach 360 animation frames (turret_aim.py) + tool model-animations
  objects   .model / .vehicle / .weapon / .projectile / .damage_effect from stock H3 donors + Reach values
Run with OPENH3M_ASSET_KIT=.local/asset-kit-h3-veh (private exe folder; tags are the shared kit).
"""
import json, re, sys
from pathlib import Path
from PIL import Image
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import kit, blender_env
from build import wp, BS, param_index

FAL = wp('objects', 'vehicles', 'reach_falcon'); REV = wp('objects', 'vehicles', 'reach_revenant')
TW = kit.WORK / 'turrets'
MG = {k: 'reach_falcon_mg' for k in ('machinegun_turret_composite', 'machinegun_turret_metal', 'machinegun_turret_rubber',
                                      'machinegun_turret_shiny', 'falcon_machinegun_mounted_l_heat', 'falcon_machinegun_mounted_r_heat')}
REV_DMG = {k: 'reach_revenant_damage' for k in ('cov_damage_charred_hole_01', 'cov_damage_charred_hole_02', 'cov_damage_ripped_hex_cage_01',
                                                 'cov_damage_ripped_open_tech_02', 'cov_damage_ripped_open_tech_03', 'hum_damage_streak')}
T = {
 'chin': dict(src='falcon_chin_gun', root=wp(FAL, 'turrets', 'falcon_chin_gun'), name='falcon_chin_gun', parent=FAL,
              render_regions=['default:default', 'default:destroyed'], material_map={'falcon_hull_1': 'reach_falcon_hull_1'},
              collision_material={'default': 'chin_gun'}, physics_material='hard_metal_thick_hum_hornet', physics_region='default'),
 'side_l': dict(src='falcon_side_gun_left', root=wp(FAL, 'turrets', 'falcon_side_gun_left'), name='falcon_side_gun_left', parent=FAL,
                render_regions=['default:default'], material_map=dict(MG, falcon_hull_2='reach_falcon_hull_2'),
                collision_material={'default': 'side_gun'}, physics_material='hard_metal_thick_hum_hornet', physics_region='default'),
 'side_r': dict(src='falcon_side_gun_right', root=wp(FAL, 'turrets', 'falcon_side_gun_right'), name='falcon_side_gun_right', parent=FAL,
                render_regions=['default:default'], material_map=dict(MG, falcon_hull_2='reach_falcon_hull_2'),
                collision_material={'default': 'side_gun'}, physics_material='hard_metal_thick_hum_hornet', physics_region='default'),
 'mortar': dict(src='revenant_plasma_turret', root=wp(REV, 'turrets', 'revenant_plasma_turret'), name='revenant_plasma_turret', parent=REV,
                render_regions=['default:default', 'default:major', 'interior:default'],  # Reach 'med_decals' (hidden-by-default decal overlay) left out, as on the Revenant
                material_map=dict(REV_DMG, revenant_metal='reach_revenant_metal', revenant_shell='reach_revenant_shell', revenant_matte='reach_revenant_metal',
                                  revenant_illum='reach_revenant_illum', covenant_decals01='reach_revenant_decals', covenant_decals01_variant='reach_revenant_decals'),
                collision_material={'default': 'turret', 'interior': 'turret'}, physics_material='hard_metal_thick_cov_ghost', physics_region='default'),
}
# new shaders: (folder root, name, stock donor shader, {param: bitmap tag})
SHADERS = [
    (FAL, 'reach_falcon_mg', wp('objects', 'weapons', 'turret', 'machinegun_turret', 'shaders', 'chaingun.shader'),
     {'base_map': wp(FAL, 'bitmaps', 'reach_falcon_mg_diffuse.bitmap'), 'bump_map': wp(FAL, 'bitmaps', 'reach_falcon_mg_normal.bitmap')}),
    # unchanged copies of the stock H3 damage shaders (the kit only looks in the model's own shader collection);
    # used for Reach's damage-only materials (charred holes, ripped panels, streaks) in damaged/destroyed permutations
    (FAL, 'reach_falcon_damage', wp('objects', 'vehicles', 'hornet', 'shaders', 'hornet_damage.shader'), {}),
    (FAL, 'reach_falcon_glass_damage', wp('objects', 'vehicles', 'hornet', 'shaders', 'hornet_glass_damage.shader'), {}),
    (REV, 'reach_revenant_damage', wp('objects', 'vehicles', 'ghost', 'shaders', 'ghost_damage.shader'), {}),
]


def shaders(_):
    data = kit.DATA / FAL / 'bitmaps'; tga = TW / 'tga'
    Image.open(tga / 'mg_turret_diffusemg_turret_diffuse_00_00.tga').convert('RGBA').save(data / 'reach_falcon_mg_diffuse.tif', compression='tiff_lzw')
    a = np.asarray(Image.open(tga / 'mg_turret_zbumpmg_turret_zbump_00_00.tga').convert('RGB')).astype(np.float32) / 127.5 - 1.0
    a[..., 2] = np.sqrt(np.clip(1.0 - a[..., 0] ** 2 - a[..., 1] ** 2, 0, 1))  # Reach two-channel normal -> RGB
    Image.fromarray(np.clip((a + 1.0) * 127.5 + 0.5, 0, 255).astype(np.uint8)).save(data / 'reach_falcon_mg_normal.tif', compression='tiff_lzw')
    for n in ('reach_falcon_mg_diffuse', 'reach_falcon_mg_normal'):
        rc, out = kit.htool('bitmap_single', wp(FAL, 'bitmaps', n + '.tif'), log=TW / (n + '.log')); print(n, rc, out.strip()[-160:])
    tag = wp(FAL, 'bitmaps', 'reach_falcon_mg_normal.bitmap')
    kit.htool('patch-tag-field', tag, 'bitmap_block_struct[0].Usage', 'ZBrush Bump Map (from Bump Map)', log=TW / 'mg-normal-patch.log')
    rc, out = kit.htool('bitmap_single', wp(FAL, 'bitmaps', 'reach_falcon_mg_normal.tif'), log=TW / 'mg-normal-reimport.log'); print('normal', rc, out.strip()[-160:])
    ops = []
    for root, name, donor, params in SHADERS:
        dump = kit.dump(donor); tag = wp(root, 'shaders', name + '.shader')
        ops.append({'op': 'copy', 'from': donor, 'to': tag, 'overwrite': True})
        for pn, bmp in params.items():
            ops.append({'op': 'set', 'tag': tag, 'field': 'Struct:render_method[0]/Block:parameters[%d]/bitmap' % param_index(dump, pn), 'value': bmp})
    print(kit.edit(ops, 'turret_shaders'))


def own(t):
    c = T[t]; w = TW / c['src']
    cfg = dict(name=c['name'], out_dir=str(kit.DATA / c['root']), out_blend=str(w / (c['name'] + '-own.blend')),
               render_regions=c['render_regions'], material_map=c['material_map'], collision_material=c['collision_material'],
               physics_material=c['physics_material'], physics_region=c['physics_region'], seal_collision=True, animations=[], lift_aims=[])
    cp = w / 'own.json'; cp.write_text(json.dumps(cfg, indent=1))
    rc, out = blender_env.run(HERE.parent / 'build_vehicle_own.py', cp, blend=w / 'source.blend', log=w / 'own.log', timeout=1800)
    print('\n'.join(l for l in out.splitlines() if l.startswith(('RENDER', 'EXPORTED', 'SEAL', 'Error', 'Traceback', '  File', 'SystemExit', 'KeyError'))))
    if rc: print(out[-2500:]); raise SystemExit(rc)


def compile_(t):
    c = T[t]; w = TW / c['src']
    for verb in ('render', 'collision', 'physics'):
        if not (kit.DATA / c['root'] / verb).exists(): print(verb, 'no source'); continue
        args = (verb, c['root'], 'draft') if verb == 'render' else (verb, c['root'])
        rc, out = kit.htool(*args, log=w / ('compile-%s.log' % verb), timeout=1800)
        keep = [l.strip() for l in out.replace(chr(13), chr(10)).splitlines() if re.search(r'ERROR|triangles|WARNING|shader', l) and 'leaking' not in l]
        print(verb, 'rc', rc, *keep[:14], sep='\n  ')


if __name__ == '__main__':
    ts = list(T) if sys.argv[1] == 'all' else [sys.argv[1]]
    for t in ts:
        print('==', t)
        {'shaders': shaders, 'own': own, 'compile': compile_}[sys.argv[2]](t)
        if sys.argv[2] == 'shaders': break
