"""Pack retired resource slots and remap typed references and residency bits."""
import struct
import xml.etree.ElementTree as ET


def compact_resource_indices(importer):
    r, b = importer.registry, importer.builder
    retired = getattr(r, 'retired_resources', set())
    count = len(r.resources) // 64
    mapping = {old: new for new, old in enumerate(i for i in range(count) if i not in retired)}
    if not retired:
        return {'before': count, 'after': count, 'references': 0}
    schemas, visited = {}, set()
    references = 0
    remapped_references, remapped_bits = set(), set()

    def word(address):
        if not b.base <= address <= b.base + len(b.meta) - 4:
            raise ValueError('Resource reference pointer outside metadata')
        return struct.unpack('>I', b.read(address, 4))[0]

    def walk(address, schema):
        nonlocal references
        key = address, id(schema)
        if key in visited:
            return
        visited.add(key)
        for f in schema:
            if 'offset' not in f.attrib:
                continue
            at = address + int(f.get('offset'), 0)
            kind = f.tag.lower()
            if kind == 'tagblock':
                n, pointer = word(at), word(at + 4)
                stride = int(f.get('elementSize'), 0)
                if n > 1000000 or n and (pointer < b.base or pointer + n * stride > b.base + len(b.meta)):
                    raise ValueError('Resource reference block outside metadata')
                for j in range(n):
                    walk(pointer + j * stride, f)
            elif kind == 'datum' and '[zone]' in f.get('name', ''):
                if at in remapped_references:
                    continue
                remapped_references.add(at)
                datum = word(at)
                if datum == 0xffffffff:
                    continue
                old = datum & 65535
                if old >= count or datum >> 16 != struct.unpack_from('>H', r.resources, old * 64 + 16)[0]:
                    # Stripped retail references are deliberately invalid.
                    b.put(at, 'I', 0xffffffff)
                    continue
                if old not in mapping:
                    raise ValueError('Live tag references a retired resource')
                b.put(at, 'I', (datum & 0xffff0000) | mapping[old])
                references += 1

    for index in range(len(r.tags) // 8):
        group, salt, address = struct.unpack_from('>HHI', r.tags, index * 8)
        if group == 65535 or not address:
            continue
        name = r.cache.groups[group].strip()
        path = importer.reference / 'plugins' / (name + '.xml')
        if name not in schemas and path.exists():
            schemas[name] = ET.parse(path).getroot()
        schema = schemas.get(name)
        if schema is not None and any('[zone]' in f.get('name', '') for f in schema.iter()):
            walk(address, schema)

    schema = ET.parse(importer.reference / 'plugins/zone.xml').getroot()
    root = r.address(r.zone)
    for field in schema:
        name = field.get('name', '')
        if field.tag.lower() != 'tagblock':
            continue
        at = root + int(field.get('offset'), 0)
        if name.startswith('Prediction '):
            # Optional original-map prefetch hints refer to the original graph.
            b.put(at, 'III', 0, 0, 0)
        if 'Manifest' not in name:
            continue
        n, pointer = word(at), word(at + 4)
        stride = int(field.get('elementSize'), 0)
        for j in range(n):
            for block in field:
                if block.tag.lower() != 'tagblock' or 'Resource' not in block.get('name', '') or 'Bits' not in block.get('name', ''):
                    continue
                pos = pointer + j * stride + int(block.get('offset'), 0)
                length, bits = word(pos), word(pos + 4)
                if bits in remapped_bits:
                    continue
                remapped_bits.add(bits)
                packed = [0] * length
                for old, new in mapping.items():
                    if old // 32 < length and word(bits + old // 32 * 4) & (1 << (old % 32)):
                        packed[new // 32] |= 1 << (new % 32)
                for k, value in enumerate(packed):
                    b.put(bits + k * 4, 'I', value)
    r.resources = bytearray(b''.join(r.resources[i * 64:(i + 1) * 64] for i in mapping))
    r.first_resource = sum(i < r.first_resource for i in mapping)
    return {'before': count, 'after': len(mapping), 'references': references,
            'old_to_new': {str(old): new for old, new in mapping.items()},
            'original_prediction_hints_cleared': True}
