"""Summarise a Halo 2 effect export (tool export-tag-to-xml): per particle system, its particle tag and emitters,
with each emitter property's input/range/output settings and its function's leading values.
Halo 2 emitter property order (unnamed in the export): emission rate, lifespan, velocity, angular velocity, size,
tint, alpha; then emission shape; then emission radius, emission angle; translational offset; relative direction.
Usage: h2_effect_summary.py <effect.xml> [out.json]"""
import json, re, struct, sys
import xml.etree.ElementTree as ET
from pathlib import Path

text = Path(sys.argv[1]).read_bytes().decode('latin-1')
text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '?', text)
root = ET.fromstring(text)
PROPS = ['emission rate', 'lifespan', 'velocity', 'angular velocity', 'size', 'tint', 'alpha', 'emission radius', 'emission angle']


def func(block):
    b = bytes((int(v.text) & 255) for v in block.iter('field') if v.get('name') == 'Value')
    head = b[:4].hex()
    vals = [round(struct.unpack_from('<f', b, o)[0], 4) for o in range(4, min(len(b) - 3, 20), 4)]
    return {'header': head, 'values': vals, 'bytes': b.hex()}


out = []
for ev in root.find("block[@name='events']"):
    for ps in ev.find("block[@name='particle systems']"):
        sysd = {'particle': ps.find("tag_reference[@name='particle']").text,
                'fields': {f.get('name'): f.text for f in ps.findall('field')}, 'emitters': []}
        for em in ps.find("block[@name='emitters']"):
            children = list(em); props = []; cur = None; fields = {}
            for c in children:
                if c.tag == 'field' and c.get('name') == 'Input Variable':
                    cur = {'input': c.text}; props.append(cur)
                elif c.tag == 'field' and c.get('name') in ('Range Variable', 'Output Modifier', 'Output Modifier Input') and cur is not None:
                    cur[c.get('name')] = c.text
                elif c.tag == 'block' and c.get('name') == 'data' and cur is not None:
                    cur.update(func(c)); cur = None
                elif c.tag == 'field':
                    fields[c.get('name')] = c.text
                elif c.tag == 'tag_reference':
                    fields[c.get('name')] = c.text
            named = {PROPS[k] if k < len(PROPS) else f'extra{k}': p for k, p in enumerate(props)}
            sysd['emitters'].append({'fields': fields, 'properties': named})
        out.append(sysd)
if len(sys.argv) > 2: json.dump(out, open(sys.argv[2], 'w'), indent=1)
for s in out:
    print('==', s['particle'])
    for e in s['emitters']:
        print('   ', {k: v for k, v in e['fields'].items() if v and v.strip() not in ('0', '0.000000')})
        for k, p in e['properties'].items():
            print(f"     {k:18s} {p['input']:22s} {p.get('Range Variable', ''):22s} {p.get('Output Modifier', '')!s:8s} {p['header']} {p['values']}")
