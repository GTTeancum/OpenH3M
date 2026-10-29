"""Reconstruct retail water corner parameters/triangle indices from MCC parts."""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


def rebuild_water_buffers(cache, bsp_offset, resource):
    if not cache.mcc:
        raise ValueError('Water reconstruction expects MCC source geometry')
    schema = ET.parse(Path(__file__).resolve().parents[1] / 'reference/mcc/sbsp.xml').getroot()
    # The schema also labels the earlier decorator geometry block "Meshes".
    mesh_field = next(node for node in schema if node.get('name') == 'Meshes'
                      and int(node.get('offset'), 0) == 0x2F4)
    meshes = cache.block(bsp_offset + int(mesh_field.get('offset'), 0), int(mesh_field.get('elementSize'), 0))
    vertices, indices = resource.buffers('vertex'), resource.buffers('index')
    result = {}

    def payload(at, size):
        address = resource.fix[at]
        segment = {0x40000000: 0, 0x60000000: 1}.get(address & 0xe0000000)
        offset = address & 0x1fffffff
        if segment is None or segment >= len(resource.raw) or offset + size > len(resource.raw[segment]):
            raise ValueError('Water payload exceeds resource page')
        return resource.raw[segment][offset:offset + size]

    for mesh_index, mesh in enumerate(meshes):
        parts = [row for row in cache.block(mesh, 16) if cache.data[row + 13] & 8]
        if not parts:
            continue
        buffers = cache.unpack('8h', mesh + 24)
        triangle_slot, parameter_slot = buffers[6:8]
        index_slot = cache.unpack('h', mesh + 40)[0]
        if not all(0 <= slot < len(vertices) for slot in (triangle_slot, parameter_slot, buffers[0])) or not 0 <= index_slot < len(indices):
            raise ValueError('Water mesh has invalid buffer bindings')
        pa, ta, ia = vertices[parameter_slot], vertices[triangle_slot], indices[index_slot]
        if resource.unpack('I', ia)[0] != 3:
            raise ValueError('Water reconstruction requires a triangle-list index buffer')
        allocated_count, fmt, stride = resource.unpack('IHH', pa)
        if (fmt, stride) != (27, 36) or resource.unpack('IHH', ta)[1:] != (28, 128):
            raise ValueError('Unsupported MCC water allocation layout')
        allocation_size = resource.unpack('I', pa + 8)[0]
        if allocation_size != allocated_count * stride:
            raise ValueError('Water parameter allocation size mismatch')
        raw = payload(pa + 20, allocation_size)
        index_data = payload(ia + 16, resource.unpack('I', ia + 4)[0])
        mesh_vertex_count = resource.unpack('I', vertices[buffers[0]])[0]
        parameters, triangles = bytearray(), bytearray()
        corner = 0
        for part in parts:
            start, count = cache.unpack('HH', part + 4)
            if start % 3 or count % 3 or start + count > allocated_count or (start + count) * 2 > len(index_data):
                raise ValueError('Water part exceeds source buffers or is not a triangle list')
            for source_corner in range(start, start + count):
                vertex = struct.unpack_from('<H', index_data, source_corner * 2)[0]
                if vertex >= mesh_vertex_count or corner > 65535:
                    raise ValueError('Water triangle index exceeds native ushort range')
                # Observed MCC layout is packed float3 local info + float3 UV;
                # native pads local info to six words before the three UV words.
                values = struct.unpack_from('<6I', raw, source_corner * 24)
                parameters.extend(struct.pack('>9I', *values[:3], 0, 0, 0, *values[3:]))
                triangles.extend(struct.pack('>HH', vertex, corner))
                corner += 1
        for slot, record in ((parameter_slot, (corner, 27, 36, bytes(parameters))),
                             (triangle_slot, (corner // 3, 26, 12, bytes(triangles)))):
            if slot in result and result[slot] != record:
                raise ValueError('Shared water buffer has conflicting mesh reconstruction')
            result[slot] = record
    return result
