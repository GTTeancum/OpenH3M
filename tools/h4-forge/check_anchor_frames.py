"""Check reviewed anchors against measured Reach construction planes."""
import json,math
from pathlib import Path
from anchor_frames import adapt
ROOT=Path(__file__).resolve().parents[2]
frames=json.loads((Path(__file__).parent/'anchor_frames.json').read_text())
models={m['name'].split('\\')[-1]:m for m in json.loads((ROOT/'work/h4-forge-research/ravine-magnets.json').read_text())['data']}
def mapped(name):
 return [adapt(p,frames[name]) for g in models[name]['markers'] for p in g['points']]
bank=mapped('fw_unsc_c_bank_2x1')
expected=[(-1,0,-.5),(0,.5,-.5),(-1,.5,-.5)]
for p,target in zip(bank,expected):
 assert math.dist(p['position'],target)<1e-5,(p,target)
for p in bank:
 assert abs(sum(v*v for v in p['rotation'])-1)<1e-5
# The Y-side anchor must face outward toward -Y after mirroring.
x,y,z,w=bank[0]['rotation'];forward=(1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w))
assert math.dist(forward,(0,-1,0))<1e-5,forward
dish=mapped('fw_unsc_c_dish')
assert abs(dish[0]['position'][1])<1e-6
assert abs(dish[0]['position'][2]+1.4)<1e-6
# Front-face normal rotates from -X to +Y on the negative-Y half-disc.
x,y,z,w=dish[0]['rotation'];forward=(1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w))
assert math.dist(forward,(0,1,0))<1e-5,forward
print('PASS measured Reach bank planes, mirrored outward normal, Dish front/base planes and normal')

# A stale or ambiguous full-position role must fail closed rather than silently
# attaching a new model revision to the nearest reviewed entrance.
import copy
tower=frames['fw_unsc_c_tower']
source=next(p for g in models['fw_unsc_c_tower']['markers'] if g['group']=='sandbox_magnet' for p in g['points'])
for failure in ('moved_source','duplicate_role','nonfinite_target','mixed_mapping'):
    frame=copy.deepcopy(tower);point=copy.deepcopy(source)
    if failure=='moved_source':
        point['position']=list(point['position']);point['position'][0]+=.0002
    elif failure=='duplicate_role':frame['position_levels']['levels'].append(copy.deepcopy(frame['position_levels']['levels'][0]))
    elif failure=='nonfinite_target':frame['position_levels']['levels'][0]['target'][0]=float('nan')
    else:frame['axis_levels']=[]
    try:adapt(point,frame)
    except ValueError:pass
    else:raise AssertionError('Invalid full-position role accepted: '+failure)
print('PASS stale, ambiguous, nonfinite and mixed full-position roles are rejected')

# Independent render bounds corroborate the large origin changes. Collision
# vertices include Havok skin and must not be used as the construction plane.
bounds=json.loads((ROOT/'work/h4-forge-research/isolated/binding-bounds.json').read_text())
for label,name in [('Crenel Notch','fw_unsc_c_crenel_notch'),
                   ('Bunker Covered','fw_unsc_c_bunker_covered')]:
 for row in (r for r in bounds if r['label']==label):
  source,target=row['h4_bounds'],row['h3_bounds']
  # Bounds are geometry, not authored marker roles. Only the affine frame
  # applies here; marker-level plane cleanup must reject these fake corners.
  geometry_frame={k:v for k,v in frames[name].items() if k not in ('coordinate_planes','coordinate_tolerance','axis_levels','upright_yaw_levels')}
  corners=[adapt(dict(position=[x,y,z],rotation=[0,0,0,1]),geometry_frame)['position']
           for x in source[:2] for y in source[2:4] for z in source[4:6]]
  extent=[v for axis in range(3) for v in (min(p[axis] for p in corners),max(p[axis] for p in corners))]
  assert abs(extent[4]-target[4])<1e-5,(label,'base',extent,target)
  for point in mapped(name):
   assert abs(sum(v*v for v in point['rotation'])-1)<1e-5
print('PASS Crenel/Bunker base origins on both map palettes; Arch Brace uses construction ledges, checked by verify_scenery_math.py')

base=mapped('fw_unsc_c_base_round')
for i in (0,3,4):
 p=base[i]
 assert abs(p['position'][1])<1e-4,p
 assert abs(p['position'][2])<2e-6,p
 x,y,z,w=p['rotation']
 forward=(1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w))
 assert math.dist(forward,(0,1,0))<1e-5,forward
# Independent target bounds: diameter 11, rear edge -5.5, base -1.
for row in (r for r in bounds if r['label']=='Base Round'):
 assert abs(abs(base[8]['position'][0])-row['h3_bounds'][1])<1e-5
 assert abs(abs(base[9]['position'][0])-row['h3_bounds'][1])<1e-5
 assert abs(base[2]['position'][1]-row['h3_bounds'][2])<1e-5
 assert abs(row['h4_bounds'][4]+frames['fw_unsc_c_base_round']['translation'][2]-row['h3_bounds'][4])<1e-5
print('PASS Base Round flat-face plane/normals, radius and base origin on both map palettes')
