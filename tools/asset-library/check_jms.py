"""Read a JMS back with the unchanged General-101 importer and report faces, tiny/degenerate faces and bounds."""
import bpy, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_env
blender_env.enable('io_scene_halo')
jms = sys.argv[sys.argv.index('--') + 1]
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
print('IMPORT', bpy.ops.import_scene.jms(filepath=jms), [o.name for o in bpy.context.scene.objects][:10], flush=True)
for o in bpy.context.scene.objects:
    if o.type != 'MESH' or o.name.startswith('#'): continue
    me = o.data
    areas = [p.area for p in me.polygons]
    print('MESH', o.name, 'faces', len(me.polygons), 'verts', len(me.vertices),
          'area<1e-6', sum(a < 1e-6 for a in areas), 'area<1e-4', sum(a < 1e-4 for a in areas),
          'mats', dict(Counter(me.materials[p.material_index].name for p in me.polygons)))
    vs = [v.co for v in me.vertices]
    print('BOUNDS', [round(min(v[k] for v in vs), 3) for k in range(3)], [round(max(v[k] for v in vs), 3) for k in range(3)])
    loose = Counter(tuple(round(c, 3) for c in v.co) for v in me.vertices)
    print('COINCIDENT_VERTEX_POSITIONS(0.001)', sum(c - 1 for c in loose.values() if c > 1))
