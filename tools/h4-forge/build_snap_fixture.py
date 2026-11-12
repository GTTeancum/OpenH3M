"""Small native H3 saved layout for the process-local two-piece magnet check."""
import argparse
import hashlib
import copy
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from h3_saved_layout import write

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bank',choices=['1x1','2x1','dish','dish-door','arch','base-round'],default='1x1')
parser.add_argument('--overlap',action='store_true',help='Same-facing offset banks for collision/release checks')
parser.add_argument('--native-flow',action='store_true',help='Place target at the measured ordinary-input 1x1 joint; no runtime forced pose')
parser.add_argument('--existing-pair',action='store_true',help='Two opposed Base Round halves for native grab/detach/regrab, without creation')
parser.add_argument('--single-near',action='store_true',help='Existing-pair control: retain only the near piece, with the same spawn and pose')
parser.add_argument('--same-facing',action='store_true',help='Existing-pair penetration diagnostic: give both halves the near-piece orientation')
parser.add_argument('--elevate',type=float,default=0.,help='Raise saved scenery to isolate terrain contact; player spawns remain grounded')
args=parser.parse_args()
if not 0. <= args.elevate <= 30.:
    parser.error('Diagnostic elevation must be between 0 and 30 world units')
if args.single_near and not args.existing_pair:
    parser.error('Single near requires the existing-pair fixture')
if args.same_facing and (not args.existing_pair or args.single_near):
    parser.error('Same facing requires both existing pieces')
if args.existing_pair and (args.bank!='base-round' or args.overlap or args.native_flow):
    parser.error('Existing pair requires Base Round without other fixture modes')
if args.overlap and args.bank not in ('1x1','2x1'):
    parser.error('Overlap fixture supports the single-polyhedron Bank pieces')
palette_index={'1x1':4,'2x1':6,'dish':36,'dish-door':37,'arch':2,'base-round':8}[args.bank]
source = ROOT/'work/forge-world/variants/layouts/hemorrhage.json'
report = json.loads(source.read_text())
map_path = next((ROOT/'work/dlc/installed-current').rglob('forge_gulch.map'))
if hashlib.sha256(map_path.read_bytes()).hexdigest() != report['map_sha256']:
    raise ValueError('Fixture base differs from verified layout base')
c = Cache(map_path)
try:
    scenario = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    row = list(c.block(scenario+0x20c, 48))[palette_index]
    datum = c.u(row+12)
    if datum != {'1x1':0x90002937,'2x1':0x90002948,'dish':0x900029fc,'dish-door':0x90002a01,'arch':0x9000291b,'base-round':0x90002952}[args.bank]:
        raise ValueError('Bank palette changed; inspect the current binding')
    tag = c.tags[datum & 65535]
    props = list(c.block(tag['offset']+0xec, 196))
    kind = c.data[props[0]+2]
finally:
    c.close()
layout = report['layout']
spawns=[]
for i,q in enumerate(layout['quotas']):
    if q.get('name','').endswith(('slayer_initial_spawn_point','spawning\\respawn_point')):
        obj=copy.deepcopy(next(o for o in layout['objects'] if o['quota']==i))
        quota=copy.deepcopy(q)
        obj.update(position=[-49.56380081176758,-195.6840057373047,1.4517199993133545],
                   forward=[1.,0.,0.],up=[0.,0.,1.])
        if args.bank=='base-round':
            obj['forward']=[0.,1.,0.]
            # Offset the approach from the central doorway so native selection
            # hits the solid curved wall, not a spawning marker behind it.
            if args.existing_pair:obj['position']=[-49.0694468,-202.0296933,2.5]
        quota['count']=1
        spawns.append((obj,quota))
if len(spawns)!=2:
    raise ValueError('Verified initial/respawn records missing')
layout.update(name='Magnet Check', description='Private original H4 magnet diagnostic.',
              unique_id=0x4846344d41474e31, spent_budget=4.)
