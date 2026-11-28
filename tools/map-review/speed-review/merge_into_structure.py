"""Move the visible geometry of placed pieces (%-instances) into the structure, keep their collision as invisible
pieces (user, 2026-11-27: Sky Bridge to stock 360 budgets, at least 42 FPS at every pain spot).

Why: the game draws a placed piece once per material per copy, but structure once per material per cluster
(50 clusters on Sky Bridge), so ~2,800 piece parts become ~160 structure parts (structure_sim.py). Structure
collision cannot take the pieces' collision (small collision BSP: 32,767 surfaces, 65,534 vertices per BSP;
tools/ho2h3/Halo3Limits.cs), so collision stays on the pieces, which become collision-only.

Material symbols (tool.exe's own table "%#?!@*$^-&=.;)><|~({}[", same order as the Halo 2 convention):
'!' render only, '@' collision only.
- Render copy: each placed copy's mesh, baked to world space (world_parent @ local @ pivot, ass_io conventions),
  materials + '!', triangles whose material is already collision-only ('@') left out. One structure object per copy,
  under the structure's own node.
- Collision piece: the % definition's mesh is replaced by its collision source (the '@' child model when the source
  has one, else the original mesh, which is what the game collided with), materials + '@', triangles whose material
  is already render-only ('!') left out. The '@' children are removed (their mesh is now the definition itself).

Usage: merge_into_structure.py <reduced.ass> <original.ass> <out.ass> [--structure-node structure]
The reduced file supplies the visible meshes (reduce_to_360.py output), the original the untouched meshes of pieces
reduce_to_360.py left alone and every collision source."""
import argparse, collections, copy, json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import ass_io

p = argparse.ArgumentParser(); p.add_argument('reduced'); p.add_argument('original'); p.add_argument('dst')
p.add_argument('--structure-node', default='structure')
p.add_argument('--clusters', default=None, help='exported structure (json with data.clusters bounds, world units): put each '
               "cluster's visible geometry in ONE render-only instance instead of the structure")
p.add_argument('--cell', type=float, default=None, help='group visible geometry in render-only instances per grid cell '
               'of this size (world units) instead of per cluster')
p.add_argument('--palette', type=int, default=None, help='keep the K most-used piece materials (plus every non-plain '
               'shader: holograms, decals, glass..., and transparent ones); other materials are painted with the '
               "piece's own most-used kept material")
p.add_argument('--materials', default=None, help='sb_materials.json (shader definitions), needed with --palette')
a = p.parse_args()
R = ass_io.read(a.reduced); O = ass_io.read(a.original)
assert len(R['mats']) == len(O['mats'])
mats = R['mats']
SYMS = set('%#?!@*$^-&=.;)><|~({}[')

def split(name):
    words = name.strip('"').split(' '); k = 1 if len(words) >= 2 else 0
    w = words[k]; j = len(w)
    while j and w[j - 1] in SYMS: j -= 1
    return words, k, w[:j], w[j:]
def flags(i): return split(mats[i][0])[3]
variant = {}
def with_symbol(i, s):
    if (i, s) in variant: return variant[(i, s)]
    words, k, base, sy = split(mats[i][0])
    if s in sy: variant[(i, s)] = i; return i
    words[k] = base + sy + s
    mats.append(['"' + ' '.join(words) + '"', mats[i][1], list(mats[i][2])]); variant[(i, s)] = len(mats) - 1
    return variant[(i, s)]

def sub(ob, keep_tri, remap):
    """copy of mesh ob with only triangles keep_tri(material), materials remapped; unused vertices dropped"""
    tr = [t for t in ob.tris if keep_tri(t[0])]
    used = sorted({v for t in tr for v in t[1:]}); new = {v: k for k, v in enumerate(used)}
    m = copy.copy(ob); m.pos = ob.pos[used].copy(); m.nrm = ob.nrm[used].copy(); m.col = ob.col[used].copy()
    m.infl = [[] for _ in used]; m.uvs = [ob.uvs[v] for v in used]
    m.tris = [(remap(t[0]), new[t[1]], new[t[2]], new[t[3]]) for t in tr]
    return m

Rins = R['insts']; by = {n.uid: n for n in Rins}
Obys = {n.uid: n for n in O['insts']}
W = ass_io.world_matrices(Rins)
snode = next(n for n in Rins if n.name == f'"{a.structure_node}"')
assert np.allclose(W[snode.uid], np.eye(4), atol=1e-6), 'structure node is not at the origin'
pieces = [n for n in Rins if n.obj >= 0 and n.name.startswith('"%') and R['objs'][n.obj].raw is None]
coll_child = {}                       # definition (object index) -> collision object index
for n in Rins:
    if n.name.startswith('"@') and n.parent in by: coll_child[by[n.parent].obj] = n.obj
drop_uids = {n.uid for n in Rins if n.name.startswith('"@') and n.parent in by and by[n.parent].name.startswith('"%')}

