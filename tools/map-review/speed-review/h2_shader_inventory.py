"""Summarise Halo 2 shader XML exports (from h2_export_xml.py): template, bitmaps, constants and bitmap scales.
Usage: h2_shader_inventory.py <xml dir> <out json>"""
import json, struct, sys
import xml.etree.ElementTree as ET
from pathlib import Path


def function_values(prop):
    """A Halo 2 animation property stores a function as signed bytes; for a constant function the two
    floats start at byte 4 (bytes 0-3 are the header)."""
    b = bytes((int(v.text) & 255) for v in prop.iter('field') if v.get('name') == 'Value')
    vals = [struct.unpack_from('<f', b, o)[0] for o in range(4, min(len(b) - 3, 12), 4)]
    return [round(v, 4) for v in vals]


inv = {}
for f in sorted(Path(sys.argv[1]).glob('*.xml')):
    root = ET.parse(f).getroot()
    tag = f.stem.replace('~', '\\')
    tpl = root.find("tag_reference[@name='template']")
    entry = {'template': tpl.text if tpl is not None else None, 'material': None, 'parameters': {}}
    m = root.find("field[@name='material name']")
    entry['material'] = m.text if m is not None else None
    lt = root.find("field[@name='lightmap type']")
    entry['lightmap_type'] = lt.text.split(',', 1)[1] if lt is not None else None
    params = root.find("block[@name='parameters']")
    for el in (params if params is not None else []):
        name = el.find("field[@name='name']").text
        kind = el.find("field[@name='type']").text.split(',')[1]
        p = {'type': kind}
        bm = el.find("tag_reference[@name='bitmap']")
        if kind == 'bitmap': p['bitmap'] = bm.text if bm is not None else None
        elif kind == 'value': p['value'] = float(el.find("field[@name='const value']").text)
        elif kind == 'color': p['color'] = el.find("field[@name='const color']").text
        anims = el.find("block[@name='animation properties']")
        for a in (anims if anims is not None else []):
            atype = a.find("field[@name='type']").text.split(',', 1)[1]
            p.setdefault('animation', {})[atype] = function_values(a)
            tp = a.find("field[@name='time period']")
            if tp is not None and float(tp.text): p.setdefault('animation_period', {})[atype] = float(tp.text)
        entry['parameters'][name] = p
    inv[tag] = entry
Path(sys.argv[2]).write_text(json.dumps(inv, indent=1))
templates = {}
for t, e in inv.items(): templates.setdefault(e['template'], []).append(t.split('\\')[-1])
for k, v in sorted(templates.items(), key=lambda kv: -len(kv[1])): print(len(v), k, ', '.join(v))
bitmaps = {p['bitmap'] for e in inv.values() for p in e['parameters'].values() if p.get('bitmap')}
print('distinct bitmaps:', len(bitmaps))
