"""Read shader authoring fields with each game's official ManagedBlam API.

One kit per process. Does not copy, save, translate, or generate any shader.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
parser = argparse.ArgumentParser()
parser.add_argument('game', choices=('hrek',), help='H3 uses export_shader_donors.ps1; its ManagedBlam Start is unimplemented.')
args = parser.parse_args()
kit = ROOT / 'work/editing-kits' / args.game
os.environ['TEMP'] = os.environ['TMP'] = str(OUT / 'temp')
sys.path.insert(0, str(OUT / 'python-packages'))
import clr
clr.AddReference(str(kit / 'bin/ManagedBlam.dll'))
import Bungie

def fields_to_data(fields):
    rows = []
    for field in fields:
        row = dict(name=str(field.DisplayName), field=str(field.FieldPath), type=str(field.GetType().Name))
        if isinstance(field, Bungie.Tags.TagFieldReference):
            row['value'] = str(field.Path.RelativePathWithExtension) if field.Path else None
        elif isinstance(field, (Bungie.Tags.TagFieldBlock, Bungie.Tags.TagFieldStruct)):
            row['elements'] = [fields_to_data(e.Fields) for e in field.Elements]
        elif isinstance(field, Bungie.Tags.TagFieldData):
            row['bytes'] = int(field.ByteCount)
            row['data_base64'] = base64.b64encode(bytes(field.GetData())).decode('ascii')
        elif hasattr(field, 'GetStringData'):
            row['value'] = str(field.GetStringData())
        elif hasattr(field, 'Value'):
            row['value'] = str(field.Value)
        rows.append(row)
    return rows

paths = sorted(json.loads((OUT / 'reach-source-references.json').read_text())['surface_references'])
callback = Bungie.ManagedBlamCrashCallback(lambda info: None)
parameters = Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel = Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(kit), callback, parameters)
result = {}
try:
    for path in paths:
        tag = Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*path.rsplit('.', 1)))
            method = tag.SelectField('Struct:render_method').Elements[0]
            result[path] = fields_to_data(method.Fields)
            reference = method.SelectField('reference').Path
            if reference:
                inherited_path = str(reference.RelativePathWithExtension)
                if inherited_path not in paths:
                    paths.append(inherited_path)
        finally:
            tag.Dispose()
    target = OUT / (args.game + '-shader-setups.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print('SHADER_SETUP_INSPECTION', args.game, len(result), str(target), flush=True)
finally:
    Bungie.ManagedBlamSystem.Stop()
