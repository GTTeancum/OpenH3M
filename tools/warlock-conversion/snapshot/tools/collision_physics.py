"""Translate MCC collision shapes and MOPP headers to Halo 3 retail layouts.

Offsets follow TagTool CollisionGeometryShape/HavokTypes, which include the MCC
large-BSP pointer missing from the older Assembly collision XML description.
"""
import struct


def convert_packed_mopp(payload):
    """Convert aligned 48-byte MCC MOPP headers used by lightmap mesh data."""
    result = bytearray()
    offset = 0
    while offset < len(payload):
        if offset + 48 > len(payload):
            raise ValueError('Truncated packed MOPP header')
        if any(struct.unpack_from('<Q', payload, offset + p)[0] for p in (0, 32)):
            raise ValueError('Packed MOPP contains runtime pointers')
        size, capacity = struct.unpack_from('<II', payload, offset + 40)
        end = offset + 48 + size
        aligned = (end + 15) & ~15
        if end > len(payload) or aligned > len(payload) or (capacity & 0x7fffffff) < size:
            raise ValueError('Packed MOPP code exceeds allocation')
        header = bytearray(48)
        struct.pack_into('>HH', header, 4, *struct.unpack_from('<HH', payload, offset + 8))
        struct.pack_into('>4I', header, 16, *struct.unpack_from('<4I', payload, offset + 16))
        struct.pack_into('>II', header, 36, size, capacity)
        result.extend(header)
        result.extend(retail_mopp(payload[offset + 48:end]))
        # MCC allocator padding can contain stale bytes, never serialized state.
        result.extend(bytes(aligned - end))
        offset = aligned
    return bytes(result)


def retail_mopp(code):
    out = bytearray(code)
    at = 0
    lengths = {0: 0, **dict.fromkeys(range(1, 5), 3), 5: 1, 6: 2, 7: 3, 8: 4,
               9: 1, 10: 2, 11: 4, 12: 2, 13: 5,
               **dict.fromkeys(range(0x10, 0x1d), 3),
               **dict.fromkeys(range(0x20, 0x23), 2),
               **dict.fromkeys(range(0x23, 0x26), 6),
               **dict.fromkeys(range(0x26, 0x29), 2),
               **dict.fromkeys(range(0x29, 0x2c), 6),
               **dict.fromkeys(range(0x30, 0x50), 0),
               **{0x50+i: i+1 for i in range(4)},
               **{0x54+i: i+1 for i in range(4)},
               **dict.fromkeys(range(0x60, 0x64), 1),
               **dict.fromkeys(range(0x64, 0x68), 2),
               **dict.fromkeys(range(0x68, 0x6c), 4)}
    while at < len(out):
        op = out[at]
        size = lengths.get(op)
        if size is None or at + size + 1 > len(out):
            raise ValueError(f'Unsupported/truncated MOPP opcode {op:#x} at {at}')
        if op in (0x0b, 0x53):
            key = int.from_bytes(out[at+1:at+5], 'big')
            if key & 0x83ff0000:
                raise ValueError(f'MOPP key cannot be represented in retail: {key:#x}')
            key = (key & 0x60000000) | (((key >> 26) & 7) << 16) | (key & 65535)
            out[at+1:at+5] = key.to_bytes(4, 'big')
        at += size + 1
    return bytes(out)


def convert_collision_block(converter, at, source_schema, target_schema, path):
    name = source_schema.get('name')
    design_mopp = path.startswith('sddt:') and name in ('Soft Ceiling MOPP Codes', 'Water MOPP Codes')
    if not design_mopp and (not path.startswith('coll:') or name not in ('BSP Physics', 'MOPP Codes')):
        return None
    c, b = converter.source, converter.builder
    out = bytearray(int(target_schema.get('elementSize'), 0))

    def copy(src, dst, fmt):
        struct.pack_into('>' + fmt, out, dst, *c.unpack(fmt, at + src))

    def null_pointer(offset):
        if c.unpack('Q', at + offset)[0]:
            raise ValueError(f'{path}: resident runtime pointer in serialized source')

    if name == 'BSP Physics':
        if len(out) != 0x70 or int(source_schema.get('elementSize'), 0) != 0xb0:
            raise ValueError('Unsupported collision shape layout')
        for offset in (0, 0x20, 0x58, 0x60, 0x70, 0x90, 0xa0):
            null_pointer(offset)
        for src, dst, fmt in ((8,4,'HH'), (0x18,0xc,'I'), (0x28,0x14,'BBH'),
                             (0x30,0x20,'8f'), (0x68,0x48,'bBHf'),
                             (0x78,0x54,'HH'), (0x88,0x5c,'I'),
                             (0x98,0x64,'hh'), (0xa8,0x6c,'f')):
            copy(src, dst, fmt)
        for src, dst in ((0x10,8), (0x80,0x58)):
            value = c.unpack('Q', at+src)[0]
            if value % 0xb0:
                raise ValueError('Unaligned collision shape user-data offset')
            struct.pack_into('>I', out, dst, value // 0xb0 * 0x70)
        owner = c.u(at+0x50)
        target = 0xffffffff if owner == 0xffffffff else converter.tag_reference(owner)[1]
        struct.pack_into('>I', out, 0x40, target)
    else:
        if len(out) != 64:
            raise ValueError('Unsupported MOPP header layout')
        null_pointer(0)
        null_pointer(0x20)
        copy(8,4,'HH')
        copy(0x10,0x10,'4f')
        copy(0x28,0x24,'II')
        rows = c.block(at+0x30,1)
        size = c.u(at+0x28)
        if size != len(rows):
            raise ValueError('MOPP size differs from data block')
        code = retail_mopp(bytes(c.data[row] for row in rows))
        struct.pack_into('>III', out, 0x30, len(code), b.alloc(code) if code else 0, 0)
        out[0x3c] = c.data[at+0x3c]
    return bytes(out)
