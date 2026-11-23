"""Report Foundry face properties, polygon sizes and duplicate faces of a mesh in an open .blend."""
import bpy, sys, json
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_env
blender_env.enable('io_scene_foundry')
name = sys.argv[sys.argv.index('--') + 1]
o = bpy.data.objects[name]; me = o.data
print('POLYS', len(me.polygons), 'sizes', dict(Counter(len(p.vertices) for p in me.polygons)))
print('TRIS_IF_TRIANGULATED', sum(len(p.vertices) - 2 for p in me.polygons))
keys = Counter(tuple(sorted(p.vertices)) for p in me.polygons)
print('DUPLICATE_FACES', sum(c - 1 for c in keys.values() if c > 1))
pos = Counter(tuple(sorted(tuple(round(c, 5) for c in me.vertices[v].co) for v in p.vertices)) for p in me.polygons)
print('DUPLICATE_BY_POSITION', sum(c - 1 for c in pos.values() if c > 1))
mats = Counter(me.materials[p.material_index].name if me.materials else None for p in me.polygons)
print('FACES_PER_MATERIAL', dict(mats))
for prop in me.nwo.face_props:
    sel = sum(bool(v.value) for v in me.attributes[prop.attribute_name].data)
    print('FACE_PROP', prop.type, {k: getattr(prop, k) for k in ('two_sided', 'face_sides_type', 'draw_distance', 'transparent', 'no_shadow', 'lightmap_only', 'precise_position') if hasattr(prop, k)}, sel, 'faces')
print('ATTRS', [(a.name, a.domain) for a in me.attributes])
