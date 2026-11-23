"""Fold single-use instanced geometry into the main structure of a Halo 3 ASS level source, for the editing
kit's own structure importer (tool structure <ass>).

For every instanced node (name starting with %) whose mesh object is used by that node only:
  * a draw-only copy (materials marked "!") is added as ordinary structure geometry, its vertices moved to
    the node's world position (normals rotated), so the importer batches it with the cluster geometry;
  * the original instanced object keeps its placement but its triangles switch to collision-only
    materials ("@"), so collision and its per-instance limits stay exactly as authored.
Every untouched line of the file is kept verbatim. Transform conventions: see ass_io.py.

Usage: ass_merge.py <in.ass> <out.ass> [--dry-run] [--max-tris N] [--report out.json]
"""
import argparse, json, re, collections
from pathlib import Path
import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).parent))
from ass_io import matrix

p = argparse.ArgumentParser(); p.add_argument('src', type=Path); p.add_argument('out', type=Path)
p.add_argument('--dry-run', action='store_true'); p.add_argument('--max-tris', type=int, default=10 ** 9)
p.add_argument('--report', type=Path)
p.add_argument('--combine-cell', type=float, default=0, help='combine picked pieces into new instanced pieces per neighbourhood of this size (ASS units, 100 = 1 world unit) instead of folding into the structure')
p.add_argument('--max-group-vertices', type=int, default=30000)
p.add_argument('--max-group-triangles', type=int, default=20000)
p.add_argument('--max-uses', type=int, default=1, help='fold instanced objects used by at most this many nodes (all their nodes are folded)')
p.add_argument('--max-dup-tris', type=int, default=-1, help='instead of --max-uses: fold an object unless its extra copies add more than this many triangles')
a = p.parse_args()
L = a.src.read_text(encoding='utf-8', errors='surrogateescape').split('\n')
i = 0
def skip_blank():
    global i
    while not L[i].strip() or L[i].lstrip().startswith(';'): i += 1
def take():
    global i
    skip_blank(); v = L[i]; i += 1; return v
def fl(s): return [float(x) for x in s.split()]

assert take().strip() == '7'
for _ in range(4): take()
skip_blank(); mat_count_line = i; nmat = int(take())
mats = []
for _ in range(nmat):
    skip_blank(); start = i; name = take(); variant = take(); n = int(take()); [take() for _ in range(n)]
    mats.append(dict(name=name, start=start, end=i))
skip_blank(); obj_count_line = i; nobj = int(take())
objs = []
for _ in range(nobj):
    skip_blank(); start = i; cls = take(); take(); take(); o = dict(cls=cls, start=start)
    if cls == '"MESH"':
        nv = int(take()); vstart = i; inf_any = False; verts = []
        for _ in range(nv):
            skip_blank(); pl = i; take(); take(); take(); ni = int(take())
            if ni: inf_any = True
            [take() for _ in range(ni)]
            nu = int(take()); [take() for _ in range(nu)]
            verts.append(pl)
        skip_blank(); tcount = i; nt = int(take()); tris = []
        for _ in range(nt):
            skip_blank(); tris.append(i); i += 1
        o.update(nv=nv, verts=verts, tris=tris, influences=inf_any, tcount=tcount)
    else:
        o['raw_until'] = None
        fields = {'"SPHERE"': 2, '"BOX"': 2, '"PILL"': 3, '"GENERIC_LIGHT"': 13}[cls]
        [take() for _ in range(fields)]
    o['end'] = i; objs.append(o)
skip_blank(); inst_count_line = i; ninst = int(take())
insts = []
for _ in range(ninst):
    skip_blank(); start = i
    obj = int(take()); name = take(); uid = int(take()); parent = int(take()); flag = int(take())
    local = (fl(take()), fl(take()), float(take())); pivot = (fl(take()), fl(take()), float(take()))
    o = objs[obj] if obj >= 0 else None
    if o is not None and o['cls'] == '"MESH"' and o['influences']:
        raise SystemExit('weighted vertices are not handled')
    insts.append(dict(obj=obj, name=name, uid=uid, parent=parent, local=local, pivot=pivot, start=start, end=i))
by_uid = {n['uid']: n for n in insts}; wcache = {}
def world(n):
    if n['uid'] in wcache: return wcache[n['uid']]
    M = matrix(n['local'])
    if n['parent'] != -1: M = world(by_uid[n['parent']]) @ M
    wcache[n['uid']] = M; return M
uses = {}
for n in insts:
    if n['obj'] >= 0: uses[n['obj']] = uses.get(n['obj'], 0) + 1
