"""List a Halo 2 scenario's object placements (from its tool export-tag-to-xml export): for each placement block,
the palette name, position, rotation and multiplayer settings. Usage: h2_placements.py <scenario.xml> <out.json>"""
import json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

text = Path(sys.argv[1]).read_bytes().decode('latin-1')
text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '?', text)
text = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+);)', '&amp;', text)
root = ET.fromstring(text)
PAIRS = {'scenery': 'scenery palette', 'crates': 'crate palette', 'light volumes': 'light volumes palette',
         'sound scenery': 'sound scenery palette', 'machines': 'machine palette', 'controls': 'control palette',
         'decals': 'decal palette', 'equipment': 'equipment palette', 'weapons': 'weapon palette',
         'vehicles': 'vehicle palette', 'bipeds': 'biped palette'}


def block(name): return root.find(f"block[@name='{name}']")


out = {}
for placements, palette in PAIRS.items():
    pb, pal = block(placements), block(palette)
    if pb is None or not len(pb): continue
    names = [(el.find('tag_reference').text if el.find('tag_reference') is not None else None) for el in (pal if pal is not None else [])]
    rows = []
    for el in pb:
        idx = [b for b in el.findall('block_index') if 'palette' in (b.text or '').lower()]
        i = int(idx[0].get('index')) if idx else -1
        f = {x.get('name'): x.text for x in el.findall('field')}
        rows.append({'palette': names[i] if 0 <= i < len(names) else None, 'position': f.get('position'),
                     'rotation': f.get('rotation'), 'scale': f.get('scale')})
    out[placements] = rows
ne = block('netgame equipment')
if ne is not None:
    rows = []
    for el in ne:
        f = {x.get('name'): x.text for x in el.findall('field')}
        ref = el.find('tag_reference')
        rows.append({'item': ref.text if ref is not None else None, 'position': f.get('position'),
                     'spawn time': f.get('spawn time (in seconds, 0 = default)') or f.get('spawn time'), 'fields': {k: v for k, v in f.items() if v}})
    out['netgame equipment'] = rows
nf = block('netgame flags')
if nf is not None:
    out['netgame flags'] = [{x.get('name'): x.text for x in el.findall('field')} for el in nf]
json.dump(out, open(sys.argv[2], 'w'), indent=1)
for k, v in out.items():
    from collections import Counter
    c = Counter((r.get('palette') or r.get('item') or r.get('type')) for r in v)
    print(f'{k}: {len(v)}'); [print(f'   {n:3d} {p}') for p, n in c.most_common()]
