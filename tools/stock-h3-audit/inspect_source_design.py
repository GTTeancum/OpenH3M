"""Read original Reach structure-design fields through the official tag API."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie

def fields(element):
    result={}
    for field in element.Fields:
        name=str(field.DisplayName)
        if isinstance(field,Bungie.Tags.TagFieldBlock):
            value=[fields(e) for e in field.Elements]
        elif hasattr(field,'Data'):
            value=field.Data
            try:value=value if isinstance(value,str) else [float(v) for v in value]
            except (TypeError,ValueError):
                try:value=float(value)
                except (TypeError,ValueError):value=str(value)
        elif hasattr(field,'GetStringData'):
            value=str(field.GetStringData())
        elif hasattr(field,'Value'):
            value=int(field.Value)
        elif hasattr(field,'Path'):
            value=str(field.Path.RelativePathWithExtension) if field.Path else None
        else:
            continue
        assert name not in result,name
        result[name]=value
    return result

callback=Bungie.ManagedBlamCrashCallback(lambda info:None)
parameters=Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
name=r'levels\dlc\cex_beaver_creek\cex_beaver_creek_design'
source=KIT/'tags'/(name+'.structure_design')
before=hashlib.sha256(source.read_bytes()).hexdigest()
tag=Bungie.Tags.TagFile()
rows={}
try:
    tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(name,'structure_design'))
    for block in ('water groups block','water instances block','soft ceilings block'):
        rows[block]=[fields(e) for e in tag.SelectField('Struct:physics[0]/Block:'+block).Elements]
    rows['planar fogs']=[fields(e) for e in tag.SelectField('Struct:planar fog set[0]/Block:planar fogs').Elements]
finally:
    tag.Dispose()
    Bungie.ManagedBlamSystem.Stop()
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/'original-structure-design.json').write_text(json.dumps(dict(source=str(source),sha256=before,blocks=rows),indent=2)+'\n')
print('ORIGINAL_DESIGN_READ', {name:len(values) for name,values in rows.items()},flush=True)