structure = [n for n in insts if n['name'] == '"structure"']; assert len(structure) == 1, 'expected one structure node'
S = structure[0]; S_inv = np.linalg.inv(world(S))
pick = [n for n in insts if n['name'].startswith('"%') and n['obj'] >= 0 and objs[n['obj']]['cls'] == '"MESH"'
        and (uses[n['obj']] <= a.max_uses if a.max_dup_tris < 0 else len(objs[n['obj']]['tris']) * (uses[n['obj']] - 1) <= a.max_dup_tris) and len(objs[n['obj']]['tris']) <= a.max_tris
        and all(m['name'].startswith('"%') for m in insts if m['obj'] == n['obj'])]
inst_nodes = [n for n in insts if n['name'].startswith('"%') and n['obj'] >= 0]
report = dict(extra_triangles=sum(len(objs[o]['tris']) * (uses[o] - 1) for o in {n['obj'] for n in pick}), instanced_nodes=len(inst_nodes), picked_nodes=len(pick), picked_objects=len({n['obj'] for n in pick}),
              picked_triangles=sum(len(objs[n['obj']]['tris']) for n in pick),
              all_instanced_triangles=sum(len(objs[n['obj']]['tris']) for n in inst_nodes if objs[n['obj']]['cls'] == '"MESH"'))
print(json.dumps(report))
if a.dry_run:
    sys.exit(0)

SYMS = set('%#?!@*$^-&=.;)><|~({}[')
def shader_index(parts): return 1 if len(parts) >= 2 else 0
def symbols(name):
    parts = name.strip('"').split(' '); sh = parts[shader_index(parts)]
    k = len(sh)
    while k and sh[k - 1] in SYMS: k -= 1
    return set(sh[k:])
def mark(name, sym):
    parts = name.strip('"').split(' '); j = shader_index(parts)
    if sym not in parts[j]: parts[j] = parts[j] + sym
    return '"' + ' '.join(parts) + '"'
def mat_name(m):
    block = L[mats[m]['start']:mats[m]['end']]
    return next(x for x in block if x.strip().startswith('"'))

used = sorted({int(L[t].split()[0]) for n in pick for t in objs[n['obj']]['tris']})
render_idx, coll_idx, new_mat_text = {}, {}, []
for m in used:
    block = L[mats[m]['start']:mats[m]['end']]
    k = next(j for j, x in enumerate(block) if x.strip().startswith('"'))
    for table, sym in ((render_idx, '!'), (coll_idx, '@')):
        table[m] = nmat + len(new_mat_text)
        b = list(block); b[k] = mark(b[k], sym)
        b = [x for x in b if not x.strip().startswith(';')]
        new_mat_text.append([f';MATERIAL{table[m]}'] + b + [''])


