"""Audit H4 material inputs with unmodified Foundry and official tag fields."""
from collections import Counter
from pathlib import Path
import json
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import OUT, KIT, SOURCE, setup, sha

source_hash = sha(SOURCE)
scene = setup()
from io_scene_foundry.managed_blam import mb_init
from io_scene_foundry.managed_blam.material import MaterialTag, MaterialParameter
from io_scene_foundry.managed_blam.material_shader import MaterialShaderTag
mb_init()
from Corinth.Tags import TagPath

def manifest():
    return {str(p.relative_to(KIT/'tags')):sha(p) for p in (KIT/'tags').rglob('*') if p.is_file()}
def serialize(value):
    if value is None or isinstance(value, (str,int,float,bool)):
        return value
    if hasattr(value, 'RelativePathWithExtension'):
        return str(value.RelativePathWithExtension).replace('\\','/')
    try:
        return [serialize(v) for v in value]
    except TypeError:
        return str(value)

before = manifest()
report = dict(status='running', source_blend_sha256=source_hash, materials={})
try:
    for material in bpy.data.materials:
        relative = material.nwo.shader_path.replace('\\','/')
        if not relative.endswith('.material'):
            continue
        groups = []
        if material.node_tree:
            for node in material.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    groups.append(dict(name=node.name, group=node.node_tree.name,
                        inputs={socket.name:dict(value=serialize(getattr(socket,'default_value',None)),
                            linked=socket.is_linked, links=[dict(node=link.from_node.name, socket=link.from_socket.name) for link in socket.links])
                            for socket in node.inputs}))
        with MaterialTag(path=TagPath.FromPathAndExtension(*relative.rsplit('.',1)), tag_must_exist=True) as tag:
            shader_path = tag.reference_material_shader.Path
            assert shader_path is not None, relative
            with MaterialShaderTag(path=shader_path, tag_must_exist=True) as shader:
                defaults = shader.get_defaults()
            values = {name:dict(type=parameter.type_name, display_name=parameter.ui_name,
                default=serialize(parameter.default), effective_static=serialize(parameter.default), authored=False)
                for name,parameter in defaults.items()}
            unknown = []
            for element in tag.block_parameters.Elements:
                name = element.Fields[0].GetStringData()
                if name not in defaults:
                    unknown.append(name)
                    continue
                parameter = MaterialParameter(defaults[name])
                parameter.from_element(element)
                functions = element.SelectField('Block:function parameters')
                values[name].update(authored=True, effective_static=serialize(parameter.default),
                    function_count=int(functions.Elements.Count) if functions is not None else 0)
            blend = str(tag.alpha_blend_mode.Items[int(tag.alpha_blend_mode.Value)].EnumName)
            physics = tag.get_global_material()
        imported_blends = [g['inputs']['blend mode']['value'] for g in groups if 'blend mode' in g['inputs']]
        report['materials'][relative] = dict(blender_material=material.name,
            material_shader=serialize(shader_path), source_sha256=sha(KIT/'tags'/relative),
            physics_material=physics, alpha_blend_mode=blend, imported_blend_modes=imported_blends,
            imported_blends_match_source=bool(imported_blends) and all(v==blend for v in imported_blends),
            parameters=values, unrecognized_authored_parameters=unknown, node_groups=groups)
    report['status'] = 'complete'
finally:
    report['source_tags_unchanged'] = manifest() == before
    report['source_blend_unchanged'] = sha(SOURCE) == source_hash
    report['scope'] = 'Source definitions, authored/static values and imported node input inventory. Function evaluation, H4 renderer equivalence and H3 mapping remain unverified.'
    (OUT/'haven-material-input-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert report['source_tags_unchanged'] and report['source_blend_unchanged']
rows = report['materials']
print('H4_MATERIAL_AUDIT',json.dumps(dict(materials=len(rows),
    shader_families=dict(Counter(v['material_shader'] for v in rows.values())),
    source_tags_unchanged=True,
    blend_mismatches=[k for k,v in rows.items() if not v['imported_blends_match_source']])) ,flush=True)
