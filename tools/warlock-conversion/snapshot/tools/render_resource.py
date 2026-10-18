"""Assemble retail render resource controls, fixups, interops and GPU payload.

The caller still must register these in zone/play and active resource manifests.
All source buffers must be supported; there is no partial-resource result.
"""
import struct
from render_buffers import convert_vertices, convert_indices


def convert_render_resource(source, water_buffers=None):
    vertices, indices = source.buffers('vertex'), source.buffers('index')
    water_buffers = water_buffers or {}
    required_water = {index for index, at in enumerate(vertices) if source.unpack('H', at + 4)[0] in (27, 28)}
    if set(water_buffers) != required_water:
        raise ValueError('Water render buffers require complete mesh-topology reconstruction')
    control = bytearray(48)
    raw = bytearray()
    fixups, interops = [], []

    def alloc(data):
        start = len(control)
        control.extend(data)
        return start

    def gpu(data):
        raw.extend(bytes((-len(raw)) % 16))
        start = len(raw)
        raw.extend(data)
        return start

    def source_payload(pointer_field, size):
        address = source.fix[pointer_field]
        segment = {0x40000000: 0, 0x60000000: 1}.get(address & 0xe0000000)
        if segment is None or segment >= len(source.raw):
            raise ValueError('Unsupported render resource payload address')
        start = address & 0x1fffffff
        if start + size > len(source.raw[segment]):
            raise ValueError('Render buffer exceeds its resource page')
        return source.raw[segment][start:start + size]

    for which, buffers, block_offset, interop_type in (
            ('vertex', vertices, 24, 0), ('index', indices, 36, 1)):
        table = alloc(bytes(12 * len(buffers))) if buffers else 0
        struct.pack_into('>I', control, block_offset, len(buffers))
        if buffers:
            fixups.append((block_offset + 4, 0x20000000 | table))
        for i, at in enumerate(buffers):
            if which == 'vertex':
                count, fmt, stride = source.unpack('IHH', at)
                size = source.unpack('I', at + 8)[0]
                if size != count * stride:
                    raise ValueError('Source vertex allocation is not count * stride')
                if i in water_buffers:
                    target_count, target_fmt, target_stride, data = water_buffers[i]
                    expected = (27, 36) if fmt == 27 else (26, 12)
                    if (target_fmt, target_stride) != expected or target_count < 0 or len(data) != target_count * target_stride:
                        raise ValueError('Invalid reconstructed native water buffer')
                    count, fmt = target_count, target_fmt
                else:
                    data, target_stride = convert_vertices(source_payload(at + 20, size), count, fmt, stride)
                descriptor = bytearray(28)
                struct.pack_into('>IHHI', descriptor, 0, count, fmt, target_stride, len(data))
                pointer_offset = 20
            else:
                primitive, size = source.unpack('II', at)
                if not 0 <= primitive <= 6:
                    raise ValueError(f'Unsupported index primitive {primitive}')
                data = convert_indices(source_payload(at + 16, size))
                descriptor = bytearray(24)
                struct.pack_into('>II', descriptor, 0, primitive, len(data))
                pointer_offset = 16
            descriptor_offset = alloc(descriptor)
            entry = table + i * 12
            fixups.extend(((entry, 0x20000000 | descriptor_offset),
                           (descriptor_offset + pointer_offset, 0x40000000 | gpu(data))))
            interops.append((0x20000000 | entry, interop_type))
    return {'control': bytes(control), 'raw': bytes(raw), 'root': 0,
            'fixups': fixups, 'interops': interops,
            'vertex_buffers': len(vertices), 'index_buffers': len(indices)}
