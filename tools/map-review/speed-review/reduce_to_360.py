"""Scale a level source (.ass) back to stock Xbox 360 Halo 3 budgets (user, 2026-11-27: "Scale the map back to
360 numbers"; PC MCC fidelity is not a goal). Only placed pieces (%-instances) are changed; structure is untouched.

For every piece definition used by a placed copy:
- Collision is kept exactly. Only pieces whose source has a collision model ('@' child of a placed copy, Microsoft
  Learn, H3 Art > Instance Objects > Collision) are reduced, so that model still holds the original shape. Pieces
  without one collide with their own visible mesh and are left as authored: adding an '@' model holding the original
  mesh crashed the importer ("bad scale (inf)", intermediate_scene.cpp #1106). That code path remains but is unused.
- The visible mesh is rebuilt: materials that look the same are merged (same shader definition, options and base
  map, same name symbols), then each piece keeps at most --max-materials surface types (the largest by triangle
  count; the rest are painted with the piece's largest one), then it is decimated with Blender's Decimate modifier
  (blender_decimate.py) to --keep of its triangles (pieces at or under --small triangles are not decimated).
- Custom fades ('@start-end' in the placement name) are removed, so the scenario/engine default fade applies.

Usage: reduce_to_360.py <in.ass> <out.ass> --materials sb_materials.json [--keep 0.34] [--max-materials 2]
       [--small 150] [--all] [--report report.json]"""
import argparse, collections, copy, json, re, subprocess, sys, tempfile, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import ass_io

BLENDER = r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
SYMS = set('%#?!@*$^-&=.;)><|~({}[')
p = argparse.ArgumentParser(); p.add_argument('src'); p.add_argument('dst'); p.add_argument('--materials', required=True)
p.add_argument('--keep', type=float, default=0.34); p.add_argument('--max-materials', type=int, default=2)
p.add_argument('--small', type=int, default=150); p.add_argument('--all', action='store_true', help='reduce every piece (collision comes from elsewhere, e.g. merge_into_structure.py)'); p.add_argument('--report', default=None)
a = p.parse_args()

def symbols(name):
    parts = name.strip('"').split(' '); sh = parts[1 if len(parts) >= 2 else 0]; k = len(sh)
    while k and sh[k - 1] in SYMS: k -= 1
    return sh[k:]

A = ass_io.read(a.src); mats = A['mats']
info = {r['i']: r for r in json.load(open(a.materials))}
def look(i):
    r = info.get(i, {})
    if not r.get('tag'): return ('raw', mats[i][0])
    return (r.get('definition'), tuple(r.get('options', [])), r.get('bitmaps', {}).get('base_map') or r['tag'], symbols(mats[i][0]))
rep = {}; first = {}
for i in range(len(mats)):
    k = look(i); first.setdefault(k, i); rep[i] = first[k]

pieces = [n for n in A['insts'] if n.obj >= 0 and n.name.startswith('"%') and A['objs'][n.obj].raw is None]
used = sorted({n.obj for n in pieces})
# definitions whose source already carries a collision model ('@' child of a placed copy) keep that one
by_uid = {n.uid: n for n in A['insts']}
has_coll = {by_uid[n.parent].obj for n in A['insts'] if n.name.startswith('"@') and n.parent in by_uid}
# --all: collision is supplied elsewhere (merge_into_structure.py), add no '@' models. Otherwise pieces without a
# collision model get one: their original mesh minus render-only ('!') triangles; their visible mesh is then marked
# render-only. (The 2026-11-27 importer crashes blamed on this were the instance renumbering, see ass_io.renumber.)
if a.all: has_coll = set(used)
def plain(i):
    d = (info.get(i) or {}).get('definition') or ''
    return d.endswith(r'shaders\shader') and not set(symbols(mats[i][0])) & set('#?')
def variant(i, s):                     # material i with symbol s added to its name symbols
    words = mats[i][0].strip('"').split(' '); k = 1 if len(words) >= 2 else 0
    if s in symbols(mats[i][0]): return i
    words[k] += s; name = '"' + ' '.join(words) + '"'
    for j, m in enumerate(mats):
        if m[0] == name: return j
    mats.append([name, mats[i][1], list(mats[i][2])]); return len(mats) - 1
