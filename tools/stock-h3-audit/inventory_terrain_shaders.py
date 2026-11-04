"""Inspect native terrain configurations from the verified stock-cache lists."""
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
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
provenance={}
for file in OUT.glob('*-all-tags.txt'):
    for line in file.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        match=re.search(r'\] (.+\.shader_terrain)$',line)
        if match:provenance.setdefault(match[1],[]).append(file.name.removesuffix('-all-tags.txt'))
missing=[p for p in provenance if not (KIT/'tags'/p).is_file()]
assert not missing,missing
plan=OUT/'stock-terrain-read-plan.json'
plan.write_text(json.dumps(dict(Kit=str(KIT),Tags=sorted(provenance),Output=str(OUT/'stock-terrain-configurations.json')),indent=2)+'\n')
run=subprocess.run([str(OUT/'h3-api-probe/ReadH3ShaderConfigurations.exe'),str(plan)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'stock-terrain-read.log').write_bytes(run.stdout)
assert run.returncode==0,run.stdout.decode(errors='replace')
definition=ET.fromstring((OUT/'h3-terrain-definition.xml').read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
categories=list(definition.find("block[@name='categories']"))
stock=json.loads((OUT/'stock-terrain-configurations.json').read_text())
for row in stock:
    assert len(row['options'])==len(categories)
    row['named_options']={c.get('name'):c.find(f"block[@name='options']/element[@index='{row['options'][i]}']").get('name') for i,c in enumerate(categories)}
rows=[]
for source,setup in json.loads((OUT/'reach-effective-shader-options.json').read_text()).items():
    if not source.endswith('.shader_terrain'):continue
    selected={c['category']:c['option'] for c in setup['categories']}
    matches=[]
    for row in stock:
        differences={k:dict(source=selected[k],stock=v) for k,v in row['named_options'].items() if selected[k]!=v}
        matches.append(dict(target=row['path'],maps=provenance[row['path']],differences=differences))
    matches.sort(key=lambda r:(len(r['differences']),'standoff' not in r['maps'],r['target']))
    exact=[r for r in matches if not r['differences']]
    rows.append(dict(source=source,matches=exact,nearest=matches[:3] if not exact else [],source_only_categories={k:v for k,v in selected.items() if k not in stock[0]['named_options']}))
    print(Path(source).stem,'EXACT',len(exact),'FIRST',exact[0]['target'] if exact else matches[0],flush=True)
(OUT/'expanded-stock-terrain-matches.json').write_text(json.dumps(dict(stock_shaders=len(stock),surfaces=rows),indent=2)+'\n')
(OUT/'stock-terrain-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('STOCK_TERRAIN_CONFIGURATIONS',len(stock),flush=True)
