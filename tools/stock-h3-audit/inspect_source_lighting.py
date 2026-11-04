"""Read original Reach material lighting through official ManagedBlam only."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/hrek'
sys.path.insert(0, str(OUT / 'python-packages'))
import clr
clr.AddReference(str(KIT / 'bin/ManagedBlam.dll'))
import Bungie

callback = Bungie.ManagedBlamCrashCallback(lambda info: None)
parameters = Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel = Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT), callback, parameters)
base = r'levels\dlc\cex_beaver_creek\cex_beaver_creek'
report = {}
try:
    for extension, block in [('scenario_structure_bsp', 'materials'),
                             ('scenario_structure_lighting_info', 'material info')]:
        path = KIT / 'tags' / (base + '.' + extension)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        tag = Bungie.Tags.TagFile()
        rows = []
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(base, extension))
            for element in tag.SelectField('Block:' + block).Elements:
                if extension == 'scenario_structure_bsp':
                    shader = element.SelectField('render method').Path
                    rows.append(dict(index=int(element.ElementIndex), shader=shader.RelativePathWithExtension,
                        emission_index=int(element.SelectField('imported material index').Data),
                        lightmap_resolution=float(element.SelectField('Real:lightmap resolution scale').Data)))
                else:
                    f = element.Fields
                    rows.append(dict(index=int(element.ElementIndex), power=float(f[0].Data),
                        color_srgb=list(f[1].Data), quality=float(f[2].Data), focus=float(f[3].Data),
                        power_per_unit_area=bool(f[4].TestBit('power per unit area')),
                        use_shader_gel=bool(f[4].TestBit('use shader gel')),
                        attenuation_falloff=float(f[5].Data), attenuation_cutoff=float(f[6].Data),
                        bounce_ratio=float(f[7].Data)))
        finally:
            tag.Dispose()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        report[extension] = dict(source=str(path), sha256=before, materials=rows)
finally:
    Bungie.ManagedBlamSystem.Stop()
(OUT / 'original-material-lighting.json').write_text(json.dumps(report, indent=2)+'\n')
print('ORIGINAL_MATERIAL_LIGHTING_READ', {k:len(v['materials']) for k,v in report.items()})
