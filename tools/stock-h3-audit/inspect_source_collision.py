"""Read the original Reach boulder collision/auxiliary BSP via ManagedBlam."""
import collections
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

def scalar(field):
    if hasattr(field,'Data'):
        value=field.Data
        if isinstance(value,(str,int,float,bool)):return value
        try:return [float(v) for v in value]
        except TypeError:return str(value)
    if hasattr(field,'Value'):return int(field.Value)
    if hasattr(field,'Path'):return str(field.Path.RelativePathWithExtension) if field.Path else None
    return str(field.GetStringData()) if hasattr(field,'GetStringData') else None

def read_bsp(element):
    result={}
    for name in ('vertices','surfaces','edges','planes'):
        result[name]=[{str(f.DisplayName):scalar(f) for f in e.Fields} for e in element.SelectField('Block:'+name).Elements]
        if name=='surfaces':
            for row,e in zip(result[name],element.SelectField('Block:'+name).Elements):
                flags=e.SelectField('flags')
                row['flags']={bit:bool(flags.TestBit(bit)) for bit in ('plane negated','invalid','climbable','breakable','slip','invisible','two sided')}
    return result

callback=Bungie.ManagedBlamCrashCallback(lambda info:None)
parameters=Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
name=r'levels\dlc\cex_beaver_creek\cex_beaver_creek'
path=KIT/'tags'/(name+'.scenario_structure_bsp')
before=hashlib.sha256(path.read_bytes()).hexdigest()
tag=Bungie.Tags.TagFile()
try:
    tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(name,'scenario_structure_bsp'))
    definitions=tag.SelectField('Struct:resource interface[0]/Block:raw_resources[0]/Struct:raw_items[0]/Block:instanced geometries definitions')
    definition=definitions.Elements[74]
    collision=read_bsp(definition.SelectField('Struct:collision info').Elements[0])
    render=[read_bsp(e) for e in definition.SelectField('Block:render bsp').Elements]
    material_indices={int(s['material']) for s in collision['surfaces']}
    materials={}
    for i,e in enumerate(tag.SelectField('Block:collision materials').Elements):
        if i in material_indices:materials[i]={str(f.DisplayName):scalar(f) for f in e.Fields}
finally:
    tag.Dispose()
    Bungie.ManagedBlamSystem.Stop()
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
report=dict(source=str(path),sha256=before,definition_index=74,collision=collision,render_bsp=render,materials=materials)
(OUT/'original-boulder-collision.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_BOULDER_COLLISION',json.dumps(dict(collision={k:len(v) for k,v in collision.items()},
    render_bsp=[{k:len(v) for k,v in b.items()} for b in render],
    surface_materials=dict(collections.Counter(s['material'] for s in collision['surfaces'])),materials=materials)),flush=True)
