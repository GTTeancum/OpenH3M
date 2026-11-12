"""Read H4 instance/mesh evidence through official ManagedBlam, without edits."""
from collections import Counter
import json
import os
import sys
from inspect_halo4_source import ROOT, OUT, KIT, TAG_ROOT, digest

for key, suffix in [('TEMP', 'temp'), ('TMP', 'temp'), ('APPDATA', 'profile/roaming'),
                    ('LOCALAPPDATA', 'profile/local')]:
    os.environ[key] = str(OUT / suffix)
os.chdir(KIT)
sys.path.insert(0, str(ROOT / 'work/stock-h3-audit/python-packages'))
import clr
clr.AddReference(str(KIT / 'bin/ManagedBlam.dll'))
import Corinth as Halo

def manifest():
    return {str(p.relative_to(TAG_ROOT)): digest(p) for p in TAG_ROOT.rglob('*') if p.is_file()}

def fields(element):
    result = {}
    for field in element.Fields:
        path = str(field.FieldPath)
        if isinstance(field, (Halo.Tags.TagFieldBlock, Halo.Tags.TagFieldStruct)):
            result[path] = {'elements': int(field.Elements.Count)}
        else:
            try:
                value = field.Data
                result[path] = (value if isinstance(value, (str, bool, int, float)) else
                    list(value) if str(type(value)).startswith("<class 'System.") and hasattr(value, 'Rank')
                    else str(value))
            except Exception:
                result[path] = {'type': str(field.GetType())}
    return result

before = manifest()
callback = Halo.ManagedBlamCrashCallback(lambda info: print('H4_NATIVE_CRASH', str(info), flush=True))
params = Halo.ManagedBlamStartupParameters()
params.InitializationLevel = Halo.InitializationType.TagsOnly
Halo.ManagedBlamSystem.Start(str(KIT), callback, params)
tag = Halo.Tags.TagFile()
report = {'scope': 'Official API instance and mesh inventory; no asset decoding or modification.'}
try:
    tag.Load(Halo.Tags.TagPath.FromPathAndExtension('levels/multi/wraparound/wraparound_000', 'scenario_structure_bsp'))
    definitions = tag.SelectField('Struct:resource interface[0]/Block:raw_resources[0]/Struct:raw_items[0]/Block:instanced geometries definitions')
    meshes = tag.SelectField('Struct:render geometry[0]/Block:meshes')
    instances = tag.SelectField('instanced geometry instances')
    report['definitions'] = [dict(index=int(e.ElementIndex), fields=fields(e),
        mesh_index=int(e.SelectField('mesh index').Data)) for e in definitions.Elements]
    report['meshes'] = [dict(index=int(e.ElementIndex), fields=fields(e)) for e in meshes.Elements]
    report['instances'] = [dict(index=int(e.ElementIndex), fields=fields(e),
        definition_index=int(e.SelectField('ShortInteger:mesh_index').Data)) for e in instances.Elements]
    report['definition_use_counts'] = dict(Counter(e['definition_index'] for e in report['instances']))
finally:
    tag.Dispose()
    Halo.ManagedBlamSystem.Stop()
    after = manifest()
    report['source_tags_unchanged'] = before == after
    assert before == after, 'Official read changed tag inputs'
    (OUT / 'haven-instance-audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('INSTANCE_AUDIT_OK', {k:len(report[k]) for k in ('definitions','meshes','instances')}, flush=True)
