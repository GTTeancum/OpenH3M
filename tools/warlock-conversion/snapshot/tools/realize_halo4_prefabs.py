"""Realize source prefab placements with Blender; verify without rebuilding meshes."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import OUT, SOURCE, setup, sha, stored


def fingerprint(mesh):
    """Read source geometry and metadata solely for before/after verification."""
    digest = hashlib.sha256()
    def add(value):
        digest.update(repr(value).encode('utf-8'))
        digest.update(b'\n')
    add(stored(mesh.nwo))
    add([stored(p) for p in mesh.nwo.face_props])
    add([m.name if m else None for m in mesh.materials])
    for vertex in mesh.vertices:
        add(tuple(vertex.co))
    for edge in mesh.edges:
        add(tuple(edge.vertices))
    for polygon in mesh.polygons:
        add((tuple(polygon.vertices), polygon.material_index, polygon.use_smooth))
    for normal in mesh.corner_normals:
        add(tuple(normal.vector))
    for attribute in mesh.attributes:
        add((attribute.name, attribute.domain, attribute.data_type))
        for item in attribute.data:
            for name in ('value', 'vector', 'color'):
                if hasattr(item, name):
                    value = getattr(item, name)
                    add(tuple(value) if hasattr(value, '__iter__') and not isinstance(value, str) else value)
                    break
    return digest.hexdigest()


source_hash = sha(SOURCE)
scene = setup(exporter=True)
original_objects = set(scene.objects)
prefabs = [o for o in scene.objects if o.instance_type == 'COLLECTION' and o.instance_collection]
expected = []
for instance in bpy.context.evaluated_depsgraph_get().object_instances:
    if instance.is_instance:
        obj = instance.object.original
        assert obj.type == 'MESH', (obj.name, obj.type)
        expected.append(dict(parent=instance.parent.original.name, source=obj.name,
            mesh=obj.data, matrix=instance.matrix_world.copy(), metadata=stored(obj.nwo)))
assert len(prefabs) == 25 and len(expected) == 62
meshes = {row['mesh'] for row in expected}
before = {mesh: fingerprint(mesh) for mesh in meshes}
bpy.ops.object.select_all(action='DESELECT')
for obj in prefabs:
    obj.select_set(True)
bpy.context.view_layer.objects.active = prefabs[0]
result = bpy.ops.object.duplicates_make_real(use_base_parent=False, use_hierarchy=True)
assert result == {'FINISHED'}
bpy.context.view_layer.update()
created = set(scene.objects) - original_objects
assert len(created) == len(expected) and all(o.type == 'MESH' for o in created)
unmatched = list(created)
matches = []
maximum_error = 0.0
for row in expected:
    choices = [o for o in unmatched if o.data == row['mesh']]
    assert choices, row['source']
    def error(obj):
        return max(abs(obj.matrix_world[r][c] - row['matrix'][r][c]) for r in range(4) for c in range(4))
    obj = min(choices, key=error)
    difference = error(obj)
    assert difference < 0.0001, (obj.name, difference)
    assert stored(obj.nwo) == row['metadata'], obj.name
    maximum_error = max(maximum_error, difference)
    unmatched.remove(obj)
    matches.append(dict(prefab=row['parent'], source_object=row['source'], realized_object=obj.name,
        mesh=obj.data.name, shared_mesh_data=True, matrix_error=difference))
assert not unmatched
assert all(fingerprint(mesh) == before[mesh] for mesh in meshes)
remaining_instances = [i for i in bpy.context.evaluated_depsgraph_get().object_instances if i.is_instance]
assert not remaining_instances, len(remaining_instances)
assert sha(SOURCE) == source_hash
destination = OUT / 'h3-authoring/haven-prefabs-realized.blend'
destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
report = dict(status='verified', operation='bpy.ops.object.duplicates_make_real',
    source=str(SOURCE), source_sha256=source_hash, source_unchanged=True,
    destination=str(destination), destination_sha256=sha(destination),
    prefab_placements=len(prefabs), realized_mesh_objects=len(created),
    realized_types=dict(Counter(o.data.nwo.mesh_type for o in created)),
    unique_prefab_meshes=len(meshes), mesh_geometry_and_metadata_unchanged=True,
    maximum_matrix_error=maximum_error, all_object_metadata_unchanged=True,
    remaining_collection_instances=0, scene_objects=len(scene.objects),
    mesh_fingerprints={m.name: value for m, value in before.items()}, matches=matches,
    pending=['H3 collision-category mapping', 'H3 material and face authoring',
             'Coordinate conversion', 'H3 export/compile', 'Source appearance verification'])
(OUT / 'haven-prefab-realization.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('H4_PREFABS_REALIZED', json.dumps({k:v for k,v in report.items() if k not in ('matches','mesh_fingerprints')}), flush=True)
