"""Verify source animation inheritance against unmodified Foundry readers.

Read-only Blender/ManagedBlam inspection. Exports original native function
bytes and their origin for later authoring; does not create shader functions.
"""
import base64
from enum import Enum
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name='Reach inherited function inspection'
project.project_path=str(KIT)
project.tags_directory=str(KIT/'tags')
project.data_directory=str(KIT/'data')
project.corinth=False
bpy.context.scene.nwo.scene_project=project.name
bpy.context.scene.nwo_export.show_output=False
from io_scene_foundry.managed_blam.shader import ShaderTag
from io_scene_foundry.managed_blam.render_method_option import RenderMethodOptionTag
from io_scene_foundry.managed_blam.connected_material import Function,AnimatedParameterType
from io_scene_foundry.managed_blam import mb_init
mb_init()
from Bungie.Tags import TagPath

setups=json.loads((OUT/'hrek-shader-setups.json').read_text())
effective=json.loads((OUT/'reach-effective-shader-options.json').read_text())
hashes={}
def tag_path(path):
    absolute=KIT/'tags'/path
    hashes.setdefault(str(absolute),hashlib.sha256(absolute.read_bytes()).hexdigest())
    return TagPath.FromPathAndExtension(*path.rsplit('.',1))
def fields(path):return {f['name']:f for f in setups[path]}
def snapshot(value):
    if isinstance(value,Enum):return value.value
    if isinstance(value,(list,tuple)):return [snapshot(v) for v in value]
    if isinstance(value,dict):return {k:snapshot(v) for k,v in value.items() if k!='editor'}
    if hasattr(value,'__dict__'):return snapshot(vars(value))
    return value

report=[]
for path in effective:
    if not fields(path)['reference'].get('value'):continue
    chain=[]
    current=path
    while current:
        assert current not in chain,'Inheritance cycle'
        chain.append(current)
        current=fields(current)['reference'].get('value')
    parameters={}
    for category in effective[path]['categories']:
        if category['tag']:
            with RenderMethodOptionTag(path=tag_path(category['tag']),tag_must_exist=True) as option:
                parameters.update(option.get_option_parameters())
    origins={}
    # Resolve which existing field supplies each function; Foundry's reader
    # independently verifies the effective function, including curve segments.
    for ancestor in reversed(chain):
        for parameter in fields(ancestor)['parameters']['elements']:
            row={f['name']:f for f in parameter}
            name=row['parameter name']['value']
            if name not in parameters:continue
            seen=set()
            for index,animation in enumerate(row['animated parameters']['elements']):
                entry={f['name']:f for f in animation}
                atype=int(entry['type']['value'])
                assert atype not in seen,(ancestor,name,atype)
                seen.add(atype)
                origins[(name,atype)]=(ancestor,index)
    functions=[]
    with ShaderTag(path=tag_path(path),tag_must_exist=True) as shader:
        for (name,atype),(origin,index) in sorted(origins.items()):
            actual=shader._value_from_parameter(parameters[name],AnimatedParameterType(atype))
            assert isinstance(actual,Function),(path,name,atype)
            with ShaderTag(path=tag_path(origin),tag_must_exist=True) as ancestor:
                parameter=next(e for e in ancestor.block_parameters.Elements if e.SelectField('parameter name').GetStringData()==name)
                animation=parameter.SelectField(ancestor.function_parameters).Elements[index]
                expected=Function()
                expected.from_element(animation,ancestor.animated_function)
                assert snapshot(actual)==snapshot(expected),(path,name,atype,origin)
                data=bytes(animation.SelectField('Struct:function/Data:data').GetData())
                functions.append(dict(parameter=name,type=atype,origin=origin,animation_index=index,
                    inherited=origin!=path,data_base64=base64.b64encode(data).decode('ascii'),
                    controls=snapshot(expected)))
    report.append(dict(source=path,chain=chain,functions=functions))
    print('INHERITED_FUNCTIONS_VERIFIED',Path(path).name,len(functions),sum(f['inherited'] for f in functions),flush=True)
for path,expected in hashes.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
(OUT/'inherited-function-inspection.json').write_text(json.dumps(dict(surfaces=report,source_hashes=hashes,
    limitation='Native function ancestry checked against unmodified Foundry; no H3 authoring or bitmap inheritance acceptance'),indent=2)+'\n')
