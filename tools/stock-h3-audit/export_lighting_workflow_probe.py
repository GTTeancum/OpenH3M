"""Exercise existing H3 lighting controls on the upstream example, without saving it."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
source=OUT/'upstream/c20-water-example/water-visual.blend'
assert Path(bpy.data.filepath)==source
before=hashlib.sha256(source.read_bytes()).hexdigest()
assert before=='830830c7eb3ea17d84dbbf4e29bd1fc437d82c0442cd0e6e7a996c4d76e68589'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
native=json.loads((OUT/'original-material-lighting.json').read_text())
for tag in native.values():assert hashlib.sha256(Path(tag['source']).read_bytes()).hexdigest()==tag['sha256']
emissions=native['scenario_structure_lighting_info']['materials']
bound='--bound-shaders' in sys.argv
stem='bound_shaders' if bound else 'lighting'
bindings=json.loads((OUT/'h3-material-bindings.json').read_text()) if bound else None
aliases=sorted([b for b in bindings['bindings'].values() if b['authored'].endswith('.shader')],key=lambda b:b['name'])[:6] if bound else []
if bound:
    assert len(aliases)==6
    assert hashlib.sha256(Path(bindings['shader_collection']['path']).read_bytes()).hexdigest()==bindings['shader_collection']['sha256']
level=bpy.data.objects['level']
assert len(level.data.polygons)==6
wall=next(m for m in level.data.materials if not m.name.startswith('+'))
for obj in list(bpy.context.scene.objects):
    if obj!=level:bpy.data.objects.remove(obj,do_unlink=True)
level.data.materials.clear()
cases=[]
for index,(priority,emission_index) in enumerate(zip((.0625,.25,1,4,8,32),(5,1,2,3,7,8))):
    original=emissions[emission_index]
    mat=wall.copy()
    mat.name='lighting_probe_'+chr(ord('a')+index)
    mat.ass_jms.name_override=aliases[index]['export_prefix']+' '+aliases[index]['name'] if bound else wall.name
    p=mat.ass_jms
    p.is_bm=True
    p.lightmap_res=priority
    p.power=original['power']
    p.color=original['color_srgb']
    p.quality=original['quality']
    p.emissive_focus=original['focus']
    p.power_per_unit_area=original['power_per_unit_area']
    p.use_shader_gel=original['use_shader_gel']
    p.attenuation_enabled=True
    p.falloff_distance=original['attenuation_falloff']
    p.cutoff_distance=original['attenuation_cutoff']
    level.data.materials.append(mat)
    level.data.polygons[index].material_index=index
    cases.append(dict(material=mat.name,priority=priority,source_emission=original))
    if bound:
        alias=aliases[index]
        assert hashlib.sha256(Path(alias['export_tag']).read_bytes()).hexdigest()==alias['sha256']
        cases[-1]['expected_shader']=str(Path(alias['export_tag']).relative_to(ROOT/'work/editing-kits/h3ek/tags')).removesuffix('.shader')+',rmsh'
dest=ROOT/'work/editing-kits/h3ek/data/levels/custom/bc_lighting_workflow_probe/structure'/(stem+'.ass')
dest.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(dest),7,'halo3',False,True,True,True,True,True,
    global_functions.EdgeSplit(False,False,0.0,False),False,1.0,
    lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/(stem+'-workflow-probe.json')).write_text(json.dumps(dict(source_sha256=before,ass=str(dest),stem=stem,
    ass_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),cases=cases,
    limitation='Native control diagnostic only; no Battle Canyon lighting authored or approved.'),indent=2)+'\n')
print('LIGHTING_WORKFLOW_EXPORTED',len(cases),'native input combinations',flush=True)
