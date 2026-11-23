"""Choose which folded pieces stay instanced so every structure section (one per cluster) stays inside the
editing kit's per-section limits. Each folded piece's vertices are classified into clusters by walking the
kit-built map's collision BSP (leaf -> cluster), the same data the repository's collision tools read.

Usage: cluster_budget.py <kit-built MCC map> <scenario> <fold report.json> <folded.ass> <out keep-instanced.txt>
       [--max-vertices N] [--max-triangles N]
"""
import argparse, json, collections, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from forge_collision_mesh import read_mesh

p = argparse.ArgumentParser(); p.add_argument('map'); p.add_argument('scenario'); p.add_argument('report'); p.add_argument('ass'); p.add_argument('out')
p.add_argument('--whole', choices=['split', 'center', 'origin'], default='split', help='how the importer places a folded piece: split by area, whole at its centre, or whole at its node origin')
p.add_argument('--max-vertices', type=int, default=26000); p.add_argument('--max-triangles', type=int, default=40000)
a = p.parse_args()
c = Cache(a.map, mcc=True)
tag, arr = read_mesh(c, a.scenario)
nodes, planes = arr[0], arr[1]
leaf_cluster = [c.data[r] for r in c.block(tag['offset'] + 0x34, 1)]
assert len(leaf_cluster) == len(arr[2]), (len(leaf_cluster), len(arr[2]))
P = np.array(planes, dtype=np.float64)

def cluster_of(pt):
    n = 0
    for _ in range(4096):
        plane, back, front = nodes[n]
        nx, ny, nz, w = P[plane]
        child = front if nx * pt[0] + ny * pt[1] + nz * pt[2] - w >= 0 else back
        if child == -1: return None
        if child < 0: return leaf_cluster[child & 0x7fffffff]
        n = child
    return None

rep = json.load(open(a.report)); folded = rep['folded']
L = open(a.ass, encoding='utf-8', errors='surrogateescape').read().split('\n')
obj_starts = [i for i, l in enumerate(L) if l.startswith(';###OBJECT')]
inst_obj = {L[i + 2].strip('"'): int(L[i + 1]) for i, l in enumerate(L) if l.startswith(';INSTANCE ')}

def piece(o):
    j = obj_starts[o] + 4
    while not L[j].strip(): j += 1
    nv = int(L[j]); j += 1; pts = []
    for _ in range(nv):
        while not L[j].strip(): j += 1
        pts.append([float(x) for x in L[j].split()]); j += 3
        ni = int(L[j]); j += 1 + 2 * ni; nu = int(L[j]); j += 1 + nu
    while not L[j].strip(): j += 1
    return np.array(pts) * 0.01, int(L[j])

pieces = []
for k, name in folded:
    pts, nt = piece(inst_obj[f's3dmerged_{k}'])
    if a.whole == 'split':
        sample = pts[np.linspace(0, len(pts) - 1, min(len(pts), 64)).astype(int)]
        cls = collections.Counter(cluster_of(q) for q in sample); cls.pop(None, None)
        share = {cl: n / max(1, sum(cls.values())) for cl, n in cls.items()}
    else:
        q = (pts.min(0) + pts.max(0)) / 2 if a.whole == 'center' else np.zeros(3)
        cl = cluster_of(q); share = {cl: 1.0} if cl is not None else {}
    pieces.append(dict(name=name, v=len(pts), t=nt, share=share))
load_v = collections.Counter(); load_t = collections.Counter()
for pc in pieces:
    for cl, f in pc['share'].items(): load_v[cl] += pc['v'] * f; load_t[cl] += pc['t'] * f
keep = set()
for cl in sorted(load_v, key=lambda x: -load_v[x]):
    if load_v[cl] <= a.max_vertices and load_t[cl] <= a.max_triangles: continue
    for pc in sorted((pc for pc in pieces if cl in pc['share'] and pc['name'] not in keep), key=lambda pc: -pc['v'] * pc['share'][cl]):
        if load_v[cl] <= a.max_vertices and load_t[cl] <= a.max_triangles: break
        keep.add(pc['name'])
        for c2, f in pc['share'].items(): load_v[c2] -= pc['v'] * f; load_t[c2] -= pc['t'] * f
unplaced = sum(1 for pc in pieces if not pc['share'])
Path(a.out).write_text('\n'.join(sorted(keep)) + '\n')
top = sorted(load_v.items(), key=lambda kv: -kv[1])[:6]
print(json.dumps(dict(pieces=len(pieces), keep_instanced=len(keep), unplaced=unplaced,
                      heaviest_after=[(int(k), int(v), int(load_t[k])) for k, v in top])))
