"""Inspect stock unlit shader candidates without saving or generating tags."""
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/h3ek'
env = os.environ.copy()
for key, rel in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'), ('TEMP', 'temp'), ('TMP', 'temp')]:
    env[key] = str(OUT / rel)
provenance = {}
for file in OUT.glob('*-all-tags.txt'):
    for line in file.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        match = re.search(r'\] (.+\.shader_halogram)$', line)
        if match:
            provenance.setdefault(match[1], []).append(file.name.removesuffix('-all-tags.txt'))
assert provenance
missing = [p for p in provenance if not (KIT / 'tags' / p).is_file()]
plan = OUT / 'stock-halogram-read-plan.json'
plan.write_text(json.dumps(dict(Kit=str(KIT), Tags=sorted(set(provenance) - set(missing)),
    Output=str(OUT / 'stock-halogram-configurations.json')), indent=2) + '\n')
result = subprocess.run([str(OUT / 'h3-api-probe/ReadH3ShaderConfigurations.exe'), str(plan)],
    cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
(OUT / 'stock-halogram-read.log').write_bytes(result.stdout)
assert result.returncode == 0, result.stdout.decode(errors='replace')
xml = OUT / 'h3-halogram-definition.xml'
result = subprocess.run([str(KIT / 'tool.exe'), 'export-tag-to-xml',
    str(KIT / 'tags/shaders/halogram.render_method_definition'), str(xml)],
    cwd=KIT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
(OUT / 'h3-halogram-definition.log').write_bytes(result.stdout)
assert result.returncode == 0
categories = list(ET.fromstring(xml.read_text(errors='replace').replace('<unavailable>', '&lt;unavailable&gt;')).find("block[@name='categories']"))
candidates = []
for row in json.loads((OUT / 'stock-halogram-configurations.json').read_text()):
    named = {c.get('name'): c.find(f"block[@name='options']/element[@index='{row['options'][i] if i < len(row['options']) else 0}']").get('name') for i, c in enumerate(categories)}
    if named['albedo'] == 'default' and named['self_illumination'] == 'illum_detail' and named['blend_mode'] == 'alpha_blend':
        candidates.append(dict(target=row['path'], maps=provenance[row['path']], options=named))
        print('UNLIT_SKY_CANDIDATE', row['path'], named, flush=True)
(OUT / 'stock-halogram-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
(OUT / 'stock-unlit-sky-candidates.json').write_text(json.dumps(dict(candidates=candidates, missing_mcc_tags=missing,
    limitation='Candidate option inspection; no cross-group authoring or rendered equivalence established.'), indent=2) + '\n')
print('STOCK_HALOGRAMS_INSPECTED', len(provenance) - len(missing), 'MISSING', missing, flush=True)