objs = R['objs']; out_objs = list(objs); rep = collections.Counter()
paint = {}                             # (definition object, material) -> material
if a.palette:
    info = {r['i']: r for r in json.load(open(a.materials))}
    use = collections.Counter()
    for n in pieces: use.update(t[0] for t in objs[n.obj].tris)
    def protected(m):
        d = (info.get(m) or {}).get('definition') or ''
        return not d.endswith('shaders\\shader') or '#' in flags(m) or '?' in flags(m)
    keep_m = {m for m, _ in use.most_common(a.palette)} | {m for m in use if protected(m)}
    for o in {n.obj for n in pieces}:
        own = collections.Counter(t[0] for t in objs[o].tris)
        kept = [m for m, _ in own.most_common() if m in keep_m]
        for m in own: paint[(o, m)] = m if (m in keep_m or not kept) else kept[0]
    rep['palette'] = len(keep_m)
uid = max(n.uid for n in Rins) + 1; new_insts = []; vis_list = []
for n in pieces:
    ob = objs[n.obj]
    if not len(ob.tris): continue
    M = W[n.uid] @ ass_io.matrix(n.pivot)
    vis = sub(ob, lambda m: m < 0 or '@' not in flags(m), lambda m, o=n.obj: m if m < 0 else with_symbol(paint.get((o, m), m), '!'))
    vis.pos = (np.c_[vis.pos, np.ones(len(vis.pos))] @ M.T)[:, :3]
    nr = vis.nrm @ M[:3, :3].T; vis.nrm = nr / np.maximum(np.linalg.norm(nr, axis=1, keepdims=True), 1e-12)
    vis.xref_path = vis.xref_name = '""'
    vis_list.append((n, vis)); rep['render_copies'] += 1; rep['render_tris'] += len(vis.tris)

def concat(ms):
    m = copy.copy(ms[0]); off = 0; tris = []
    for x in ms: tris += [(t[0], t[1] + off, t[2] + off, t[3] + off) for t in x.tris]; off += len(x.pos)
    m.pos = np.vstack([x.pos for x in ms]); m.nrm = np.vstack([x.nrm for x in ms]); m.col = np.vstack([x.col for x in ms])
    m.infl = [v for x in ms for v in x.infl]; m.uvs = [v for x in ms for v in x.uvs]; m.tris = tris
    return m
def place(mesh, name, prefix):
    global uid
    out_objs.append(mesh)
    c = ass_io.Inst(); c.obj = len(out_objs) - 1; c.name = f'"{prefix}{name}"'
    c.uid = uid; uid += 1; c.parent = snode.uid; c.flag = 0
    c.local = ([0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0], 1.0); c.pivot = ([0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0], 1.0); c.bones = []
    new_insts.append(c)
if a.clusters is None and a.cell is None:   # into the structure: one structure object per copy
    for n, vis in vis_list: place(vis, 'sv_' + n.name.strip('"').lstrip('%?!>-') + f'_{n.uid}', '')
else:                                  # render-only instances per grid cell or cluster (copy's bounds centre, cm -> wu)
    groups = collections.defaultdict(list)
    if a.cell:
        for n, vis in vis_list:
            c = (vis.pos.min(0) + vis.pos.max(0)) / 200.0
            groups[tuple((c // a.cell).astype(int))].append(vis)
    else:
        cl = json.load(open(a.clusters))['data']['clusters']
        B = np.array([[list(map(float, c[f'bounds {x}'].split(','))) for x in 'xyz'] for c in cl])   # (k,3,2)
        for n, vis in vis_list:
            c = (vis.pos.min(0) + vis.pos.max(0)) / 200.0
            d = np.maximum(np.maximum(B[:, :, 0] - c, c - B[:, :, 1]), 0).sum(1)
            groups[int(np.argmin(d))].append(vis)
    for k in sorted(groups):
        chunk = []                     # keep each instance mesh well under the kit's 32,767 vertices per instance section (tool splits more)
        for m in groups[k] + [None]:
            if m is None or (chunk and sum(len(x.pos) for x in chunk) + len(m.pos) > 24000):
                place(concat(chunk), f'sv_area_{rep["groups"]}', '%'); rep['groups'] += 1; chunk = []
            if m is not None: chunk.append(m)

done = set()
for n in pieces:
    if n.obj in done: continue
    done.add(n.obj)
    src = O['objs'][coll_child[n.obj]] if n.obj in coll_child else O['objs'][n.obj]
    col = sub(src, lambda m: m < 0 or '!' not in flags(m), lambda m: m if m < 0 else with_symbol(m, '@'))
    if not col.tris:                   # render-only piece: nothing to collide with, nothing to draw
        rep['render_only_definitions'] += 1
    out_objs[n.obj] = col; rep['collision_definitions'] += 1; rep['collision_tris'] += len(col.tris)

keep = []
for n in Rins:
    if n.uid in drop_uids: continue
    if n.name.startswith('"%') and n.obj >= 0 and not out_objs[n.obj].tris: rep['placements_removed_empty'] += 1; continue
    keep.append(n)
R['objs'] = out_objs; R['insts'] = ass_io.renumber(keep + new_insts)
ass_io.write(a.dst, R)
rep['materials'] = len(mats); print(json.dumps(rep))
