"""Explicit MCC-to-retail BSP metadata layout adapters."""
import copy
import struct
from collision_physics import convert_collision_block


def convert_bsp_block(converter, at, source_schema, target_schema, path):
    if not path.startswith('sbsp:'):
        return None
    name = source_schema.get('name')
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
