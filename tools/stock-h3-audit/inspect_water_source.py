"""Read original water vertex metadata with the official Reach tag API."""
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
    rows=[]
    for field in element.Fields:
        row=dict(name=str(field.DisplayName),type=type(field).__name__)
        if hasattr(field,'Data'):
            value=field.Data
            try:value=[float(v) for v in value]
            except TypeError:
                try:value=float(value)
                except (TypeError,ValueError):value=str(value)
            row['value']=value
        elif hasattr(field,'GetStringData'):
            row['value']=str(field.GetStringData())
        if isinstance(field,Bungie.Tags.TagFieldBlock):row['count']=int(field.Elements.Count)
        rows.append(row)
    return rows

callback=Bungie.ManagedBlamCrashCallback(lambda info:None)
parameters=Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
base=r'levels\dlc\cex_beaver_creek\cex_beaver_creek'
path=KIT/'tags'/(base+'.scenario_structure_bsp')
before=hashlib.sha256(path.read_bytes()).hexdigest()
tag=Bungie.Tags.TagFile()
rows=[]
try:
    tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(base,'scenario_structure_bsp'))
    meshes=tag.SelectField('Struct:render geometry[0]/Block:meshes')
    temporary=tag.SelectField('Struct:render geometry[0]/Block:per mesh temporary')
    materials=tag.SelectField('materials')
    render=Bungie.Tags.GameRenderModel()
    assert temporary.Elements.Count==meshes.Elements.Count
    for mesh in temporary.Elements:
        water=mesh.SelectField('raw water data')
        if not water.Elements.Count:continue
        data=water.Elements[0]
        vertices=mesh.SelectField('raw vertices')
        parts=meshes.Elements[mesh.ElementIndex].SelectField('parts')
        raw_indices=mesh.SelectField('raw indices')
        if not raw_indices.Elements.Count:raw_indices=mesh.SelectField('raw indices32')
        indices=[int(e.Fields[0].Data)&0xffff for e in raw_indices.Elements]
        water_global=[]
        for part in parts.Elements:
            material=materials.Elements[part.SelectField('render method index').Value]
            shader=material.SelectField('render method').Path.RelativePathWithExtension
            if shader.endswith('.shader_water'):
                start=int(part.SelectField('index start').Data)
                count=int(part.SelectField('index count').Data)
                water_global.extend(indices[start:start+count])
        local=[int(e.Fields[0].Data)&0xffff for e in data.Fields[0].Elements]
        assert len(water_global)==len(local)
        mapping={}
        for li,gi in zip(local,water_global):
            assert li not in mapping or mapping[li]==gi
            mapping[li]=gi
        native_uv=list(render.GetTexCoordsFromMesh(temporary,mesh.ElementIndex))
        samples=[dict(local=li,global_index=gi,raw_fields=fields(vertices.Elements[gi]),
                      api_texcoord=[float(v) for v in native_uv[gi*2:gi*2+2]])
                 for li,gi in sorted(mapping.items())]
        rows.append(dict(mesh=int(mesh.ElementIndex),raw_vertex_count=int(vertices.Elements.Count),
            raw_vertex_schema=fields(vertices.Elements[0]),
            water_fields=fields(data),
            water_indices=[int(e.Fields[0].Data) for e in data.Fields[0].Elements],
            water_vertices=[fields(e) for e in data.Fields[1].Elements],
            water_global_vertices=samples,
            parts=[fields(e) for e in meshes.Elements[mesh.ElementIndex].SelectField('parts').Elements],
            subparts=[fields(e) for e in meshes.Elements[mesh.ElementIndex].SelectField('subparts').Elements]))
        print('NATIVE_WATER_SOURCE',mesh.ElementIndex,'vertices',vertices.Elements.Count,
              'water vertices',data.Fields[1].Elements.Count,flush=True)
finally:
    tag.Dispose()
    Bungie.ManagedBlamSystem.Stop()
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
assert rows
(OUT/'original-water-geometry.json').write_text(json.dumps(dict(source=str(path),sha256=before,
    meshes=rows,limitation='Read-only native source metadata; no UV authoring or shader acceptance.'),indent=2)+'\n')
