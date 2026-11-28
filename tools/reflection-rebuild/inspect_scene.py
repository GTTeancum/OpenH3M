"""Inside Blender: report what Foundry recorded for Reflection's collision-related pieces (read only)."""
from collections import Counter
from pathlib import Path
import json, sys
import bpy
import numpy as np

OLD = Path(r'C:\X360\ISOs\H3M\.local\OpenH3M-source\work\halo4-to-h3')
OUT = Path(r'C:\Programming\GitHub\OpenH3M\.local\reflection-rebuild')
sys.path.insert(0, str(OLD / 'python-packages-313')); sys.path.insert(0, str(OLD / 'upstream/Foundry-1.9.19'))
import addon_utils
addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'reflection-reach-source.blend'))

KEYS = ('walking', 'collision', 'physics', 'sphere', 'water', 'fountain', 'structure', 'rail_zen', 'stair')


def face_modes(me):
    res = {}
    for fp in me.nwo.face_props:
        a = me.attributes.get(fp.attribute_name)
        n = len(me.polygons)
        if a is not None:
            arr = np.zeros(n, dtype=np.int8); a.data.foreach_get('value', arr); n = int(arr.sum())
        res[f'{fp.type}:{getattr(fp, "face_mode", "")}'] = n
    return res


def props(o):
    nwo = o.nwo; d = {}
    for k in ('poop_render_only', 'poop_does_not_block_aoe', 'poop_lighting', 'poop_pathfinding', 'poop_collision_type',
              'poop_excluded_from_lightprobe', 'mesh_type', 'proxy_collision', 'proxy_physics', 'proxy_cookie_cutter'):
        if hasattr(nwo, k): d[k] = str(getattr(nwo, k))
    for k in ('mesh_type', 'render_only', 'collision_only', 'sphere_collision_only'):
        if hasattr(o.data.nwo, k): d['data.' + k] = str(getattr(o.data.nwo, k))
    return d


rows = []
coll_types = Counter(); proxies = Counter()
for o in bpy.context.scene.objects:
    if o.type != 'MESH': continue
    coll_types[(props(o).get('poop_collision_type', '?'), o.data.nwo.mesh_type)] += 1
    for k in ('proxy_collision', 'proxy_physics'):
        if getattr(o.data.nwo, k, None): proxies[k] += 1
    if any(k in o.name.lower() for k in KEYS):
        rows.append(dict(name=o.name, mesh=o.data.name, polys=len(o.data.polygons), props=props(o),
                         face_modes=face_modes(o.data), parent=o.parent.name if o.parent else None,
                         children=[c.name for c in o.children][:5]))
report = dict(collision_type_by_mesh_type={f'{a} | {b}': v for (a, b), v in coll_types.items()},
              proxies=dict(proxies), pieces=rows)
(OUT / 'inspect-report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
print('INSPECT_DONE', len(rows), flush=True)
bpy.ops.wm.quit_blender()
