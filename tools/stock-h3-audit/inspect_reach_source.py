"""Read source references through official ManagedBlam, using Foundry's API pattern.

No tag saves, binary parsing, asset conversion, or geometry generation.
"""
import json
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/hrek'
os.environ['TEMP'] = os.environ['TMP'] = str(OUT / 'temp')
sys.path.insert(0, str(OUT / 'python-packages'))
import clr
clr.AddReference(str(KIT / 'bin/ManagedBlam.dll'))
import Bungie

callback = Bungie.ManagedBlamCrashCallback(lambda info: None)
parameters = Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel = Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT), callback, parameters)
base = r'levels\dlc\cex_beaver_creek\cex_beaver_creek'
result = {}
def references(fields):
    found = []
    for field in fields:
        if isinstance(field, Bungie.Tags.TagFieldReference):
            if field.Path:
                found.append(dict(field=str(field.FieldPath), tag=str(field.Path.RelativePathWithExtension)))
        elif isinstance(field, (Bungie.Tags.TagFieldBlock, Bungie.Tags.TagFieldStruct)):
            for element in field.Elements:
                found.extend(references(element.Fields))
    return found

try:
    for extension, requests in [
        ('scenario', [('skies', 'sky'), ('structure bsps', 'structure bsp'),
                      ('effect scenery palette', 'name'), ('scenery palette', 'name')]),
        ('scenario_structure_bsp', [('materials', 'render method')]),
    ]:
        tag = Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(base, extension))
            result[extension] = {}
            for block, field in requests:
                values = []
                for element in tag.SelectField('Block:' + block).Elements:
                    path = element.SelectField(field).Path
                    values.append(str(path.RelativePathWithExtension) if path else None)
                result[extension][block] = values
        finally:
            tag.Dispose()
    result['object_references'] = {}
    for source in result['scenario']['skies'] + result['scenario']['effect scenery palette']:
        tag = Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*source.rsplit('.', 1)))
            first = tag.Fields[0]
            obj = first if first.DisplayName == 'object' else first.Elements[0].Fields[0]
            model = tag.SelectField(str(obj.FieldPath) + '/Reference:model').Path
            attachments = []
            for element in tag.SelectField(str(obj.FieldPath) + '/Block:attachments').Elements:
                path = element.Fields[0].Path
                attachments.append(str(path.RelativePathWithExtension) if path else None)
            result['object_references'][source] = dict(model=str(model.RelativePathWithExtension) if model else None,
                                                       attachments=attachments)
        finally:
            tag.Dispose()
    result['effect_references'] = {}
    for obj in result['object_references'].values():
        for source in obj['attachments']:
            if not source or not source.endswith('.effect'):
                continue
            tag = Bungie.Tags.TagFile()
            try:
                tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*source.rsplit('.', 1)))
                result['effect_references'][source] = references(tag.Fields)
            finally:
                tag.Dispose()
    result['surface_references'] = {}
    surfaces=set(result['scenario_structure_bsp']['materials'])
    sky_manifest=OUT/'original-sky-import.json'
    if sky_manifest.is_file():
        sky=json.loads(sky_manifest.read_text())
        assert hashlib.sha256(Path(sky['source']).read_bytes()).hexdigest()==sky['source_sha256']
        surfaces.update(sky['materials'])
        result['sky_materials']=sky['materials']
    for source in sorted(s for s in surfaces if s):
        if not source:
            continue
        tag = Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*source.rsplit('.', 1)))
            result['surface_references'][source] = references(tag.Fields)
        finally:
            tag.Dispose()
    (OUT / 'reach-source-references.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
finally:
    Bungie.ManagedBlamSystem.Stop()
