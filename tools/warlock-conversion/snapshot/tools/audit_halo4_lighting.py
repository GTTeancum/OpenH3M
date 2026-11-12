"""Read source H4 lights and atmosphere through official tag fields only."""
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

def value(field):
    if str(field.GetType()).endswith('TagFieldCustomFunctionEditor'):
        editor=field.Value
        result={'editor_type':str(editor.GetType())}
        for name in ('ClampRangeMin','ClampRangeMax','MasterType','IsRanged','PeriodicFunction','TimePeriod'):
            try: result[name]=str(getattr(editor,name))
            except AttributeError: pass
        return result
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

sources=json.loads((OUT/'haven-source-inventory.json').read_text())
selected=[p for p in sources['tags'] if any(p.endswith('.'+ext) for ext in ('scenario_structure_lighting_info','atmosphere_fog','atmosphere_globals','camera_fx_settings'))]
sky_only='--sky' in sys.argv
if sky_only:
    selected=['environments/shared/skies/wraparound_sky/wraparound_sky_new/wraparound_sky_new.scenario_structure_lighting_info']
callback=Halo.ManagedBlamCrashCallback(lambda info: print('H4_NATIVE_CRASH',str(info),flush=True))
params=Halo.ManagedBlamStartupParameters();params.InitializationLevel=Halo.InitializationType.TagsOnly
Halo.ManagedBlamSystem.Start(str(KIT),callback,params)
report={'api':'Official Corinth.ManagedBlam','tags':{},'source_tags_unchanged':False}
try:
    for relative in selected:
        path=TAG_ROOT/relative;before=digest(path);tag=Halo.Tags.TagFile()
        try:
            tag.Load(Halo.Tags.TagPath.FromPathAndExtension(*relative.rsplit('.',1)))
            fields={str(f.FieldPath):value(f) for f in tag.Fields}
            report['tags'][relative]={'sha256':before,'fields':fields}
            print('LIGHTING_SOURCE_READ',relative,len(fields),flush=True)
        finally: tag.Dispose()
        assert digest(path)==before
        if relative in sources['tags']:assert before==sources['tags'][relative]['sha256']
    report['source_tags_unchanged']=True
finally:
    Halo.ManagedBlamSystem.Stop()
    (OUT/('haven-sky-lighting-source.json' if sky_only else 'haven-lighting-source.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
