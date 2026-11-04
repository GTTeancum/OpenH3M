"""Read source references through official ManagedBlam, using Foundry's API pattern.

No tag saves, binary parsing, asset conversion, or geometry generation.
"""
import json
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
try:
    for extension, requests in [
        ('scenario', [('skies', 'sky'), ('structure bsps', 'structure bsp')]),
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
    (OUT / 'reach-source-references.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
finally:
    Bungie.ManagedBlamSystem.Stop()
