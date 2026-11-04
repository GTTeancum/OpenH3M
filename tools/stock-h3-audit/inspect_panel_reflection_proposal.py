"""Read-only stock-map evidence for the three remaining panel material choices."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
env=os.environ.copy()
for key,rel in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/rel)
env['DOTNET_ROLL_FORWARD']='Major'
configurations=json.loads((OUT/'stock-shader-configurations.json').read_text())
provenance=json.loads((OUT/'stock-shader-map-provenance.json').read_text())
reach=json.loads((OUT/'reach-effective-shader-options.json').read_text())
categories=list(ET.fromstring((OUT/'h3-shader-definition.xml').read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;')).find("block[@name='categories']"))
names={r['path']:{c.get('name'):c.find(f"block[@name='options']/element[@index='{r['options'][i] if i<len(r['options']) else 0}']").get('name') for i,c in enumerate(categories)} for r in configurations}
by_path={r['path']:r for r in configurations}
shared=['albedo','bump_mapping','alpha_test','specular_mask','material_model','environment_mapping','self_illumination','blend_mode','parallax']
choices=[('circle_panels',r'levels\dlc\cex_beaver_creek\shaders\ca_bcreek_forerunner_panel_circle_quarter.shader',r'objects\vehicles\brute_chopper\shaders\brute_chopper_exposed.shader','bunkerworld'),
         ('forge_panel',r'levels\multi\forge_halo\shaders\for_forge_gen_panel_02.shader',r'levels\dlc\armory\shaders\metal_black_ibeam_unwrap.shader','armory')]
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
rows=[]
for label,source,donor,map_name in choices:
    original={c['category']:c['option'] for c in reach[source]['categories']}
    exact=[r['path'] for r in configurations if not any(r['options'][10:]) and all(names[r['path']].get(k)==original[k] for k in shared)]
    assert not exact,('Review exact stock alternative before proposing a change',source,exact)
    differences=[k for k in shared if names[donor][k]!=original[k]]
    assert differences==['environment_mapping'] and names[donor]['environment_mapping']=='dynamic'
    cache=Path('C:/X360/ISOs/H3M/maps')/(map_name+'.map')
    before=sha(cache)
    command=OUT/(label+'-reflection-proposal.commands')
    command.write_text('EditTag '+donor+'\nForEach Options ListFields OptionIndex\n')
    run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(command)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(label+'-reflection-proposal.log')).write_bytes(run.stdout)
    assert run.returncode==0 and sha(cache)==before
    options=[int(v) for v in re.findall(rb'OptionIndex: Int16 = (\d+)',run.stdout)]
    assert options==by_path[donor]['options'][:10] and options[9]==0
    assert not any(by_path[donor]['options'][10:])
    assert sha(KIT/'tags'/donor)==by_path[donor]['sha256']
    rows.append(dict(source=source,donor=donor,original_cache=str(cache),original_sha256=before,
        stock_options=options,mcc_sha256=by_path[donor]['sha256'],different_shared_categories=differences,
        exact_matches_in_available_inventory=exact,available_stock_maps=provenance[donor]))
    print('PANEL_REFLECTION_PROPOSAL_CHECKED',label,flush=True)
(OUT/'panel-reflection-proposal-evidence.json').write_text(json.dumps(dict(choices=rows,
    limitation='Proposal only. No panel shaders changed. Available stock-cache inventory is not every shipped campaign asset.'),indent=2)+'\n')
