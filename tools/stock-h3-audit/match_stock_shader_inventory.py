"""Compare native stock option vectors; candidates are not automatic approvals."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
stock=json.loads((OUT/'stock-shader-configurations.json').read_text())
reach=json.loads((OUT/'reach-effective-shader-options.json').read_text())
provenance=json.loads((OUT/'stock-shader-map-provenance.json').read_text())
definition=ET.fromstring((OUT/'h3-shader-definition.xml').read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
categories=list(definition.find("block[@name='categories']"))
keys=['albedo','bump_mapping','alpha_test','specular_mask','material_model','environment_mapping','self_illumination','blend_mode','parallax']
for row in stock:
    row['named_options']={c.get('name'):c.find(f"block[@name='options']/element[@index='{row['options'][i] if i<len(row['options']) else 0}']").get('name') for i,c in enumerate(categories)}
rows=[]
for source,inspection in reach.items():
    if not source.endswith('.shader'):continue
    selected={c['category']:c['option'] for c in inspection['categories']}
    compared=[]
    for target in stock:
        differences={k:dict(source=selected[k],stock=target['named_options'][k]) for k in keys if selected[k]!=target['named_options'][k]}
        compared.append(dict(target=target['path'],maps=provenance[target['path']],differences=differences))
    compared.sort(key=lambda c:(len(c['differences']),'standoff' not in c['maps'],not c['target'].startswith('levels\\multi\\guardian'),c['target']))
    matches=[c for c in compared if not c['differences']]
    rows.append(dict(source=source,matches=matches,nearest_candidates=[] if matches else compared[:3]))
    if not matches:print(Path(source).name,compared[0]['differences'],flush=True)
report=dict(stock_shaders=len(stock),source_shaders=len(rows),matching=sum(bool(r['matches']) for r in rows),
            surfaces=rows,limitation='Nine shared category names only. Inspect active inputs, stock provenance and appearance before assignment. Extra game-specific categories remain separate.')
(OUT/'expanded-stock-shader-matches.json').write_text(json.dumps(report,indent=2)+'\n')
print('STOCK_CONFIGURATION_MATCHES',report['matching'],'of',len(rows),'using',len(stock),'stock shaders',flush=True)