if a.combine_cell > 0:
    def ff(x): return f'{x:.10f}'
    def node_matrix(n):
        return (world(by_uid[n['parent']]) if n['parent'] != -1 else np.eye(4)) @ matrix(n['local']) @ matrix(n['pivot'])
    def obj_vertices(o):
        res = []
        for pl in o['verts']:
            j = pl
            while not L[j].strip(): j += 1
            pos = np.array(fl(L[j])); j += 1
            while not L[j].strip(): j += 1
            nrm = np.array(fl(L[j])); j += 1
            rest = []
            while not L[j].strip(): j += 1
            rest.append(L[j]); j += 1                    # colour
            while not L[j].strip(): j += 1
            rest.append(L[j]); j += 1                    # influence count (0)
            while not L[j].strip(): j += 1
            nu = int(L[j]); rest.append(L[j]); j += 1
            for _ in range(nu):
                while not L[j].strip(): j += 1
                rest.append(L[j]); j += 1
            res.append((pos, nrm, rest))
        return res
    # world-space centres and sizes of picked pieces
    info = []
    for n in pick:
        o = objs[n['obj']]; M = node_matrix(n)
        verts = obj_vertices(o)
        P = np.array([v[0] for v in verts]); W = (M[:3, :3] @ P.T).T + M[:3, 3]
        info.append(dict(n=n, o=o, M=M, verts=verts, centre=(W.min(0) + W.max(0)) / 2, nv=len(verts), nt=len(o['tris'])))
    cells = {}
    for it in info: cells.setdefault(tuple(np.floor(it['centre'] / a.combine_cell).astype(int)), []).append(it)
    groups = []
    for key in sorted(cells):
        members = sorted(cells[key], key=lambda it: tuple(it['centre']))
        cur = []; v = t = 0
        for it in members:
            if cur and (v + it['nv'] > a.max_group_vertices or t + it['nt'] > a.max_group_triangles):
                groups.append(cur); cur = []; v = t = 0
            cur.append(it); v += it['nv']; t += it['nt']
        if cur: groups.append(cur)
    # Single-member groups are kept too: a reused mesh switched to collision-only must still be drawn
    # wherever it is placed, so every picked placement gets a draw-only copy.
    # Halo 3 convention in this source: an instanced piece gets its collision from child nodes named "@...".
    # A combined piece therefore gets one "@" child holding its members' collision stand-ins, moved into the
    # combined piece's space; the members and their stand-ins are emptied. Materials are untouched.
    children = {}
    for n in insts:
        if n['parent'] != -1 and n['name'].startswith('"@') and n['obj'] >= 0: children.setdefault(n['parent'], []).append(n)
    def mesh_block(oi, parts, centre):
        """parts: list of (object, world matrix). Returns object text with vertices relative to centre."""
        text = [f';###OBJECT{oi}###', '"MESH"', '""', '""', str(sum(len(o['verts']) for o, _ in parts))]
        tris = []; base = 0
        for o, M in parts:
            R = M[:3, :3]; Nm = np.linalg.inv(R).T
            for pos, nrm, rest in obj_vertices(o):
                wp = R @ pos + M[:3, 3] - centre; wn = Nm @ nrm; ln = np.linalg.norm(wn); wn = wn / ln if ln > 0 else wn
                text += ['\t'.join(map(ff, wp)), '\t'.join(map(ff, wn))] + rest + ['']
            for tl in o['tris']:
                parts_ = L[tl].split('\t'); idx = [x for x in parts_[1:] if x != '']
                tris.append(parts_[0] + '\t\t' + '\t'.join(str(int(x) + base) for x in idx))
            base += len(o['verts'])
        return text + [str(len(tris))] + tris + ['']
    IDENT = ['0.0000000000\t0.0000000000\t0.0000000000\t1.0000000000', '0.0000000000\t0.0000000000\t0.0000000000', '1.0000000000']
    new_obj_text, new_inst_text = [], []
    next_uid = max(n['uid'] for n in insts) + 1
    emptied = set(); coll_parts_total = 0
    for gi, g in enumerate(groups):
        allW = np.concatenate([((it['M'][:3, :3] @ np.array([v[0] for v in it['verts']]).T).T + it['M'][:3, 3]) for it in g])
        centre = (allW.min(0) + allW.max(0)) / 2
        lights = collections.Counter(it['n']['name'][2] for it in g if it['n']['name'][2] in '?!>')
        prefix = lights.most_common(1)[0][0] if lights else ''
        oi = nobj + len(new_obj_text)
        new_obj_text.append(mesh_block(oi, [(it['o'], it['M']) for it in g], centre))
        uid = next_uid; next_uid += 1
        new_inst_text.append([f';INSTANCE {ninst + len(new_inst_text)}', str(oi), f'"%{prefix}s3dgroup_{gi}"', str(uid), str(S['uid']), '0',
                              IDENT[0], '\t'.join(map(ff, (S_inv[:3, :3] @ centre + S_inv[:3, 3]))), IDENT[2]] + IDENT + [''])
        coll = [(objs[c['obj']], node_matrix(c)) for it in g for c in children.get(it['n']['uid'], []) if objs[c['obj']]['cls'] == '"MESH"']
        if coll:
            ci = nobj + len(new_obj_text)
            new_obj_text.append(mesh_block(ci, coll, centre)); coll_parts_total += len(coll)
            new_inst_text.append([f';INSTANCE {ninst + len(new_inst_text)}', str(ci), f'"@s3dgroup_{gi}"', str(next_uid), str(uid), '0'] + IDENT + IDENT + [''])
            next_uid += 1
        for it in g:
            emptied.add(it['n']['start'])
            for c in children.get(it['n']['uid'], []): emptied.add(c['start'])
    out = []
    j = 0
    while j < len(L):
        line = L[j]
        if j == obj_count_line: out.append(str(nobj + len(new_obj_text))); j += 1; continue
        if j == inst_count_line: out.append(str(ninst + len(new_inst_text))); j += 1; continue
        if j == objs[-1]['end']:
            for b in new_obj_text: out.extend(b)
        if j in emptied:
            # the original node keeps its place in the hierarchy but no longer carries geometry
            k = j
            while not L[k].strip() or L[k].lstrip().startswith(';'): out.append(L[k]); k += 1
            out.append('-1'); j = k + 1; continue
        out.append(line); j += 1
    while out and not out[-1].strip(): out.pop()
    out.append('')
    for b in new_inst_text: out.extend(b)
    a.out.write_text('\n'.join(out) + '\n', encoding='utf-8', errors='surrogateescape', newline='\n')
    report.update(groups=len(groups), pieces_combined=sum(len(g) for g in groups), collision_standins_moved=coll_parts_total,
                  largest_group_vertices=max(sum(it['nv'] for it in g) for g in groups),
                  groups_detail=[[gi, [it['n']['name'].strip('"') for it in g]] for gi, g in enumerate(groups)], out=str(a.out))
    if a.report: a.report.write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != 'groups_detail'}))
    sys.exit(0)