# Measured held pose from the exclusive replay with explicit player spawns.
# Oppose triangular banks across their diagonal markers. Same-facing banks
# connected center-to-edge overlap and separate under native H3 physics.
# Original H4 marker 0 is (-.501512706, .501440883, -.502214313).
# Rotate the target 180 degrees; leave a measured .1-unit initial Y gap.
target=[-45.79547917842865, -196.83774628639222, 2.5829529762268066] if args.bank=='1x1' else [-46.79245376586914,-196.84062805175782,2.5829529762268066]
if args.bank in ('dish','dish-door'):target=[-44.79245376586914,-197.84062805175782,3.8]
# Opposed Arch Brace end anchors at nominal local X=2.9, Y=0.
# Keep the same 0.1-unit initial gap so H4 must select and close the joint.
if args.bank=='arch':target=[-38.9924538,-197.8406281,2.582953]
if args.bank=='base-round':
    target=[-51.5694467806461,-190.02969331161876,1.4892260808555875]
    if args.existing_pair:
        # The target's verified model minimum is local Z=-1, not zero.
        # The old ground-level origin buried that lower metre in terrain and
        # confounded magnet detachment with initial contact penetration.
        # Keep a further metre of clearance for this uneven-ground fixture.
        target[2]+=2.
if args.native_flow:
    if args.bank!='1x1' or args.overlap:
        parser.error('Native-flow joint currently supports the opposed 1x1 pieces')
    # Measured unobstructed native creation position from run
    # 20261112-100551-9684. Existing opposed diagonal anchor separation,
    # with a 0.1-unit gap. Only the saved target is positioned here.
    target=[-44.81729-1.00302541255951, -195.62943+1.1028817653656, 2.6332347]
if args.overlap:
    target=[-44.5424538,-197.9406281,2.582953]
    layout.update(name='Overlap Check',description='Private overlapping scenery physics diagnostic.')
layout['objects'] = [dict(quota=0, position=target,
                         forward=[1. if args.overlap else -1.,0.,0.], up=[0.,0.,1.], engine_flags=1023,
                         mp_flags=0, team=8, shared_storage=0, spawn_time=0,
                         object_type=kind, shape=0, boundary=[0.,0.,0.,0.])]
layout['quotas'] = [dict(datum=datum, count=1, maximum=100, price=4.)]
if args.existing_pair:
    near=copy.deepcopy(layout['objects'][0])
    near['forward']=[1.,0.,0.]
    near['position']=[target[0],target[1]-.1,target[2]]
    layout['objects'].append(near)
    layout['quotas'][0]['count']=2
    layout['spent_budget']=8.
    if args.same_facing:
        layout['objects'][0]['forward']=[1.,0.,0.]
        layout['description']='Private initially overlapping same-facing physics diagnostic.'
    if args.single_near:
        layout['objects']=[near]
        layout['quotas'][0]['count']=1
        layout['spent_budget']=4.

if args.elevate:
    for obj in layout['objects']:
        obj['position'][2]+=args.elevate
for obj,quota in spawns:
    obj['quota']=len(layout['quotas'])
    layout['objects'].append(obj)
    layout['quotas'].append(quota)
out = ROOT/'work/h4-forge-research/isolated'/('snap-fixture.bin' if args.bank=='1x1' else 'snap-fixture-'+args.bank+'.bin')
if args.existing_pair:out=out.with_name('snap-fixture-base-round-pair.bin')
if args.single_near:out=out.with_name('snap-fixture-base-round-solo.bin')
if args.same_facing:out=out.with_name('snap-fixture-base-round-same-facing.bin')
if args.overlap:out=out.with_name('overlap-fixture-'+args.bank+'.bin')
data = write(layout)
out.write_bytes(data)
out.with_suffix('.json').write_text(json.dumps(dict(layout=layout,
    map_sha256=report['map_sha256'], sha256=hashlib.sha256(data).hexdigest()), indent=2)+'\n')
print(f'{out}: {len(data)} bytes; ' + ('initially overlapping same-facing Base Round pair' if args.same_facing else 'single near Base Round control' if args.single_near else 'two existing opposed Base Round pieces for native grab replay' if args.existing_pair else f'target {args.bank} piece; replay creates its counterpart'))
