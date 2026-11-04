"""Compare inspected option names; this report does not assign donor materials."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
reach=json.loads((OUT/'reach-effective-shader-options.json').read_text())
h3=json.loads((OUT/'h3-effective-shader-options.json').read_text())
assert h3 and all(k.endswith('.shader') for k in h3)
surface_categories={'albedo','bump_mapping','alpha_test','specular_mask','material_model','environment_mapping','self_illumination','blend_mode','parallax'}
rows=[]
for source,inspection in reach.items():
    if not source.endswith('.shader'):continue
    source_options={c['category']:c['option'] for c in inspection['categories']}
    matches=[]
    for target,selected in h3.items():
        differences=[dict(category=c['category'],source=source_options[c['category']],target=c['option'])
                     for c in selected if c['category'] in surface_categories and source_options[c['category']]!=c['option']]
        if differences:continue
        target_names={c['category'] for c in selected}
        matches.append(dict(target=target,
            other_source_options={k:v for k,v in source_options.items() if k not in surface_categories},
            other_target_options={c['category']:c['option'] for c in selected if c['category'] not in surface_categories},
            defaulted_target_options=[c['category'] for c in selected if c['defaulted_missing_option']]))
    rows.append(dict(source=source,shared_category_matches=matches))
report=dict(surfaces=rows,compared_categories=sorted(surface_categories),source_count=len(rows),sources_with_shared_category_match=sum(bool(r['shared_category_matches']) for r in rows),
            limitation='Nine surface category names only. Misc differs by game and is reported separately along with extra categories. Input semantics, animation layouts, bitmap roles and actual appearance still require review; no donor was assigned.')
(OUT/'ordinary-shader-configuration-matches.json').write_text(json.dumps(report,indent=2)+'\n')
print('SHADER_CONFIGURATION_REVIEW',report['sources_with_shared_category_match'],'of',len(rows),'have shared-category matches',flush=True)
