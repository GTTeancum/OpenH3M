"""Add placed Halo 2 scenery to a version-2 ASS level source as instanced level geometry.

Each scenery type's mesh comes from its Halo 2 render-model source (tool extract-render-data JMS); every placement
from the Halo 2 scenario becomes an instance of that mesh (name prefixed '%', instanced geometry), at the Halo 2
position (x100 ASS units) and rotation (yaw about z, pitch, roll; Halo convention R = Rz(yaw) Ry(-pitch) Rx(roll)).
Materials are matched to the ASS material list by shader name ('hang ' collection prefix and lighting suffix
symbols stripped); unknown ones are appended. '+seamsealer' triangles are dropped.
Usage: ass2_add_instances.py <in.ass> <out.ass> <placements.json> <type=jms path>...
"""
import json, math, sys
from pathlib import Path


def lines_of(path):
    return [l.rstrip('\r') for l in open(path, encoding='latin-1').read().split('\n')]


def data_lines(path):
    return [l.strip() for l in lines_of(path) if l.strip() and not l.strip().startswith(';')]


def parse_jms(path):
    t = data_lines(path); i = 0
    def nxt():
        nonlocal i; i += 1; return t[i - 1]
    assert nxt() == '8210'
    for _ in range(int(nxt())): nxt(); nxt(); nxt(); nxt()                 # nodes
    mats = []
    for _ in range(int(nxt())): mats.append(nxt()); nxt()                   # name, lighting/LOD line
    for _ in range(int(nxt())): nxt(); nxt(); nxt(); nxt(); nxt()           # markers
    for _ in range(int(nxt())): nxt(); nxt()                                # xref paths
    for _ in range(int(nxt())): nxt(); nxt(); nxt(); nxt(); nxt()           # instance markers
    verts = []
    for _ in range(int(nxt())):
        pos = nxt(); nrm = nxt()
        for _ in range(int(nxt())): nxt(); nxt()                            # node influences
        uvs = [nxt() for _ in range(int(nxt()))]
        verts.append((pos, nrm, uvs[0] if uvs else '0.0\t0.0'))
    tris = []
    for _ in range(int(nxt())):
        m = int(nxt()); v = [int(x) for x in nxt().split()]
        tris.append((m, v))
    return mats, verts, tris


def clean(name):
    n = name.strip('"')
    if n.lower().startswith('hang '): n = n[5:]
    return n.rstrip('%!*@#=?^&-+<>| ').strip()


def quat(yaw, pitch, roll):
    y, p, r = (math.radians(a) / 2 for a in (yaw, -pitch, roll))
    qz = (0, 0, math.sin(y), math.cos(y)); qy = (0, math.sin(p), 0, math.cos(p)); qx = (math.sin(r), 0, 0, math.cos(r))
    def mul(a, b):
        ax, ay, az, aw = a; bx, by, bz, bw = b
        return (aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz)
    return mul(mul(qz, qy), qx)


src, out, placements = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
types = dict(a.split('=', 1) for a in sys.argv[4:])
L = lines_of(src)
mat_hdr = L.index(';### MATERIALS ###'); obj_hdr = L.index(';### OBJECTS ###'); inst_hdr = L.index(';### INSTANCES ###')
# existing materials: count line then blocks of ';MATERIAL n', name, second line
mcount_i = next(k for k in range(mat_hdr + 1, obj_hdr) if L[k].strip().isdigit())
mat_names = [clean(L[k + 1]) for k in range(mcount_i, obj_hdr) if L[k].startswith(';MATERIAL ')]
mat_index = {}
for k, n in enumerate(mat_names): mat_index.setdefault(n.lower(), k)
new_mats = []
ocount_i = next(k for k in range(obj_hdr + 1, inst_hdr) if L[k].strip().isdigit()); n_obj = int(L[ocount_i])
icount_i = next(k for k in range(inst_hdr + 1, len(L)) if L[k].strip().isdigit()); n_inst = int(L[icount_i])
new_objs, new_insts = [], []
uid = 900000
# Parent new instances to the level frame (the importer only takes nodes under it); its rotation is identity and
# scale 1 (checked), so a child's local translation is world minus the frame's translation.
frame_i = next(k for k in range(icount_i, len(L)) if L[k].startswith('"frame '))
assert L[frame_i + 4].split() == ['0.0000000000', '0.0000000000', '0.0000000000', '1.0000000000'] and float(L[frame_i + 6]) == 1.0
frame_index = int(L[frame_i - 2].split()[-1])
frame_t = [float(v) for v in L[frame_i + 5].split()]
for tname, jms in types.items():
    rows = [r for r in placements['scenery'] if r['palette'] and r['palette'].split('\\')[-1] == tname]
    if not rows: print('no placements for', tname); continue
    mats, verts, tris = parse_jms(jms)
    remap = {}
    for k, m in enumerate(mats):
        c = clean(m)
        if c.startswith('+seamsealer'): remap[k] = None; continue
        if c.lower() not in mat_index:
            mat_index[c.lower()] = len(mat_names) + len(new_mats); new_mats.append(c)
        remap[k] = mat_index[c.lower()]
    kept = [(remap[m], v) for m, v in tris if remap.get(m) is not None]
    obj = ['', f';OBJECT {n_obj + len(new_objs)}', '"MESH"', '""', '""', str(len(verts))]
    for pos, nrm, uv in verts: obj += [pos, nrm, '0', '1', uv]
    obj.append(str(len(kept)))
    for m, v in kept: obj += [str(m)] + [str(x) for x in v]
    oi = n_obj + len(new_objs); new_objs.append(obj)
    for j, r in enumerate(rows):
        x, y, z = (float(a) * 100 - f for a, f in zip(r['position'].split(','), frame_t))
        q = quat(*(float(a) for a in r['rotation'].split(',')))
        uid += 1
        new_insts.append(['', f';INSTANCE {n_inst + len(new_insts)}', str(oi), f'"%{tname}_{j}"', str(uid), str(frame_index), '0',
                          '\t'.join(f'{v:.10f}' for v in q), f'{x:.10f}\t{y:.10f}\t{z:.10f}', '1.0000000000',
                          '0.0000000000\t0.0000000000\t0.0000000000\t1.0000000000', '0.0000000000\t0.0000000000\t0.0000000000', '1.0000000000'])
    print(f'{tname}: {len(rows)} placements, {len(verts)} vertices, {len(kept)} triangles')
mat_block = []
for k, n in enumerate(new_mats):
    mat_block += ['', f';MATERIAL {len(mat_names) + k}', f'"{n}"', '""']
L[mcount_i] = str(len(mat_names) + len(new_mats)); L[ocount_i] = str(n_obj + len(new_objs)); L[icount_i] = str(n_inst + len(new_insts))
res = L[:obj_hdr] + mat_block + [''] + L[obj_hdr:inst_hdr] + sum(new_objs, []) + [''] + L[inst_hdr:] + sum(new_insts, [])
open(out, 'w', encoding='latin-1', newline='\n').write('\n'.join(res) + '\n')
print('materials added:', new_mats, '| objects added:', len(new_objs), '| instances added:', len(new_insts))
