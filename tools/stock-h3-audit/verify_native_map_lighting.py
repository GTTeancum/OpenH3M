"""Verify actual full-map H3 material lighting via official API and Tool XML.

Reads BSP materials through the existing water inspector and exports only the
small lighting-info tag. Geometry import errors remain an independent gate.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text())
imported=read('h3-full-geometry-import.json')
bindings=read('h3-material-bindings.json')
saved=read('h3-lighting-metadata-bound-verification.json')
ass=read('h3-lighting-metadata-ass-verification.json')
export=read('h3-bound-ass-inspection-report.json')
assert imported['import_completed'] and imported['returncode']==0
assert imported['scene_sha256']==saved['scene_sha256']==ass['scene_sha256']==sha(bindings['scene'])
assert imported['ass_sha256']==ass['ass_sha256']==sha(export['ass'])
assert imported['lighting_ass_verification_sha256']==sha(OUT/'h3-lighting-metadata-ass-verification.json')
name=r'levels\custom\battle_canyon_fresh\battle_canyon'
paths={suffix:KIT/'tags'/(name+'.'+suffix) for suffix in ('scenario_structure_bsp','scenario_structure_lighting_info')}
for path in paths.values():assert sha(path)==imported['native_outputs'][path.name]
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
def run(command,log):
    with (OUT/log).open('wb') as stream:
        result=subprocess.run(command,cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    text=(OUT/log).read_text(errors='replace')
    assert result.returncode==0 and '-ERROR-' not in text and 'FATAL' not in text,text[-4000:]
native_path=OUT/'h3-lighting-native-materials.json'
run([str(OUT/'h3-api-probe/InspectH3WaterGeometry.exe'),str(KIT),str(native_path),name],'h3-lighting-native-materials.log')
native=read(native_path.name)
assert native['sha256']==imported['native_outputs']['battle_canyon.scenario_structure_bsp']
xml=OUT/'h3-full-map-lighting-info.xml'
run([str(KIT/'tool.exe'),'export-tag-to-xml',str(paths['scenario_structure_lighting_info']),str(xml)],'h3-full-map-lighting-info.log')
tree=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
infos=tree.find('./block[@name="material info"]')
def field(element,name):return element.find('./field[@name="'+name+'"]').attrib['value']
def close(a,b):return abs(float(a)-float(b))<1e-6
verified=[]
for expected in saved['expected_native_materials']:
    binding=bindings['bindings'][expected['shader']]
    shader=str(Path(binding['export_tag']).relative_to(KIT/'tags'))
    assert sha(binding['export_tag'])==binding['sha256']
    matches=[]
    for material in native['material_lightmap_scales']:
        if material['fields']['render method']!=shader:continue
        resolution=[p for p in material['properties'] if p['type']==0]
        if len(resolution)!=1 or not close(resolution[0]['real-value'],expected['lightmap_res']):continue
        info=infos[int(material['fields']['imported material index'])]
        if not close(field(info,'emissive power'),expected['power']):continue
        if expected['power']>0:
            if not all(close(field(info,k),expected[v]) for k,v in (
                ('emissive quality','quality'),('emissive focus','focus'),
                ('attenuation falloff','attenuation_falloff'),('attenuation cutoff','attenuation_cutoff'))):continue
            if not all(close(a,b) for a,b in zip(field(info,'emissive color').split(','),expected['color'])):continue
            flags=int(field(info,'flags'))
            if not (flags&1) or bool(flags&2)!=expected['power_per_unit_area']:continue
            assert not expected['use_shader_gel'] and expected['attenuation_enabled']
        matches.append(material['index'])
    assert matches,('Missing native material lighting',expected)
    verified.append(dict(material=expected['material'],native_material_indices=matches,emitting=expected['power']>0))
assert len(verified)==saved['material_variants']==len(saved['expected_native_materials'])
for path in paths.values():assert sha(path)==imported['native_outputs'][path.name]
report=dict(scene_sha256=saved['scene_sha256'],ass_sha256=ass['ass_sha256'],
    native_tags=imported['native_outputs'],lighting_xml_sha256=sha(xml),
    verified_material_variants=verified,geometry_import_clean=imported['clean_import_completed'],
    limitation='Actual compiled lighting inputs and shader references verified. This does not resolve geometry errors or establish baked lighting, shadows, MCC appearance or gameplay.')
(OUT/'h3-full-map-lighting-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_FULL_MAP_LIGHTING_INPUTS_VERIFIED',len(verified),'variants;',sum(r['emitting'] for r in verified),'emitting variants; geometry clean:',report['geometry_import_clean'],flush=True)
