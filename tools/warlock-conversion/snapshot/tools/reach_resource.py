"""Read original MCC Reach U13 resource controls and verified pages, read-only.

The shipped cache uses play+60 segments and section-relative pages, unlike
workshop caches. Shared files must be supplied explicitly by the caller.
"""
import struct
import zlib
from pathlib import Path


class ReachResource:
    def __init__(self, cache, datum, shared_paths=None, decoded_pages=None):
        self.c = cache
        zone = next(t['offset'] for t in cache.tags.values() if t['group'] == 'zone')
        records = cache.block(zone + 100, 64)
        index = datum & 65535
        if index >= len(records):
            raise ValueError('Reach resource index outside gestalt')
        record = records[index]
        if struct.unpack_from('<H', cache.data, record + 16)[0] != datum >> 16:
            raise ValueError('Reach resource salt mismatch')
        start, length = struct.unpack_from('<II', cache.data, record + 20)
        total = cache.u(zone + 0x148)
        if start + length > total:
            raise ValueError('Reach control slice outside gestalt')
        base = cache.pointer(cache.u(zone + 0x154))
        self.data = bytes(cache.data[base + start:base + start + length])
        self.root = cache.u(record + 36) & 0x1fffffff
        self.fix = {cache.u(p): cache.u(p + 4) for p in cache.block(record + 40, 8)}
        if self.root >= length or any(p + 4 > length for p in self.fix):
            raise ValueError('Reach resource fixup outside control data')
        self.raw = []
        segment = struct.unpack_from('<h', cache.data, record + 34)[0]
        if segment < 0:
            return
        play = next(t['offset'] for t in cache.tags.values() if t['group'] == 'play')
        row = cache.block(play + 60, 16)[segment]
        indices = struct.unpack_from('<hh', cache.data, row)
        offsets = struct.unpack_from('<II', cache.data, row + 4)
        for page_index, offset in zip(indices, offsets):
            if page_index < 0:
                self.raw.append(b'')
                continue
            key = (str(cache.file.name), page_index)
            raw = decoded_pages.get(key) if decoded_pages is not None else None
            if raw is None:
                page = cache.block(play + 24, 88)[page_index]
                shared = struct.unpack_from('<h', cache.data, page + 4)[0]
                block, compressed, size, crc = struct.unpack_from('<IIII', cache.data, page + 8)
                codec = cache.data[page + 3]
                if size > 512 * 1024 * 1024:
                    raise ValueError('Reach resource page exceeds reader allocation limit')
                if shared == -1:
                    base = (cache.u(1252) + cache.u(1232)) & 0xffffffff
                    payload = cache.data[base + block:base + block + compressed]
                else:
                    files = cache.block(play + 12, 264)
                    if not 0 <= shared < len(files):
                        raise ValueError('Invalid Reach shared cache index')
                    at = files[shared]
                    name = cache.data[at:at + 256].split(b'\0')[0].decode('ascii')
                    if not shared_paths or name not in shared_paths:
                        raise ValueError(f'Explicit shared cache mapping required: {name}')
                    with Path(shared_paths[name]).open('rb') as stream:
                        header = stream.read(1280)
                        if len(header) != 1280 or header[:8] != b'daeh\r\0\0\0':
                            raise ValueError('Expected U13 shared cache header')
                        base = (struct.unpack_from('<I', header, 1252)[0] +
                                struct.unpack_from('<I', header, 1232)[0]) & 0xffffffff
                        stream.seek(base + block)
                        payload = stream.read(compressed)
                if len(payload) != compressed:
                    raise ValueError('Truncated Reach resource page')
                if codec == 0:
                    decoder = zlib.decompressobj(-15)
                    raw = decoder.decompress(payload, size + 1)
                    if not decoder.eof or decoder.unused_data:
                        raise ValueError('Invalid Reach compressed page framing')
                elif codec == 255:
                    raw = bytes(payload)
                else:
                    raise ValueError(f'Unsupported Reach compression codec {codec}')
                if len(raw) != size or (crc and (zlib.crc32(raw) ^ 0xffffffff) != crc):
                    raise ValueError('Reach page size/checksum mismatch')
                if decoded_pages is not None:
                    decoded_pages[key] = raw
            if offset > len(raw):
                raise ValueError('Reach segment outside resource page')
            self.raw.append(memoryview(raw)[offset:])

    def unpack(self, fmt, at):
        return struct.unpack_from('<' + fmt, self.data, at)

    def ptr(self, at):
        address = self.fix[at]
        if address & 0xe0000000 != 0x20000000:
            raise ValueError('Expected Reach control-data pointer')
        return address & 0x1fffffff

    def buffers(self, which):
        if which not in ('vertex', 'index'):
            raise ValueError('Unknown render buffer kind')
        at = self.root + (24 if which == 'vertex' else 36)
        count = self.unpack('I', at)[0]
        if not count:
            return []
        table = self.ptr(at + 4)
        if count > 65536 or table + count * 12 > len(self.data):
            raise ValueError('Reach buffer table outside control data')
        return [self.ptr(table + i * 12) for i in range(count)]


