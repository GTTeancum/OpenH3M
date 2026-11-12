"""Compare official source placements with the saved unmodified Foundry scene."""
import json
from pathlib import Path
import sys
import bpy
import addon_utils
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/python-packages-313'))
sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/upstream/Foundry-1.9.19'))
addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
source = OUT / 'foundry-1.9.19/application/haven-source-geometry.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
from io_scene_foundry.managed_blam import import_transform

inventory = json.loads((OUT / 'haven-instance-audit.json').read_text())
havok = json.loads((OUT / 'haven-havok-audit.json').read_text())
compiled_instances = {i['source_instance_index'] for s in havok['serialized_sources'] for i in s['instances']}
objects = bpy.data.collections['wraparound_000_instances'].objects
report = dict(source=str(source.relative_to(ROOT)), scene_scale=bpy.context.scene.nwo.scale,
    forward_direction=bpy.context.scene.nwo.forward_direction, compared=[], missing=[], mismatches=[],
    scope='Instance names and transforms; not topology, materials, light fidelity or visual acceptance.')
for instance in inventory['instances']:
    fields = {k.rsplit('/', 1)[-1].split(':', 1)[-1]:v for k,v in instance['fields'].items()}
    name = fields['name']
    ob = objects.get(name)
    if ob is None:
        definition = inventory['definitions'][instance['definition_index']]
        mesh = inventory['meshes'][definition['mesh_index']]
        parts = next(v['elements'] for k,v in mesh['fields'].items() if k.endswith('/Block:parts'))
        report['missing'].append(dict(index=instance['index'], name=name, render_parts=parts,
            present_in_serialized_havok=instance['index'] in compiled_instances))
        continue
    authored = import_transform.matrix_from_axes(fields['forward'], fields['left'], fields['up'], fields['position'])
    expected = Matrix.LocRotScale(authored.translation, authored.to_quaternion(), Vector.Fill(3, fields['scale']))
    error = max(abs(expected[row][col]-ob.matrix_world[row][col]) for row in range(4) for col in range(4))
    report['compared'].append(dict(index=instance['index'], name=name, max_matrix_error=error))
    if error > 0.0002:
        report['mismatches'].append(report['compared'][-1])
report['explained_absent_records'] = all(m['render_parts']==0 and not m['present_in_serialized_havok'] for m in report['missing'])
report['pass'] = not report['mismatches'] and report['explained_absent_records'] and len(report['compared'])==len(objects)
(OUT / 'haven-instance-import-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('INSTANCE_COMPARISON',json.dumps({k:report[k] for k in ('pass','scene_scale','forward_direction','missing','mismatches')}),flush=True)
print('COMPARED',len(report['compared']),'MAX_ERROR',max(r['max_matrix_error'] for r in report['compared']),flush=True)
assert report['pass']
