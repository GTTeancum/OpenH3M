"""Explicit MCC-to-retail BSP metadata layout adapters."""
import copy
import struct
from bisect import bisect_right
from pathlib import Path
import xml.etree.ElementTree as ET
from collision_physics import convert_collision_block


def decorator_group(converter, at, schema, target, path):
    from resource_reader import Resource
    source = converter.source
    resource = getattr(converter, '_decorator_resource', None)
    if resource is None:
        bsps = [t for t in source.tags.values() if t['group'] == 'sbsp']
        if len(bsps) != 1:
            raise ValueError('Decorator conversion needs an unambiguous source BSP')
        root_schema = ET.parse(Path(__file__).resolve().parents[1] / 'reference/mcc/sbsp.xml').getroot()
        field = next(f for f in root_schema if f.get('name') == '[zone] Asset Datum 1')
        resource = Resource(source, source.u(bsps[0]['offset'] + int(field.get('offset'), 0)))
        converter._decorator_resource = resource
    count, set_index, buffer_index, offset = source.unpack('hbbI', at)
    buffers = resource.buffers('vertex')
    if count < 0 or set_index < 0 or not 0 <= buffer_index < len(buffers) or offset % 16:
        raise ValueError(f'{path}: invalid decorator buffer binding')
    descriptor = buffers[buffer_index]
    total, fmt, stride = resource.unpack('IHH', descriptor)
    if fmt != 20 or stride != 16 or offset + count * 16 > total * 16:
        raise ValueError(f'{path}: decorator instances outside TinyPosition buffer')
    starts = [source.unpack('h', row)[0] for row in source.block(at + 48, 2)]
    if starts != sorted(starts) or any(v < 0 or v > count for v in starts):
        raise ValueError(f'{path}: invalid decorator model boundaries')
    pointer = resource.fix[descriptor + 20]
    segment = (pointer >> 29) - 2
    base = (pointer & 0x1fffffff) + offset
    if segment not in (0, 1) or segment >= len(resource.raw) or base + count * 16 > len(resource.raw[segment]):
        raise ValueError(f'{path}: decorator payload outside resource')
    for i in range(count):
        variant = struct.unpack_from('<H', resource.raw[segment], base + i * 16 + 6)[0]
        if variant >> 8 != bisect_right(starts, i):
            raise ValueError(f'{path}: model boundaries disagree with instance variants')
    # Retail consumes the model selector encoded in each TinyPosition vertex;
    # its 48-byte group has no MCC draw-boundary acceleration block.
    schema = copy.deepcopy(schema)
    schema.set('name', 'Verified decorator fields')
    schema.set('elementSize', '0x30')
    for node in list(schema):
        if node.get('name') == 'Model Start Index':
            schema.remove(node)
    return converter.convert(at, schema, target, path + '/verified')


def convert_bsp_block(converter, at, source_schema, target_schema, path):
    if not path.startswith('sbsp:'):
        return None
    name = source_schema.get('name')
    if name == 'Decorator Groups':
        return decorator_group(converter, at, source_schema, target_schema, path)
    if name == 'Collision MOPP Codes':
        schema = copy.deepcopy(source_schema)
        schema.set('name', 'MOPP Codes')
        return convert_collision_block(converter, at, schema, target_schema, 'coll:' + path)
    if name != 'Clusters':
        return None
    if source_schema.get('elementSize') != '0x118' or target_schema.get('elementSize') != '0xDC':
        raise ValueError('Unsupported BSP cluster layout')
    source = converter.source

    def section(schema, start, end):
        result = copy.deepcopy(schema)
        result.set('name', 'Cluster fields')
        result.set('elementSize', hex(end - start))
        for node in list(result):
            offset = node.get('offset')
            if offset is None or not start <= int(offset, 0) < end:
                result.remove(node)
            else:
                node.set('offset', hex(int(offset, 0) - start))
        return result

    out = bytearray(0xdc)
    out[:0x48] = converter.convert(at, section(source_schema, 0, 0x48),
                                  section(target_schema, 0, 0x48), path + '/fields')
    out[0x9c:] = converter.convert(at + 0xd8, section(source_schema, 0xd8, 0x118),
                                   section(target_schema, 0x9c, 0xdc), path + '/fields')
    # Runtime pointers, alignment padding and user-data offsets are zero in
    # serialized H3 clusters. Reject resident/unsupported layouts explicitly.
    for offset in (0x48, 0x58, 0x68, 0x70, 0x90, 0xa0, 0xb0, 0xb8, 0xc0):
        if source.unpack('Q', at + offset)[0]:
            raise ValueError(f'{path}: nonzero cluster runtime field at {offset:#x}')
    for offset in (0x54, 0x64, 0x8c, 0x9c, 0xac, 0xd4):
        if source.u(at + offset):
            raise ValueError(f'{path}: nonzero cluster padding at {offset:#x}')
    for src, dst, fmt in ((0x50, 0x4c, 'HH'), (0x60, 0x54, 'I'),
                          (0x88, 0x70, 'I'), (0x98, 0x78, 'HH'), (0xa8, 0x80, 'I')):
        struct.pack_into('>' + fmt, out, dst, *source.unpack(fmt, at + src))
    owner = source.u(at + 0x84)
    if owner == 0xffffffff:
        group, datum = 'sbsp', owner
    else:
        group, datum = converter.tag_reference(owner)
        if group != 'sbsp':
            raise ValueError('Cluster owner is not a BSP')
    out[0x60:0x64] = group.encode('ascii')
    struct.pack_into('>I', out, 0x6c, datum)
    ss = next(f for f in source_schema if f.get('name') == 'Collision MOPP Codes')
    ds = next(f for f in target_schema if f.get('name') == 'Collision MOPP Codes')
    rows = source.block(at + 0xc8, 64)
    payload = b''.join(convert_bsp_block(converter, row, ss, ds, path + '/Collision MOPP Codes')
                       for row in rows)
    struct.pack_into('>III', out, 0x90, len(rows), converter.builder.alloc(payload) if rows else 0, 0)
    return bytes(out)
