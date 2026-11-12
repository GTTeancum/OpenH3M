"""Read H4 material functions through unchanged Foundry and the official editor.

This is an inventory, not a function decoder, shader converter or tag writer.
"""
from collections import Counter
from enum import Enum
from pathlib import Path
import base64
import json
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import OUT, KIT, SOURCE, setup, sha

source_hash = sha(SOURCE)
setup()
from io_scene_foundry.managed_blam import mb_init
from io_scene_foundry.managed_blam.material import MaterialTag
from io_scene_foundry.managed_blam.connected_material import Function
mb_init()
from Corinth.Tags import TagPath

def serialize(value):
    if isinstance(value, Enum):
        return value.name
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if hasattr(value, '__dict__'):
        return {k:serialize(v) for k,v in vars(value).items() if k != 'editor'}
    raise TypeError(type(value).__name__)

def manifest():
    return {str(p.relative_to(KIT/'tags')):sha(p) for p in (KIT/'tags').rglob('*') if p.is_file()}

inputs = json.loads((OUT/'haven-material-input-audit.json').read_text())
before = manifest()
report = dict(status='running', materials={}, errors=[], source_blend_sha256=source_hash)
try:
    for relative, material in inputs['materials'].items():
        records = {}
        with MaterialTag(path=TagPath.FromPathAndExtension(*relative.rsplit('.',1)), tag_must_exist=True) as tag:
            for parameter in tag.block_parameters.Elements:
                name = parameter.Fields[0].GetStringData()
                if name not in material['parameters']:
                    continue
                block = parameter.SelectField('Block:function parameters')
                if block is None or not block.Elements.Count:
                    continue
                functions = []
                for index, element in enumerate(block.Elements):
                    try:
                        function = Function()
                        function.from_element(element, 'function')
                        result = serialize(function)
                        # Preserve original input separately: Foundry substitutes "one"
                        # for absent input while building its Blender nodes.
                        result['source_input'] = element.SelectField('input name').GetStringData()
                        result['source_type'] = str(element.Fields[0].Items[element.Fields[0].Value].EnumName)
                        data = element.SelectField('Struct:function/Data:data')
                        if data is not None:
                            result['data_base64'] = base64.b64encode(bytes(data.GetData())).decode('ascii')
                        else:
                            result['field_schema'] = [dict(path=str(field.FieldPath),type=str(field.GetType())) for field in element.Fields]
                        if function.is_basic_function and not function.is_ranged:
                            result['constant'] = (list(function.colors[0]) if function.is_color else function.clamp_min)
                        elif not function.is_color:
                            result['native_scalar_samples'] = [dict(input=x, range=r,
                                value=float(function.editor.Evaluate(x, r)))
                                for r in (0.0,1.0) for x in [i/64 for i in range(65)]]
                        functions.append(result)
                    except Exception as error:
                        report['errors'].append(dict(material=relative, parameter=name,index=index,error=repr(error)))
                records[name] = functions
        report['materials'][relative] = records
    functions = [f for m in report['materials'].values() for rows in m.values() for f in rows]
    report['summary'] = dict(materials=len(report['materials']), functions=len(functions),
        master_types=dict(Counter(f['master_type'] for f in functions)),
        animated_types=dict(Counter(f['animated_type'] for f in functions)),
        constant_functions=sum('constant' in f for f in functions),
        ranged_functions=sum(f['is_ranged'] for f in functions))
    report['status'] = 'complete' if not report['errors'] else 'incomplete'
finally:
    report['source_tags_unchanged'] = before == manifest()
    report['source_blend_unchanged'] = source_hash == sha(SOURCE)
    report['scope'] = ('Recognized source material functions read using unmodified Foundry 1.9.19 and '
        'Corinth.ManagedBlam. Scalar samples use the official function editor. '
        'No binary decoding, H3 mapping, tag writes or appearance acceptance.')
    (OUT/'haven-material-function-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert report['source_tags_unchanged'] and report['source_blend_unchanged']
print('H4_MATERIAL_FUNCTION_AUDIT',json.dumps(report.get('summary',{})),flush=True)
assert report['status'] == 'complete', report['errors'][:3]
