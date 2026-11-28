import json, sys, collections, math
def f(v):
    try: return float(v.split('|')[0].split(',')[-1])
    except: return None
def analyze(m):
    d = json.load(open(f'{m}.json'))['data']
    cl = d['clusters']; me = d['meshes']; inst = d['instanced geometry instances']; defs = d['instanced geometries definitions']
    r = {'map': m, 'clusters': len(cl), 'portals': len(d.get('cluster portals', [])), 'materials': len(d.get('materials', [])),
         'meshes': len(me), 'inst_defs': len(defs), 'instances': len(inst)}
    def mesh_stats(i):
        x = me[i]; parts = x.get('@parts', [])
        idx = sum(int(p['index count']) for p in parts)
        return len(parts), x.get('#subparts', 0), idx, x.get('#instance buckets', 0), x.get('index buffer type'), x.get('mesh flags')
    cm = [int(c['mesh index']) for c in cl]
    cp = [mesh_stats(i) for i in cm if i >= 0]
    r['cluster_parts_total'] = sum(p[0] for p in cp); r['cluster_parts_max'] = max(p[0] for p in cp)
    r['cluster_tris'] = sum(p[2] for p in cp)//3  # approx: strips differ
    r['cluster_ibtype'] = collections.Counter(p[4] for p in cp)
    # instances
    dm = [int(x.get('mesh index', -1)) for x in defs]
    used = collections.Counter(int(x['instance definition'].split(',')[-1]) for x in inst)
    r['defs_used'] = len(used); r['placements_per_def_max'] = max(used.values()) if used else 0
    r['defs_multi_placed'] = sum(1 for v in used.values() if v > 1)
    tparts = 0; ttris = 0; buckets = 0
    for di, n in used.items():
        mi = dm[di]
        if mi < 0: continue
        s = mesh_stats(mi); tparts += s[0]*n; ttris += s[2]//3*n
    r['inst_parts_drawn_if_all'] = tparts; r['inst_tris_all'] = ttris
    r['meshes_with_buckets'] = sum(1 for x in me if x.get('#instance buckets', 0) > 0)
    r['lm_policy'] = collections.Counter(x.get('lightmapping policy') for x in inst)
    r['inst_flags'] = collections.Counter(x.get('flags','').split('|')[-1] for x in inst)
    r['fade_set'] = sum(1 for x in inst if x.get('fade pixels start') not in ('0', None) or x.get('fade pixels end') not in ('0', None))
    r['name_prefix'] = collections.Counter((x['_name'] or ' ')[0] for x in inst)
    r['portal_flags'] = collections.Counter(p.get('flags') for p in d.get('cluster portals', []))
    r['cluster_flags'] = collections.Counter(c.get('flags') for c in cl)
    rad = sorted(f(x['world bounding sphere radius']) for x in inst); r['inst_radius_median'] = rad[len(rad)//2] if rad else None
    r['def_keys'] = [k for k in defs[0].keys()] if defs else []
    return r
for m in sys.argv[1:]:
    print(json.dumps(analyze(m), default=str))
