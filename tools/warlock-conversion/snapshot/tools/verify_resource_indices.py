"""Validate all typed resource references in a serialized retail cache."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--map', required=True)
a = p.parse_args()
c = Cache(a.map)
reference = Path(__file__).resolve().parents[1] / 'reference/plugins'
zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
resources = c.block(zone + 88, 64)
visited, checked = set(), set()

def walk(at, schema):
    key = at, id(schema)
    if key in visited:
        return
    visited.add(key)
    for field in schema:
        if 'offset' not in field.attrib:
            continue
        pos = at + int(field.get('offset'), 0)
        if field.tag.lower() == 'tagblock':
            for row in c.block(pos, int(field.get('elementSize'), 0)):
                walk(row, field)
        elif field.tag.lower() == 'datum' and '[zone]' in field.get('name', ''):
            datum = c.u(pos)
            if datum == 0xffffffff:
                continue
            index = datum & 65535
            if index >= len(resources) or c.unpack('H', resources[index] + 16)[0] != datum >> 16:
                raise ValueError(f'Invalid resource reference {datum:#x} at {pos:#x}')
            checked.add(pos)

try:
    schemas = {}
    for tag in c.tags.values():
        group = tag['group'].strip()
        path = reference / (group + '.xml')
        if group not in schemas and path.exists():
            schemas[group] = ET.parse(path).getroot()
        schema = schemas.get(group)
        if schema is not None and any('[zone]' in f.get('name', '') for f in schema.iter()):
            walk(tag['offset'], schema)
    print(json.dumps({'resource_slots': len(resources), 'typed_references_verified': len(checked)}))
finally:
    c.close()
