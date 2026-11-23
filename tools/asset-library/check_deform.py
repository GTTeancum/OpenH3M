"""In a rigged .blend: per vertex group, how far the armature moves vertices from their stored positions."""
import bpy, sys
from collections import defaultdict
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.startswith('#'))
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg).to_mesh()
names = {g.index: g.name for g in obj.vertex_groups}
worst = defaultdict(float); count = defaultdict(int)
for v, e in zip(obj.data.vertices, ev.vertices):
    d = (v.co - e.co).length
    g = max(v.groups, key=lambda x: x.weight).group if v.groups else -1
    worst[names.get(g, 'none')] = max(worst[names.get(g, 'none')], d); count[names.get(g, 'none')] += 1
print('DEFORM', {k: (count[k], round(worst[k], 4)) for k in worst})
arm = obj.parent
for b in arm.pose.bones:
    print('BONE', b.name, 'pose==rest', (b.matrix - arm.data.bones[b.name].matrix_local).to_3x3().is_zero if hasattr((b.matrix - arm.data.bones[b.name].matrix_local).to_3x3(), 'is_zero') else [round(x, 4) for r in (b.matrix - arm.data.bones[b.name].matrix_local) for x in r])
