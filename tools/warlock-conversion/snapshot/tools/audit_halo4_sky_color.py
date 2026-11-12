"""Read imported sky color values and node wiring; never alter/save the scene.

Use Blender's existing semantic API only. The official shader source is the
reference for color-channel semantics; this report is not an H3 acceptance.
"""
from collections import Counter
from pathlib import Path
import json
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import OUT, SOURCE, setup, sha

before = sha(SOURCE)
scene = setup()
sky = scene.objects['default:default']
mesh = sky.data
attribute = mesh.color_attributes['Color']
assert attribute.domain == 'POINT' and attribute.data_type == 'FLOAT_COLOR'

def values(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)

def statistics(colors):
    return dict(count=len(colors), channels=[dict(min=min(c[i] for c in colors),
        max=max(c[i] for c in colors), distinct=len({c[i] for c in colors}))
        for i in range(4)], nonidentity_alpha=sum(c[3] != 1 for c in colors),
        nongreyscale=sum(max(c[:3])-min(c[:3]) > 1e-6 for c in colors))

trees = {}
def inspect_tree(tree, key):
    if key in trees:
        return
    row = dict(nodes=[], links=[])
    trees[key] = row
    for node in tree.nodes:
        settings = {}
        for key in ('operation', 'data_type', 'attribute_name', 'attribute_type',
                    'layer_name', 'blend_type', 'mode'):
            if hasattr(node, key):
                settings[key] = values(getattr(node, key))
        row['nodes'].append(dict(name=node.name, type=node.bl_idname,
            group=node.node_tree.name if node.type == 'GROUP' and node.node_tree else None,
            settings=settings,
            inputs=[dict(name=s.name, identifier=s.identifier, linked=s.is_linked,
                         value=values(getattr(s, 'default_value', None))) for s in node.inputs],
            outputs=[dict(name=s.name, identifier=s.identifier) for s in node.outputs]))
        if node.type == 'GROUP' and node.node_tree:
            inspect_tree(node.node_tree, 'group:'+node.node_tree.name)
    for link in tree.links:
        row['links'].append(dict(source_node=link.from_node.name,
            source_socket=link.from_socket.name, source_identifier=link.from_socket.identifier,
            target_node=link.to_node.name, target_socket=link.to_socket.name,
            target_identifier=link.to_socket.identifier))

material_rows = []
for index, material in enumerate(mesh.materials):
    polygons = [p for p in mesh.polygons if p.material_index == index]
    if not polygons:
        continue
    indices = sorted({i for p in polygons for i in p.vertices})
    colors = [tuple(attribute.data[i].color) for i in indices]
    material_rows.append(dict(material=material.name,
        source=material.nwo.shader_path.replace('\\', '/'), polygons=len(polygons),
        color=statistics(colors), node_tree='material:'+material.name))
    inspect_tree(material.node_tree, 'material:'+material.name)

report = dict(status='read_only_inventory_complete', source_blend_sha256=before,
    source_blend_unchanged=sha(SOURCE) == before, object=sky.name, vertices=len(mesh.vertices),
    polygons=len(mesh.polygons), color_attribute=dict(name=attribute.name,
        domain=attribute.domain, type=attribute.data_type), materials=material_rows,
    node_trees=trees,
    scope='Imported RGB/alpha values and node wiring, without shader execution or native H3 appearance validation.')
assert report['source_blend_unchanged']
(OUT/'haven-sky-color-audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('H4_SKY_COLOR_AUDIT', json.dumps(dict(vertices=report['vertices'],
    polygons=report['polygons'], materials=material_rows,
    node_types=dict(Counter(n['type'] for t in trees.values() for n in t['nodes'])),
    source_blend_unchanged=True)), flush=True)
