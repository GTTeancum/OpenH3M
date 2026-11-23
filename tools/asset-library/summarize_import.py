"""Summarize a foundry_import.py JSON report: bones, meshes by type, markers."""
import json, sys
from collections import Counter, defaultdict
r = json.load(open(sys.argv[1]))
objs = r['objects']
for o in objs:
    if o['type'] == 'ARMATURE':
        print('ARMATURE', o['name'], len(o['bones']), 'bones')
        for b in o['bones']:
            print('   BONE', b['name'], '<-', b['parent'], [round(b['matrix'][i][3], 3) for i in range(3)])
meshes = [o for o in objs if o['type'] == 'MESH']
by = defaultdict(list)
for m in meshes: by[m['mesh_type']].append(m)
for t, ms in by.items():
    print('MESHTYPE', t, len(ms), 'objects', sum(m['faces'] for m in ms), 'faces')
    for m in ms[:60]:
        print('    ', m['name'], m['faces'], 'faces', 'groups', m['groups'][:6], 'parent_bone', m['parent_bone'])
markers = Counter(o['name'].split('.')[0] for o in objs if o['type'] == 'EMPTY')
print('MARKERS', dict(markers))
print('ACTIONS', len(r['actions']))