def ff(x): return f'{x:.10f}'
new_obj_text, new_inst_text = [], []
retarget = {}   # line index -> replacement (collision-only triangles)
dropped = set(); recount = {}
next_uid = max(n['uid'] for n in insts) + 1
for k, n in enumerate(pick):
    o = objs[n['obj']]
    M = S_inv @ world(by_uid[n['parent']]) @ matrix(n['local']) @ matrix(n['pivot']) if n['parent'] != -1 else S_inv @ matrix(n['local']) @ matrix(n['pivot'])
    R = M[:3, :3]; Nm = np.linalg.inv(R).T
    oi = nobj + len(new_obj_text)
    text = [f';###OBJECT{oi}###', '"MESH"', '""', '""', str(o['nv'])]
    for pl in o['verts']:
        j = pl
        while not L[j].strip(): j += 1
        pos = np.array(fl(L[j])); j += 1
        while not L[j].strip(): j += 1
        nrm = np.array(fl(L[j])); j += 1
        wp = M[:3, :3] @ pos + M[:3, 3]; wn = Nm @ nrm; ln = np.linalg.norm(wn); wn = wn / ln if ln > 0 else wn
        text += ['\t'.join(map(ff, wp)), '\t'.join(map(ff, wn))]
        # colour, influence count (0), uv count and uvs: verbatim
        while not L[j].strip(): j += 1
        text.append(L[j]); j += 1
        while not L[j].strip(): j += 1
        text.append(L[j]); j += 1           # influence count (always 0 here)
        while not L[j].strip(): j += 1
        nu = int(L[j]); text.append(L[j]); j += 1
        for _ in range(nu):
            while not L[j].strip(): j += 1
            text.append(L[j]); j += 1
        text.append('')
    text.append(str(len(o['tris'])))
    for t in o['tris']:
        parts = L[t].split('\t'); m = int(parts[0])
        text.append('\t'.join([str(render_idx[m])] + parts[1:]))
        retarget[t] = '\t'.join([str(coll_idx[m])] + parts[1:])
    text.append('')
    new_obj_text.append(text)
    new_inst_text.append([f';INSTANCE {ninst + k}', str(oi), f'"s3dmerged_{k}"', str(next_uid + k), str(S['uid']), '0',
                          '0.0000000000\t0.0000000000\t0.0000000000\t1.0000000000', '0.0000000000\t0.0000000000\t0.0000000000', '1.0000000000',
                          '0.0000000000\t0.0000000000\t0.0000000000\t1.0000000000', '0.0000000000\t0.0000000000\t0.0000000000', '1.0000000000', ''])

out = []
for j, line in enumerate(L):
    if j == mat_count_line: out.append(str(nmat + len(new_mat_text))); continue
    if j == obj_count_line: out.append(str(nobj + len(new_obj_text))); continue
    if j == inst_count_line: out.append(str(ninst + len(new_inst_text))); continue
    if j in retarget: out.append(retarget[j]); continue
    if j in dropped: continue
    if j in recount: out.append(str(recount[j])); continue
    if j == mats[-1]['end']:
        for b in new_mat_text: out.extend(b)
    if j == objs[-1]['end']:
        for b in new_obj_text: out.extend(b)
    out.append(line)
if insts[-1]['end'] >= len(L): pass
# instances go at the very end of the file
while out and not out[-1].strip(): out.pop()
out.append('')
for b in new_inst_text: out.extend(b)
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text('\n'.join(out) + '\n', encoding='utf-8', errors='surrogateescape', newline='\n')
report.update(new_materials=len(new_mat_text), new_objects=len(new_obj_text), out=str(a.out), folded=[[k, n['name'].strip('"')] for k, n in enumerate(pick)])
if a.report: a.report.write_text(json.dumps(report, indent=1))
print(json.dumps(report))
