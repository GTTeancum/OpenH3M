"""Read and write Halo 3 ASS (version 7) level-geometry source files, as produced by the editing kit
(tool extract-import-info). Format and transform conventions follow the General-101 Halo Asset Blender
Development Toolset reader (file_ass/process_file.py, build_scene.py): quaternions are x y z w and not
inverted for version 7; a node's world matrix is parent_world @ LocRotScale(local); mesh vertices of an
instanced node are placed by world_parent @ local @ pivot."""
import numpy as np


class Tokens:
    def __init__(self, path):
        self.lines = open(path, encoding='utf-8', errors='surrogateescape').read().split('\n')
        self.i = 0

    def next(self):
        while True:
            line = self.lines[self.i].strip(); self.i += 1
            if line and not line.startswith(';'):
                return line


def floats(s):
    return [float(x.rsplit('.', 1)[0]) if x.count('.') > 1 else float(x) for x in s.split()]


class Mesh:
    __slots__ = ('cls', 'xref_path', 'xref_name', 'raw', 'pos', 'nrm', 'col', 'infl', 'uvs', 'tris')


class Inst:
    __slots__ = ('obj', 'name', 'uid', 'parent', 'flag', 'local', 'pivot', 'bones')


def read(path):
    t = Tokens(path)
    version = int(t.next()); assert version == 7, version
    header = [t.next() for _ in range(4)]
    mats = []
    for _ in range(int(t.next())):
        name = t.next(); variant = t.next(); info = [t.next() for _ in range(int(t.next()))]
        mats.append([name, variant, info])
    objs = []
    for _ in range(int(t.next())):
        o = Mesh(); o.cls = t.next(); o.xref_path = t.next(); o.xref_name = t.next(); o.raw = None
        if o.cls == '"MESH"':
            n = int(t.next()); pos = np.empty((n, 3)); nrm = np.empty((n, 3)); col = np.empty((n, 3)); infl = []; uvs = []
            for k in range(n):
                pos[k] = floats(t.next()); nrm[k] = floats(t.next()); col[k] = floats(t.next())
                infl.append([(int(t.next()), t.next()) for _ in range(int(t.next()))])
                uvs.append([t.next() for _ in range(int(t.next()))])
            o.pos, o.nrm, o.col, o.infl, o.uvs = pos, nrm, col, infl, uvs
            o.tris = [tuple(int(t.next()) for _ in range(4)) for _ in range(int(t.next()))]
        else:
            # Non-mesh objects (lights, spheres, boxes, pills) are kept verbatim.
            fields = {'"SPHERE"': 2, '"BOX"': 2, '"PILL"': 3, '"GENERIC_LIGHT"': 13}[o.cls]
            o.raw = [t.next() for _ in range(fields)]
        objs.append(o)
    insts = []
    for _ in range(int(t.next())):
        n = Inst(); n.obj = int(t.next()); n.name = t.next(); n.uid = int(t.next()); n.parent = int(t.next()); n.flag = int(t.next())
        n.local = (floats(t.next()), floats(t.next()), float(t.next())); n.pivot = (floats(t.next()), floats(t.next()), float(t.next()))
        nb = len({i for v in objs[n.obj].infl for i, _ in v}) if n.obj >= 0 and objs[n.obj].cls == '"MESH"' else 0
        n.bones = [t.next() for _ in range(nb)]
        insts.append(n)
    return dict(header=header, mats=mats, objs=objs, insts=insts)


def f(x):
    return f'{x:.10f}'


def write(path, a):
    out = []; w = out.append
    w(';### HEADER ###'); w('7'); [w(h) for h in a['header']]; w('')
    w(';### MATERIALS ###'); w(str(len(a['mats']))); w('')
    for i, (name, variant, info) in enumerate(a['mats']):
        w(f';MATERIAL{i}'); w(name); w(variant); w(str(len(info))); [w(x) for x in info]; w('')
    w(';### OBJECTS ###'); w(str(len(a['objs']))); w('')
    for i, o in enumerate(a['objs']):
        w(f';###OBJECT{i}###'); w(o.cls); w(o.xref_path); w(o.xref_name)
        if o.raw is not None:
            [w(x) for x in o.raw]
        else:
            w(str(len(o.pos)))
            for k in range(len(o.pos)):
                w('\t'.join(map(f, o.pos[k]))); w('\t'.join(map(f, o.nrm[k]))); w('\t'.join(map(f, o.col[k])))
                w(str(len(o.infl[k]))); [w(f'{n}\n{wt}') for n, wt in o.infl[k]]
                w(str(len(o.uvs[k]))); [w(uv) for uv in o.uvs[k]]
                w('')
            w(str(len(o.tris)))
            for tri in o.tris: w(f'{tri[0]}\n{tri[1]}\t{tri[2]}\t{tri[3]}')
        w('')
    w(';### INSTANCES ###'); w(str(len(a['insts']))); w('')
    for i, n in enumerate(a['insts']):
        w(f';INSTANCE {i}'); w(str(n.obj)); w(n.name); w(str(n.uid)); w(str(n.parent)); w(str(n.flag))
        for q, p, s in (n.local, n.pivot):
            w('\t'.join(map(f, q))); w('\t'.join(map(f, p))); w(f(s))
        [w(b) for b in n.bones]; w('')
    open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='\n').write('\n'.join(out) + '\n')


def matrix(t):
    (x, y, z, ww), p, s = t
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * ww), 2 * (x * z + y * ww)],
                  [2 * (x * y + z * ww), 1 - 2 * (x * x + z * z), 2 * (y * z - x * ww)],
                  [2 * (x * z - y * ww), 2 * (y * z + x * ww), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * s; M[:3, 3] = p
    return M


def world_matrices(insts):
    by_uid = {n.uid: n for n in insts}; cache = {}
    def g(n):
        if n.uid in cache: return cache[n.uid]
        M = matrix(n.local)
        if n.parent != -1: M = g(by_uid[n.parent]) @ M
        cache[n.uid] = M; return M
    return {n.uid: g(n) for n in insts}
