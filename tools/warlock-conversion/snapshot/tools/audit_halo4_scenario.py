"""Inventory authored H4 scenario placements through official tag fields only."""
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

BLOCKS = ('object names', 'scenery', 'scenery palette', 'bipeds', 'biped palette',
    'vehicles', 'vehicle palette', 'equipment', 'equipment palette', 'weapons',
    'weapon palette', 'machines', 'machine palette', 'controls', 'control palette',
    'sound scenery', 'sound scenery palette', 'effect scenery', 'effect scenery palette',
    'crates', 'crate palette', 'player starting profile', 'player starting locations',
    'trigger volumes', 'named location volumes', 'scenario kill triggers',
    'scenario safe zone triggers', 'spawn data', 'acoustics palette', 'acoustic sectors',
    'map variant palettes', 'Drop sets')

def manifest():
    return {str(p.relative_to(TAG_ROOT)):digest(p) for p in TAG_ROOT.rglob('*') if p.is_file()}

def value(field):
    if isinstance(field, Halo.Tags.TagFieldReference):
        return str(field.Path.RelativePathWithExtension).replace('\\', '/') if field.Path else None
    if isinstance(field, Halo.Tags.TagFieldFlags):
        return {'raw_value':int(field.RawValue),
            'set_flags':[str(item.FlagName) for item in field.Items if field.TestBit(str(item.FlagName))]}
    if isinstance(field, Halo.Tags.TagFieldEnum):
        index = int(field.Value)
        items = list(field.Items)
        return {'value':index, 'name':str(items[index].EnumName) if 0 <= index < len(items) else None}
    if isinstance(field, (Halo.Tags.TagFieldStruct, Halo.Tags.TagFieldBlock)):
        return [{str(f.FieldPath): value(f) for f in e.Fields} for e in field.Elements]
    for property_name in ('Data', 'Value'):
        try:
            data = getattr(field, property_name)
            if data is None or isinstance(data, (str, bool, int, float)):
                return data
            if hasattr(data, 'Rank'):
                return list(data)
        except (AttributeError, TypeError):
            pass
    try:
        return {'string_data':str(field.GetStringData())}
    except (AttributeError, TypeError):
        return {'field_type':str(field.GetType()), 'value_not_read':True}

sources = json.loads((OUT / 'haven-source-inventory.json').read_text())
scenarios = [p for p in sources['tags'] if p.endswith('.scenario')]
before = manifest()
callback = Halo.ManagedBlamCrashCallback(lambda info: print('H4_NATIVE_CRASH', str(info), flush=True))
params = Halo.ManagedBlamStartupParameters()
params.InitializationLevel = Halo.InitializationType.TagsOnly
Halo.ManagedBlamSystem.Start(str(KIT), callback, params)
report = {'api':'Official Corinth.ManagedBlam', 'scope':'Authored placement/role inventory; no conversion or tag edits.', 'status':'running', 'scenarios':{}}
try:
    for relative in scenarios:
        tag = Halo.Tags.TagFile()
        try:
            tag.Load(Halo.Tags.TagPath.FromPathAndExtension(*relative.rsplit('.',1)))
            selected = {}
            for name in BLOCKS:
                field = tag.SelectField('Block:' + name)
                if field is not None and field.Elements.Count:
                    selected[name] = value(field)
            report['scenarios'][relative] = selected
            print('SCENARIO',relative,{k:len(v) for k,v in selected.items()},flush=True)
        finally:
            tag.Dispose()
    report['status'] = 'complete'
except BaseException as error:
    report.update(status='failed', error=repr(error))
    raise
finally:
    Halo.ManagedBlamSystem.Stop()
    report['source_tags_unchanged'] = manifest() == before
    (OUT / 'haven-scenario-authoring-inventory.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert report['source_tags_unchanged']
