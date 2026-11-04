"""Compare named texture inputs for authoring review; never auto-author shaders.

Uses official XML/ManagedBlam inspection reports. Matching input names alone
does not prove matching shader options, UV interpretation, or visual behavior.
"""
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
reach = json.loads((OUT / 'hrek-shader-setups.json').read_text())
surfaces = json.loads((OUT / 'reach-source-references.json').read_text())['surface_references']

def source_inputs(path, ancestors=()):
    assert path not in ancestors, f'Inheritance cycle: {path}'
    fields = {f['name']: f for f in reach[path]}
    parent = fields['reference'].get('value')
    parameters = source_inputs(parent, ancestors + (path,)) if parent else {}
    for element in fields['parameters']['elements']:
        row = {f['name']: f.get('value') for f in element}
        if row.get('bitmap'):
            parameters[row['parameter name']] = row['bitmap']
    return parameters

targets = []
for path in sorted((OUT / 'h3-shader-xml').glob('*.xml')):
    if path.stat().st_size == 0:
        raise RuntimeError(f'Empty official shader export: {path}')
    root = ET.fromstring(path.read_text(errors='replace').replace('<unavailable>', '&lt;unavailable&gt;'))
    parameters = root.find("block[@name='parameters']")
    textures = {}
    for element in parameters:
        row = {f.get('name'): f.get('value') for f in element.findall('field')}
        if row.get('parameter type') == 'bitmap':
            textures[row['parameter name']] = row.get('bitmap')
    targets.append(dict(tag=root.get('id') + '.' + root.get('group'), group=root.get('group'),
                        texture_inputs=textures,
                        options=[e.find('field').get('value') for e in root.find("block[@name='options']")]))

rows = []
for source in sorted(surfaces):
    textures = source_inputs(source)
    candidates = []
    for target in targets:
        if target['group'] != source.rsplit('.',1)[1]:
            continue
        names = set(target['texture_inputs'])
        candidates.append(dict(target=target['tag'], stock_options=target['options'],
                               matching_inputs=sorted(set(textures) & names),
                               source_inputs_not_listed=sorted(set(textures) - names),
                               target_inputs_without_source=sorted(names - set(textures))))
    candidates.sort(key=lambda c: (len(c['source_inputs_not_listed']),
                                   not c['target'].startswith('levels\\dlc\\bunkerworld\\'),
                                   len(c['target_inputs_without_source']), c['target']))
    rows.append(dict(source=source, textures=textures, candidates=candidates[:3]))
report = dict(source_surfaces=len(rows), stock_candidates=len(targets), surfaces=rows,
              limitation='Named-input coverage only. Candidates are not approvals or verified matches; options/defaults/UVs and visual behavior require review.')
(OUT / 'shader-input-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
with (OUT / 'shader-input-comparison.csv').open('w',newline='') as stream:
    writer=csv.writer(stream)
    writer.writerow(['source','candidate','matching_inputs','source_inputs_not_listed','target_inputs_without_source'])
    for row in rows:
        for c in row['candidates']:
            writer.writerow([row['source'],c['target'],';'.join(c['matching_inputs']),
                             ';'.join(c['source_inputs_not_listed']),';'.join(c['target_inputs_without_source'])])
print('SHADER_INPUT_COMPARISON',len(rows),'source surfaces;',len(targets),'stock candidates')
