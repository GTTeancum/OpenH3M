"""Extract a portable pose from the private, pointer-bearing guest snapshot."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('snapshot',type=Path)
parser.add_argument('--trace-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[5]
args.output.resolve().relative_to(repo)
snapshot=json.loads(args.snapshot.read_text())
blobs=snapshot['blobs']
def data(name): return bytes.fromhex(blobs[name]['bytes'])
def u(raw,offset): return struct.unpack_from('>I',raw,offset)[0]
def vec(raw,offset):
    value=list(struct.unpack_from('>3f',raw,offset))
    if not all(math.isfinite(x) for x in value): raise ValueError('Nonfinite pose')
    return value
def basis(forward,up):
    lengths=[math.sqrt(sum(v*v for v in row)) for row in (forward,up)]
    dot=sum(a*b for a,b in zip(forward,up))
    if max(abs(n-1) for n in lengths)>0.002 or abs(dot)>0.002:
        raise ValueError('Pose basis is not orthonormal')
    return {'lengths':lengths,'dot':dot}
observer_offset=snapshot.get('observer_result_offset',0x1cc)
observer=data('observer')[observer_offset:observer_offset+112]
# Accept the preserved older snapshot only when the two routes resolve to the
# same address; the proper allocation is TLS+0x2cc, result +0x110 for user 0.
native_observer=u(data('tls'),0x2cc)
if int(blobs['observer']['guest_address'],16)+observer_offset!=native_observer+0x110:
    raise ValueError('Saved result is not the native observer result')
camera={'position':vec(observer,0),'forward':vec(observer,0x28),'up':vec(observer,0x34),
        'horizontal_fov_radians':struct.unpack_from('>f',observer,0x40)[0],
        'observer_aspect_ratio':struct.unpack_from('>f',observer,0x58)[0],
        'location_bytes':observer[12:16].hex(),'raw_observer_result':observer.hex(),
        'native_layout':{'tls_offset':'0x2cc','user_stride':968,'user0_result_offset':'0x110',
                         'source_evidence':'82098CD0 result getter; 82213440 allocates 3880 bytes; 8213BC50 final observer update'}}
camera['basis_check']=basis(camera['forward'],camera['up'])
player=data('players')
handle=u(player,0x28); heads=data('object'); chain=[]
while handle!=0xffffffff:
    if hex(handle) in [o['recorded_handle'] for o in chain]: raise ValueError('Parent cycle')
    header=heads[(handle&65535)*16:(handle&65535)*16+16]
    if struct.unpack_from('>H',header)[0]!=handle>>16: raise ValueError('Stale object handle')
    body=data('object_'+hex(handle)); parent=u(body,0x10)
    obj={'recorded_handle':hex(handle),'tag_datum':hex(u(body,0)),
         'object_type':header[3],'parent_handle':hex(parent),
         'position':vec(body,0x54),'forward':vec(body,0x60),'up':vec(body,0x6c),
         'position_space':'world' if parent==0xffffffff else 'parent node local',
         'parent_node_index':body[0x14],
         'world_bounding_sphere_center':vec(body,0x20),
         'translational_velocity':vec(body,0x78),'angular_velocity':vec(body,0x84),
         'body_bytes_saved':len(body),'body_sha256':hashlib.sha256(body).hexdigest()}
    obj['basis_check']=basis(obj['forward'],obj['up'])
    chain.append(obj);handle=parent
variant=data('map_variant'); game=data('game_globals')
groups=json.loads((args.trace_dir/'geometry-state.json').read_text())['groups']
views=sorted({g['vertex_constants_0_18'] for g in groups})
matches=all(vec(observer,0)==list(struct.unpack_from('<3f',bytes.fromhex(v),7*16)) for v in views)
if not matches: raise ValueError('Saved camera does not match the recorded draw camera')
report={'map':'Sky Bridge','map_id':u(variant,0x100),
    'native_map_path':game[0x34:0x138].split(b'\0')[0].decode('ascii'),
    'map_sha256':'311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d',
    'exe_sha256':snapshot['exe_sha256'],'captured_unix_time':snapshot['captured_unix_time'],
    'camera':camera,'player_and_parent_chain':chain,
    'map_variant_sha256':hashlib.sha256(variant).hexdigest(),
    'recorded_vertex_constants_0_18':views,'camera_matches_recorded_draws_exactly':matches,
    'snapshot':str(args.snapshot.relative_to(repo) if args.snapshot.is_absolute() else args.snapshot),
    'snapshot_sha256':hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),
    'replay_validated':False,
    'replay_requirements':[
        'Load this exact map and map variant through native game initialization.',
        'Resolve fresh handles by player ownership, native type, and tag identity; never reuse saved handles or pointers.',
        'The player is seated in a Mongoose. Move the vehicle with the native object/physics API and preserve the seat attachment.',
        'Use the saved observer position, forward, up and projection constants as the camera witness.',
        'Verify the repeated camera and vehicle transforms numerically before accepting a repeated flicker test.',
        'This is a pose and diagnostic state snapshot, not a complete engine save state. Do not memcpy raw snapshots into another process.'
    ],
    'credit':json.loads((Path(__file__).parent/'sky-pixel-probe-build.json').read_text())['credit']}
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'output':str(args.output),'camera':camera['position'],
                  'camera_matches_draws':matches,'vehicle_position':chain[-1]['position']}))
