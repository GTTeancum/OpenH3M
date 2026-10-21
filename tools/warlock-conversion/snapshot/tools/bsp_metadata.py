"""Explicit MCC-to-retail BSP metadata layout adapters."""
import copy
import struct
from bisect import bisect_right
from pathlib import Path
import xml.etree.ElementTree as ET
from collision_physics import convert_collision_block


def convert_bsp_root(converter, at, schema, target, path):
    from resource_reader import Resource
    source = converter.source
    if source.u(at + 0xc) & ~1 or source.u(at + 0x398):
        raise ValueError('Unsupported MCC BSP root flags/padding')
    schema = copy.deepcopy(schema)
    schema.set('name', 'Normalized BSP Root')
    for node in list(schema):
        offset = int(node.get('offset', '-1'), 0)
        if node.get('name') == 'Unknown Raw Leaves':
            node.set('name', 'Leaves')
        if offset == 0x38c:
            node.set('name', '[zone] Tag Resources Asset Datum')
        if offset in (0xc, 0x394, 0x398):
            schema.remove(node)
    out = bytearray(converter.convert(at, schema, target, path))
    resource = Resource(source, source.u(at + 0x394))
    if len(resource.data) != 48 or resource.root != 0 or resource.unpack('I', 36)[0]:
        raise ValueError('Unsupported BSP cache-file resource/pathfinding data')
    consumed = set()
    for src, dst, source_fmt, target_fmt in ((0, 0x54, 'ii', 'Hh'),
                                            (12, 0x60, '2H', '2H'),
                                            (24, 0x18, '2H', '2H')):
        # Both locations must not contain competing authored arrays.
        if struct.unpack_from('>I', out, dst)[0]:
            raise ValueError('BSP array exists in both metadata and resource')
        count = resource.unpack('I', src)[0]
        if not count:
            continue
        pointer = resource.fix[src + 4]
        consumed.add(src + 4)
        segment, offset = (pointer >> 29) - 2, pointer & 0x1fffffff
        size = count * struct.calcsize('<' + source_fmt)
        if segment not in (0, 1) or segment >= len(resource.raw) or offset + size > len(resource.raw[segment]):
            raise ValueError('BSP cache-file array outside resource')
        data = resource.raw[segment][offset:offset + size]
        partition = getattr(converter, 'gulch_partition', None)
        if partition and src in (0, 24):
            order = partition[1]['surfaces' if src == 0 else 'edges']
            stride = struct.calcsize('<' + source_fmt)
            if any(old >= count for old in order):
                raise ValueError('Partition metadata index outside original array')
            data = b''.join(data[old*stride:(old+1)*stride] for old in order)
            count = len(order)
        try:
            payload = b''.join(struct.pack('>' + target_fmt, *v)
                               for v in struct.iter_unpack('<' + source_fmt, data))
        except struct.error as exc:
            raise ValueError('BSP surface mapping exceeds retail limits') from exc
        struct.pack_into('>III', out, dst, count, converter.builder.alloc(payload), 0)
    if consumed != set(resource.fix):
        raise ValueError('Unconsumed BSP cache-file resource fixups')
    partition = getattr(converter, 'gulch_partition', None)
    if partition:
        # Rebuild the root leaf-to-render-cluster table using the exact leaf map.
        rows = source.block(at + 0x34, 1)
        leaf_map = partition[1]['leaves']
        if any(old >= len(rows) for old in leaf_map):
            raise ValueError('Partition leaf cluster index outside source')
        payload = bytes(source.data[rows[old]] for old in leaf_map)
        struct.pack_into('>III', out, 0x30, len(payload), converter.builder.alloc(payload), 0)
    return bytes(out)


def decorator_group(converter, at, schema, target, path):
    from resource_reader import Resource
    source = converter.source
    resource = getattr(converter, '_decorator_resource', None)
    if resource is None:
        bound = getattr(converter, 'source_bsp', None)
        bsps = [bound] if bound is not None else [t for t in source.tags.values() if t['group'] == 'sbsp']
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
    partition = getattr(converter, 'gulch_partition', None)
    if partition and name in ('Edge Mapping', 'Cluster Portals'):
        schema = copy.deepcopy(source_schema)
        schema.set('name', 'Partition remapped fields')
        out = bytearray(converter.convert(at, schema, target_schema, path + '/remapped'))
        field_offset = 0 if name == 'Edge Mapping' else 4
        table = partition[1]['edges' if name == 'Edge Mapping' else 'planes']
        old = converter.source.unpack('i', at + field_offset)[0]
        if old not in table:
            raise ValueError('Partition lost required seam edge or portal plane')
        struct.pack_into('>i', out, field_offset, table[old])
        return bytes(out)
    if source_schema.get('baseSize') and name != 'Normalized BSP Root':
        return convert_bsp_root(converter, at, source_schema, target_schema, path)
    if name == 'Instanced Geometry Instances':
        # Preserve bit 5 exactly as in the accepted retail map. The bundled
        # original plugin omits its label; do not shift it to another bit.
        target = copy.deepcopy(target_schema)
        flags = next(f for f in target if f.get('name') == 'Flags')
        ET.SubElement(flags, 'bit', name='Not For Render', index='5')
        schema = copy.deepcopy(source_schema)
        schema.set('name', 'Instance fields')
        return converter.convert(at, schema, target, path)
    if name == 'BSP Physics':
        return convert_collision_block(converter, at, source_schema, target_schema, 'coll:' + path)
    if name == 'Decorator Groups':
        return decorator_group(converter, at, source_schema, target_schema, path)
    if name in ('Collision MOPP Codes', 'MOPP Codes'):
        schema = copy.deepcopy(source_schema)
        schema.set('name', 'MOPP Codes')
        transform = None
        if partition and name == 'MOPP Codes':
            from resource_reader import Resource
            from forge_mopp import remap_surfaces
            root = converter.source_bsp['offset']
            sidecar = Resource(converter.source, converter.source.u(root + 0x394))
            surface_count = sidecar.unpack('I', 0)[0]
            instance_count = converter.source.u(root + 0x1c0)
            transform = lambda code: remap_surfaces(code, partition[1]['surfaces'],
                                                    surface_count, instance_count)
        return convert_collision_block(converter, at, schema, target_schema, 'coll:' + path,
                                       mopp_transform=transform)
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
