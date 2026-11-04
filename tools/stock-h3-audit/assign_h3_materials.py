"""Bind reviewed H3 tags through the community exporter's material names.

Short tag copies are byte-identical build inputs under the map's asset root.
No shader generation, mesh editing, serializer or missing-material substitution.
"""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
ASSET=KIT/'tags/levels/custom/battle_canyon_fresh'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.global_functions import mesh_processing
source=OUT/'battle-canyon-h3-authoring.blend'
assert Path(bpy.data.filepath)==source
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=sha(source)
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
reviewed={}
stock_bindings=json.loads((OUT/'stock-material-bindings.json').read_text())
for original,binding in stock_bindings.items():
    assert sha(KIT/'tags'/binding['target'])==binding['target_sha256']
    assert sha(ROOT/'work/editing-kits/hrek/tags'/original)==binding['source_sha256']
    reviewed[original]=binding['target']
for family in json.loads((ROOT/'tools/stock-h3-audit/material_families.json').read_text()):
    report=json.loads((OUT/(family+'-family/report.json')).read_text())
    for material in report['materials']:reviewed[material['source']]=material['target']
for path in [OUT/'terrain-trial-report.json',*sorted(OUT.glob('ca_bcreek_*-terrain-trial-report.json'))]:
    report=json.loads(path.read_text())
    reviewed[report['source']]=report['target']
foliage=r'levels\dlc\cex_beaver_creek\shaders\cex_bc_tree_boreal_leaves.shader_foliage'
assert (OUT/'foliage-trial-verification.json').is_file()
reviewed[foliage]=str(Path(r'levels\custom\battle_canyon_fresh\shaders')/Path(foliage).name)

used=set()
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    for polygon in obj.data.polygons:
        assert polygon.material_index<len(obj.data.materials),obj.name
        material=obj.data.materials[polygon.material_index]
        assert material is not None,obj.name
        used.add(material)
shape_counts={obj.name:(len(obj.data.vertices),len(obj.data.polygons)) for obj in bpy.context.scene.objects if obj.type=='MESH'}
bindings={}
assigned=[]
pending=[]
special=[]
dest=ASSET/'export_shaders'
dest.mkdir(exist_ok=True)
# Tool resolves a short material name through this documented collection prefix.
collection=KIT/'tags/levels/shader_collections.txt'
collection_before=sha(collection)
collection_text=collection.read_text(encoding='utf-8-sig')
prefix='bcf'
relative=str(dest.relative_to(KIT/'tags'))
existing=[line.split() for line in collection_text.splitlines() if line.split() and line.split()[0]==prefix]
assert not existing or existing==[[prefix,relative]],existing
if not existing:
    with collection.open('a',encoding='utf-8',newline='') as stream:
        stream.write('\n'+prefix+'\t'+relative+'\n')
for material in sorted(used,key=lambda m:m.name):
    original=material.nwo.shader_path
    if not original:
        name=material.ass_jms.name_override or material.name
        assert name in ('+sky','+portal','+seamsealer'),(material.name,name)
        special.append(dict(material=material.name,name=name))
        continue
    if original not in reviewed:
        pending.append(dict(material=material.name,source=original))
        continue
    if original in stock_bindings:
        # Stock invalid is not a substitute for unfinished visible artwork.
        assert any(getattr(material.ass_jms,mode) for mode in stock_bindings[original]['allowed_face_modes']),material.name
    target=KIT/'tags'/reviewed[original]
    digest=sha(target)
    if original not in bindings:
        stem=Path(original).stem.removeprefix('ca_bcreek_')
        name='bc_'+stem[:12].rstrip('_')+'_'+hashlib.sha256(original.encode()).hexdigest()[:8]
        assert len(name)<=24 and name==name.lower()
        assert all(row['name']!=name for row in bindings.values()),name
        alias=dest/(name+target.suffix)
        # This directory is disposable authoring output. Refresh after every
        # native tag update so the ASS binding cannot silently use an old copy.
        shutil.copyfile(target,alias)
        assert sha(alias)==digest
        bindings[original]=dict(name=name,export_prefix=prefix,authored=str(target),export_tag=str(alias),sha256=digest)
    row=bindings[original]
    material.ass_jms.name_override=("'" if original.endswith('.shader_water') else '')+prefix+' '+row['name']
    exported=mesh_processing.append_material_symbols(material,'halo3',True)
    assert len(exported)<=32,(material.name,exported)
    assigned.append(dict(material=material.name,source=original,export_name=exported))
assert shape_counts=={obj.name:(len(obj.data.vertices),len(obj.data.polygons)) for obj in bpy.context.scene.objects if obj.type=='MESH'}
assert sha(source)==before
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.nwo.lights_export_on_save=False
bpy.context.scene.nwo.prefabs_export_on_save=False
destination=OUT/'battle-canyon-h3-materials.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
report=dict(source=str(source),source_sha256=before,scene=str(destination),scene_sha256=sha(destination),
            bindings=bindings,assigned=assigned,pending=pending,special=special,
            shader_collection=dict(path=str(collection),prefix=prefix,directory=relative,before_sha256=collection_before,sha256=sha(collection)),
            limitation='Native naming and byte-identical tag staging only. Pending surfaces forbid a final map build; visual validation is still required.')
(OUT/'h3-material-bindings.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_MATERIAL_BINDINGS',len(bindings),'tags',len(assigned),'slots',len(pending),'pending slots',flush=True)
