"""Remove unrelated donor overrides and enter native source scalar defaults.

All writes use the official H3 API. The original source function blobs are
verified separately and no bitmap is reimported by this operation.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from shader_defaults import ShaderDefaults

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
DEST=OUT/'default-corrections'
DEST.mkdir(exist_ok=True)
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
defaults=ShaderDefaults()
families=json.loads(Path(__file__).with_name('material_families.json').read_text())
physical_names={t['Path']:t['Fields'] for t in json.loads((OUT/'physical-material-plan.json').read_text())['Tags']}
hashes={}
for name,records in [('hrek',defaults.reach),('h3ek',defaults.h3)]:
    for path,record in records.items():hashes[str(ROOT/'work/editing-kits'/name/'tags'/path)]=record['sha256']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
for path,expected in hashes.items():assert sha(path)==expected,path
summary=[]
for family,config in families.items():
    report_path=OUT/(family+'-family/report.json')
    report=json.loads(report_path.read_text())
    for material in report['materials']:
        original=json.loads(Path(material['plan']).read_text())
        explicit={p['Name'] for p in original['Parameters'] if not any('Constant' in a for a in p['Animations'])}
        changes=defaults.plan(material['source'],config['donor'],explicit)
        plan=dict(Kit=str(KIT),Donor=config['donor'],Target=material['target'],
                  Parameters=changes['overrides'],RemoveParameters=changes['remove'])
        path=DEST/(Path(material['source']).stem+'.json')
        path.write_text(json.dumps(plan,indent=2)+'\n')
        xml_path=Path(material['xml'])
        previous=ET.fromstring(xml_path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
        old_options=[e.find('field').get('value') for e in previous.find("block[@name='options']")]
        old_material=previous.find("field[@name='material name']")
        expected_material=physical_names.get(material['target'],{}).get('material name',old_material.get('value'))
        commands=[([str(OUT/'h3-api-probe/ApplyH3ShaderPlan.exe'),str(path),'--update'],'update'),
                  ([str(OUT/'h3-api-probe/ApplyH3ShaderPlan.exe'),str(path),'--verify'],'defaults-readback'),
                  ([str(OUT/'h3-api-probe/ApplyH3ShaderPlan.exe'),material['plan'],'--verify'],'source-readback'),
                  ([str(KIT/'tool.exe'),'export-tag-to-xml',str(KIT/'tags'/material['target']),str(xml_path)],'export')]
        for command,label in commands:
            run=subprocess.run(command,cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
            (DEST/(Path(material['source']).stem+'-'+label+'.log')).write_bytes(run.stdout)
            assert run.returncode==0,(material['source'],label,run.stdout.decode(errors='replace'))
        saved=ET.fromstring(xml_path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
        assert old_options==[e.find('field').get('value') for e in saved.find("block[@name='options']")]
        assert saved.find("field[@name='material name']").get('value')==expected_material,material['target']
        assert not set(changes['remove']) & {p.get('name') for p in saved.find("block[@name='parameters']")}
        material.update(native_default_functions=len(changes['overrides']),native_option_defaults=changes['remove'],
                        stock_inputs_retained=changes['retained'],default_correction_plan=str(path))
        summary.append(dict(source=material['source'],family=family,**changes))
    for path,expected in report['source_hashes'].items():assert sha(path)==expected,path
    pixels=json.loads(report_path.with_name('pixel-verification.json').read_text())
    for bitmap in pixels['textures']:assert sha(KIT/'tags'/bitmap['target'])==bitmap['target_sha256'],bitmap['target']
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('DEFAULTS_VERIFIED',family,len(report['materials']),flush=True)
for path,expected in hashes.items():assert sha(path)==expected,path
(OUT/'default-correction-inventory.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'default-correction-source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
print('SOURCE_DEFAULTS_APPLIED',len(summary),'shaders',sum(len(x['remove']) for x in summary),'native defaults',sum(len(x['overrides']) for x in summary),'native scalar functions',flush=True)