def convert_render_resource(source, lighting_bindings=None, water_buffers=None,index_replacements=None,index_additions=()):
    """Normalize Reach's expanded index descriptor for the H3 stream converter.

    Reach MCC rigid vertices use float4 positions, ushort2 UVs and two short4
    basis vectors. H3 MCC instead packs positions and includes a binormal.
    Index descriptors add four bytes after the primitive type; do not interpret
    that padding as the allocation size (which silently creates empty meshes).
    Explicit triangle-list replacements/additions support split meshes while
    retaining original vertex numbering. Callers must update mesh metadata and
    collision references to match; this function only writes resource buffers.
    """
    from render_resource import convert_render_resource as convert_h3
    import copy
    normalized = copy.copy(source)
    normalized.data = bytearray(source.data)
    normalized.fix = dict(source.fix)
    normalized.raw = list(source.raw)
    primary = bytearray(source.raw[0])
    vertices = source.buffers('vertex')
    indices = source.buffers('index')
    lighting_bindings = lighting_bindings or {}
    required_lighting = {i for i, at in enumerate(vertices) if source.unpack('H', at + 4)[0] == 6}
    if set(lighting_bindings) != required_lighting:
        raise ValueError('Reach lighting buffers require complete Lbsp bindings')
    for vertex_index, at in enumerate(vertices):
        count, fmt, stride = source.unpack('IHH', at)
        if (fmt, stride) not in ((1, 36), (2, 36), (4, 4), (6, 4), (9, 4), (26,12), (27,24), (28,128)):
            raise ValueError(f'Reach vertex format requires review: {fmt}/{stride}')
        if fmt == 6:
            import numpy as np
            from reach_lighting import decode_static_lighting, lighting_coefficients, pack_lighting_coefficients
            binding = lighting_bindings[vertex_index]
            pointer = source.fix[at + 20]
            segment = {0x40000000: 0, 0x60000000: 1}[pointer & 0xe0000000]
            start = pointer & 0x1fffffff
            size = source.unpack('I', at + 8)[0]
            if size != count * stride or start + size > len(source.raw[segment]):
                raise ValueError('Invalid Reach lighting allocation')
            payload = source.raw[segment][start:start + size]
            prefix = binding['prefix_vertices']
            if not isinstance(prefix, int) or not 0 <= prefix <= 65535:
                raise ValueError('Reach lighting prefix outside native vertex limits')
            native = bytes([0xcd]) * (prefix * 20) + pack_lighting_coefficients(
                lighting_coefficients(decode_static_lighting(payload, binding['hdr_scale'])))
            # Feed the existing H3 assembler its MCC representation; its normal
            # lighting conversion restores these exact signed Xbox bytes.
            signed = np.frombuffer(native, dtype=np.int8).reshape(-1, 4)
            intermediate = (signed[:, ::-1].astype(np.int16) + 127).astype(np.uint8).tobytes()
            target_count = len(native) // 20
            struct.pack_into('<IHHI', normalized.data, at, target_count, 6, 20, len(intermediate))
            normalized.fix[at + 20] = 0x40000000 | len(primary)
            primary.extend(intermediate)
        if fmt == 2:
            import numpy as np
            pointer = source.fix[at + 20]
            segment = {0x40000000: 0, 0x60000000: 1}[pointer & 0xe0000000]
            start = pointer & 0x1fffffff
            payload = source.raw[segment][start:start + count * stride]
            if len(payload) != count * stride:
                raise ValueError('Truncated Reach rigid vertex payload')
            position = np.ndarray((count, 4), dtype='<f4', buffer=payload,
                                  strides=(stride, 4)).astype(float)
            if (not np.all(np.isfinite(position)) or
                    np.any(position < -1e-6) or np.any(position > 1.000001)):
                raise ValueError('Reach rigid position outside compressed bounds')
            raw = np.frombuffer(payload, dtype=np.uint8).reshape(count, stride)
            converted = np.zeros((count, 36), dtype=np.uint8)
            packed = np.rint(np.clip(position, 0, 1)*65535).astype('<u2')
            # Reach position.W encodes tangent handedness. H3's homogeneous
            # position is one; its separate binormal carries handedness.
            packed[:, 3] = 65535
            converted[:, :8] = packed.view(np.uint8).reshape(count, 8)
            converted[:, 8:12] = raw[:, 16:20]
            converted[:, 12:28] = raw[:, 20:36]
            normal = np.ndarray((count, 3), dtype='<i2', buffer=payload, offset=20,
                                strides=(stride, 2)).astype(float)/32767
            tangent = np.ndarray((count, 3), dtype='<i2', buffer=payload, offset=28,
                                 strides=(stride, 2)).astype(float)/32767
            binormal = np.cross(np.clip(normal,-1,1),np.clip(tangent,-1,1))
            binormal *= (position[:, 3]*2-1)[:, None]
            basis = np.zeros((count, 4), dtype='<i2')
            basis[:, :3] = np.rint(np.clip(binormal,-1,1)*32767).astype('<i2')
            converted[:, 28:36] = basis.view(np.uint8).reshape(count,8)
            normalized.fix[at + 20] = 0x40000000 | len(primary)
            primary.extend(converted.tobytes())
    normalized.raw[0] = primary
    normalized_indices = []
    index_replacements=index_replacements or {}
    if any(not 0<=i<len(indices) for i in index_replacements):raise ValueError('Index replacement outside resource')
    for index_slot,at in enumerate(indices):
        primitive, padding, size = source.unpack('III', at)
        if padding:
            raise ValueError('Nonzero Reach index descriptor extension')
        new = len(normalized.data)
        normalized.data.extend(struct.pack('<II', primitive, size) + bytes(16))
        normalized.fix[new + 16] = source.fix[at + 20]
        if index_slot in index_replacements:
            replacement=index_replacements[index_slot]
            if primitive!=3 or not replacement or len(replacement)%6:raise ValueError('Invalid replacement triangle buffer')
            struct.pack_into('<I',normalized.data,new+4,len(replacement))
            normalized.fix[new+16]=0x40000000|len(primary)
            primary.extend(replacement)
        normalized_indices.append(new)
    for payload in index_additions:
        if not payload or len(payload)%6:raise ValueError('Invalid appended triangle buffer')
        if len(normalized_indices)>=32768:raise ValueError('Index buffer slot exceeds native signed index')
        new=len(normalized.data)
        normalized.data.extend(struct.pack('<II',3,len(payload))+bytes(16))
        normalized.fix[new+16]=0x40000000|len(primary)
        primary.extend(payload)
        normalized_indices.append(new)
    normalized.raw[0]=primary
    normalized.buffers = lambda which: vertices if which == 'vertex' else normalized_indices
    from render_buffers import convert_vertices
    from reach_world_vertices import convert_world_vertices

    def convert_reach_vertex(payload, count, fmt, stride):
        if fmt==26:
            if stride!=12 or len(payload)!=count*12:raise ValueError('Invalid Reach water triangle allocation')
            return b''.join(struct.pack('>6H',*row) for row in struct.iter_unpack('<6H',payload)),12
        if fmt == 1:
            if stride != 36:
                raise ValueError('Unexpected Reach world vertex stride')
            return convert_world_vertices(payload, count), 32
        return convert_vertices(payload, count, fmt, stride)

    return convert_h3(normalized, water_buffers=water_buffers, vertex_converter=convert_reach_vertex)

