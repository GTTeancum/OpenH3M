"""Read the original Reach boulder collision/auxiliary BSP via ManagedBlam."""
import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
definition_index=int(sys.argv[sys.argv.index('--definition')+1]) if '--definition' in sys.argv else 74
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
    if '--world' in sys.argv:
        raw=tag.SelectField('Struct:resource interface[0]/Block:raw_resources[0]/Struct:raw_items').Elements[0]
        world={kind:[read_bsp(e) for e in raw.SelectField('Block:'+kind).Elements]
            for kind in ('collision bsp','large collision bsp')}
        world_report=dict(source=str(path),sha256=before,collision=world,
            material_names=[{str(f.DisplayName):scalar(f) for f in e.Fields}
                for e in tag.SelectField('Block:collision materials').Elements],
            limitation='Read-only original Reach world collision; not a generated replacement or a native H3 fidelity claim.')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==before
        (OUT/'original-world-collision.json').write_text(json.dumps(world_report,indent=2)+'\n')
        print('ORIGINAL_WORLD_COLLISION',json.dumps({kind:[{k:len(v) for k,v in b.items()} for b in bsps] for kind,bsps in world.items()}),flush=True)
        raise SystemExit(0)
    definitions=tag.SelectField('Struct:resource interface[0]/Block:raw_resources[0]/Struct:raw_items[0]/Block:instanced geometries definitions')
    definition=definitions.Elements[definition_index]
    collision=read_bsp(definition.SelectField('Struct:collision info').Elements[0])
    render=[read_bsp(e) for e in definition.SelectField('Block:render bsp').Elements]
    material_indices={int(s['material']) for s in collision['surfaces']}
    materials={}
    for i,e in enumerate(tag.SelectField('Block:collision materials').Elements):
        if i in material_indices:materials[i]={str(f.DisplayName):scalar(f) for f in e.Fields}
    inventory=[]
    authored=json.loads((OUT/'h3-collision-authoring-inspection.json').read_text())
    for row in authored['definitions']:
        if not row['collision_children']:continue
        index=int(row['mesh'].split(':')[1])
        item=definitions.Elements[index]
        collision_info=item.SelectField('Struct:collision info').Elements[0]
        inventory.append(dict(definition_index=index,instances=row['instances'],
            collision_vertices=int(collision_info.SelectField('Block:vertices').Elements.Count),
            collision_surfaces=int(collision_info.SelectField('Block:surfaces').Elements.Count),
            render_bsp_count=int(item.SelectField('Block:render bsp').Elements.Count),
            surface_mapping_count=int(item.SelectField('Block:surfaces').Elements.Count),
            imported_physics_proxies=len(row['physics_proxies'])))
finally:
    tag.Dispose()
    Bungie.ManagedBlamSystem.Stop()
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
report=dict(source=str(path),sha256=before,definition_index=definition_index,collision=collision,render_bsp=render,materials=materials)
report_name='original-instance-collision-'+str(definition_index)+'.json' if '--definition' in sys.argv else 'original-boulder-collision.json'
(OUT/report_name).write_text(json.dumps(report,indent=2)+'\n')
(OUT/'original-proxy-collision-inventory.json').write_text(json.dumps(dict(source=str(path),sha256=before,
    definitions=inventory,limitation='Read-only original source inventory. Matching structure does not prove other instances accept the diagnosed boulder controls.'),indent=2)+'\n')
print('ORIGINAL_PROXY_COLLISION_INVENTORY',len(inventory),'definitions, render BSP counts',dict(collections.Counter(r['render_bsp_count'] for r in inventory)),flush=True)
print('ORIGINAL_BOULDER_COLLISION',json.dumps(dict(collision={k:len(v) for k,v in collision.items()},
    render_bsp=[{k:len(v) for k,v in b.items()} for b in render],
    surface_materials=dict(collections.Counter(s['material'] for s in collision['surfaces'])),materials=materials)),flush=True)
