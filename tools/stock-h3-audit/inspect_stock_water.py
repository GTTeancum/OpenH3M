"""Read stock water options with official Tool and original-cache provenance.

This is an inventory, not permission to drop unmatched Reach water features.
No source or stock tag is saved.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/h3ek'
DEST = OUT / 'stock-water-inspection'
DEST.mkdir(exist_ok=True)
env = os.environ.copy()
for key, relative in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'), ('TEMP', 'temp'), ('TMP', 'temp')]:
    env[key] = str(OUT / relative)
env['DOTNET_ROLL_FORWARD'] = 'Major'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


hashes = {}


def export(path):
    tag = KIT / 'tags' / path
    before = sha(tag)
    target = DEST / (Path(path).name + '.xml')
    result = subprocess.run([str(KIT / 'tool.exe'), 'export-tag-to-xml', str(tag), str(target)],
                            cwd=KIT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    target.with_suffix('.log').write_bytes(result.stdout)
    assert result.returncode == 0 and target.is_file(), result.stdout.decode(errors='replace')
    assert sha(tag) == before
    hashes[str(tag)] = before
    return ET.fromstring(target.read_text(errors='replace').replace('<unavailable>', '&lt;unavailable&gt;'))


definition = export(r'shaders\water.render_method_definition')
categories = list(definition.find("block[@name='categories']"))
provenance = {}
for file in OUT.glob('*-all-tags.txt'):
    for line in file.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        match = re.search(r'\] (.+\.shader_water)$', line)
        if match:
            provenance.setdefault(match[1], []).append(file.name.removesuffix('-all-tags.txt'))
assert provenance
reach = json.loads((OUT / 'reach-effective-shader-options.json').read_text())
source = r'levels\dlc\cex_beaver_creek\shaders\ca_bcreek_river.shader_water'
selected = {c['category']: c['option'] for c in reach[source]['categories']}
rows = []
for donor, maps in sorted(provenance.items()):
    shader = export(donor)
    options = [int(e.find('field').get('value')) for e in shader.find("block[@name='options']")]
    assert len(options) == len(categories)
    named = {c.get('name'): c.find(f"block[@name='options']/element[@index='{options[i]}']").get('name') for i, c in enumerate(categories)}
    map_name = maps[0]
    cache = Path('C:/X360/ISOs/H3M/maps') / (('bunkerworld' if map_name == 'standoff' else map_name) + '.map')
    before = sha(cache)
    commands = DEST / (Path(donor).stem + '.commands')
    commands.write_text('EditTag ' + donor + '\nForEach Options ListFields OptionIndex\n')
    result = subprocess.run([str(OUT / 'bin/TagTool.exe'), str(cache), 'RunCommands', str(commands)],
                            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    commands.with_suffix('.log').write_bytes(result.stdout)
    stock_options = [int(v) for v in re.findall(rb'OptionIndex: Int16 = (\d+)', result.stdout)]
    assert result.returncode == 0 and sha(cache) == before and stock_options
    assert stock_options == options[:len(stock_options)], (donor, stock_options, options)
    rows.append(dict(target=donor, maps=maps, options=options, stock_options=stock_options,
                     named_options=named, cache=str(cache), cache_sha256=before,
                     differences={k: dict(source=selected.get(k), stock=v) for k, v in named.items() if selected.get(k) != v},
                     source_only={k: v for k, v in selected.items() if k not in named}))
    print('STOCK_WATER_READ', Path(donor).stem, rows[-1]['differences'], rows[-1]['source_only'], flush=True)
for path, digest in hashes.items():
    assert sha(Path(path)) == digest
(OUT / 'stock-water-comparison.json').write_text(json.dumps(dict(source=source, source_options=selected,
    candidates=rows, source_hashes=hashes, limitation='Native option comparison only; no authored water, geometry compatibility or rendered acceptance.'), indent=2) + '\n')