jobs = {}; plan = {}
for o in used:
    ob = A['objs'][o]; t = np.array(ob.tris)
    rm = np.array([rep[m] if m >= 0 else m for m in t[:, 0]])
    count = collections.Counter(rm.tolist())
    # signs, holograms, lights, glass (non-plain or transparent shaders) always keep their own material
    top = [m for m, _ in count.most_common() if m < 0 or not plain(m)][:8]
    top += [m for m, _ in count.most_common() if m >= 0 and plain(m)][:a.max_materials]
    big = [m for m, _ in count.most_common() if m >= 0 and plain(m)]
    rm = np.where(np.isin(rm, top), rm, big[0] if big else top[0])
    slots = sorted(set(rm.tolist())); slot = {m: s for s, m in enumerate(slots)}
    ratio = 1.0 if len(t) <= a.small else max(a.keep, a.small / len(t))
    uv = np.array([[float(x) for x in (u[0].split() if u else ['0', '0'])][:2] for u in ob.uvs])
    jobs[o] = (ob.pos, uv, t[:, 1:4], np.array([slot[m] for m in rm]), ratio); plan[o] = slots

tmp = Path(tempfile.mkdtemp(dir=Path(a.dst).parent))
z = {}
for o, (pos, uv, tri, mm, r) in jobs.items():
    z[f'p{o}'] = pos; z[f'u{o}'] = uv; z[f't{o}'] = tri; z[f'm{o}'] = mm; z[f'r{o}'] = np.array(r)
np.savez(tmp / 'in.npz', **z)
subprocess.run([BLENDER, '--background', '--factory-startup', '--python', str(Path(__file__).parent / 'blender_decimate.py'),
                '--', str(tmp / 'in.npz'), str(tmp / 'out.npz')], check=True, capture_output=True)
R = np.load(tmp / 'out.npz')

rep_out = collections.Counter()
coll_obj = {}; tris_orig = {}
for o in used:
    ob = A['objs'][o]
    rep_out['render_tris_before'] += len(ob.tris)
    rep_out['render_parts_before'] += len({t[0] for t in ob.tris})
    tris_orig[o] = len(ob.tris)
    if o not in has_coll:
        keep_t = [t for t in ob.tris if t[0] < 0 or '!' not in symbols(mats[t[0]][0])]
        if keep_t:
            col = copy.copy(ob); col.pos, col.nrm, col.col = ob.pos.copy(), ob.nrm.copy(), ob.col.copy()
            col.infl, col.uvs, col.tris = list(ob.infl), list(ob.uvs), keep_t
            A['objs'].append(col); coll_obj[o] = len(A['objs']) - 1
            plan[o] = [variant(m, '!') if m >= 0 else m for m in plan[o]]
    np_, nn, nu, nt, nm = R[f'p{o}'], R[f'n{o}'], R[f'u{o}'], R[f't{o}'], R[f'm{o}']
    slots = plan[o]
    ob.pos, ob.nrm, ob.col = np_.astype(float), nn.astype(float), np.zeros((len(np_), 3))
    ob.infl = [[] for _ in range(len(np_))]
    ob.uvs = [[f'{u:.10f}\t{v:.10f}\t0.0000000000'] for u, v in nu]
    ob.tris = [(slots[s], int(x), int(y), int(w)) for s, (x, y, w) in zip(nm, nt)]
    rep_out['definitions'] += 1; rep_out['render_tris_after'] += len(ob.tris); rep_out['render_parts_after'] += len(slots)
R.close()

uid = max(n.uid for n in A['insts']) + 1; done = set(); new = []
for n in A['insts']:
    new.append(n)
    if n in pieces:
        rep_out['placed_tris_before'] += tris_orig[n.obj]; rep_out['placed_tris_after'] += len(A['objs'][n.obj].tris)
        rep_out['placed_parts_after'] += len(plan[n.obj])
        n.name = re.sub(r'@\d+-\d+(?=")', '', n.name)
        if n.obj in coll_obj and n.obj not in done:
            done.add(n.obj)
            base = re.sub(r'^%[?!>\-]*', '', n.name.strip('"')); base = re.sub(r'\(\d+\)$', '', base)
            c = ass_io.Inst(); c.obj = coll_obj[n.obj]; c.name = f'"@{base}"'; c.uid = uid; uid += 1
            c.parent = n.uid; c.flag = n.flag; c.local = n.pivot; c.pivot = ([0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0], 1.0)
            c.bones = []; new.append(c); rep_out['collision_models'] += 1
A['insts'] = ass_io.renumber(new)
ass_io.write(a.dst, A)
for f in tmp.iterdir(): f.unlink()
tmp.rmdir()
print(json.dumps(rep_out))
if a.report: json.dump(rep_out, open(a.report, 'w'), indent=1)
