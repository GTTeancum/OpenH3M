"""Read H4 design geometry with the shipped API; no native tag edits."""
import json
import os
import sys
from inspect_halo4_source import ROOT, OUT, KIT, TAG_ROOT, digest

for key, suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    os.environ[key] = str(OUT / suffix)
os.chdir(KIT)
sys.path.insert(0, str(ROOT / 'work/stock-h3-audit/python-packages'))
import clr
clr.AddReference(str(KIT / 'bin/ManagedBlam.dll'))
import Corinth as Halo

def fields(element):
    result = {}
    for field in element.Fields:
        name = str(field.DisplayName)
        if isinstance(field, (Halo.Tags.TagFieldBlock, Halo.Tags.TagFieldStruct)):
            value = [fields(e) for e in field.Elements]
        elif isinstance(field, Halo.Tags.TagFieldEnum):
            value = dict(value=int(field.Value), name=str(field.Items[int(field.Value)].EnumName))
        elif hasattr(field, 'Data'):
            value = field.Data
            if hasattr(value, 'Rank'):
                value = list(value)
        elif hasattr(field, 'GetStringData'):
            value = str(field.GetStringData())
        elif hasattr(field, 'Value'):
            value = int(field.Value)
        else:
            continue
        assert name not in result, name
        result[name] = value
    return result

inventory = json.loads((OUT / 'haven-source-inventory.json').read_text())
sources = [p for p in inventory['tags'] if p.endswith('.structure_design')]
assert len(sources) == 1, sources
def manifest():
    return {str(p.relative_to(TAG_ROOT)):digest(p) for p in TAG_ROOT.rglob('*') if p.is_file()}
before = manifest()
callback = Halo.ManagedBlamCrashCallback(lambda info: print('H4_NATIVE_CRASH', str(info), flush=True))
parameters = Halo.ManagedBlamStartupParameters()
parameters.InitializationLevel = Halo.InitializationType.TagsOnly
Halo.ManagedBlamSystem.Start(str(KIT), callback, parameters)
tag = Halo.Tags.TagFile()
report = dict(source=sources[0], source_sha256=digest(TAG_ROOT / sources[0]), blocks={})
try:
    tag.Load(Halo.Tags.TagPath.FromPathAndExtension(*sources[0].rsplit('.', 1)))
    for name in ('soft ceilings block','water groups block','water instances block'):
        block = tag.SelectField('Struct:physics[0]/Block:' + name)
        if block is not None:
            report['blocks'][name] = [fields(e) for e in block.Elements]
finally:
    tag.Dispose()
    Halo.ManagedBlamSystem.Stop()
    assert manifest() == before
report['source_tags_unchanged'] = True
(OUT / 'haven-source-design.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('H4_DESIGN_READ', report['source'], {k:len(v) for k,v in report['blocks'].items()}, flush=True)
