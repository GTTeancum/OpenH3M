"""Link bridge-serialized native metadata into a destination map allocation."""
import base64
import struct


ROOT_SIZES = {'mode': 0x1cc, 'hlmt': 0x188}


def link_metadata(record, builder, translate_string, resolve_tag):
    group = record['group']
    if group not in ROOT_SIZES:
        raise ValueError('Bridge metadata group requires review')
    metadata = record['metadata']
    data = bytearray(base64.b64decode(metadata['data'], validate=True))
    root = metadata['root']
    if root < 0 or root + ROOT_SIZES[group] != len(data):
        raise ValueError('Bridge root allocation size differs from native layout')
    touched = set()

    def field(offset, size=4):
        if offset < 0 or offset + size > len(data):
            raise ValueError('Bridge relocation outside metadata')
        if any(i in touched for i in range(offset, offset + size)):
            raise ValueError('Overlapping bridge relocations')
        touched.update(range(offset, offset + size))

    for row in metadata['strings']:
        at = row['offset']
        field(at)
        if struct.unpack_from('>I', data, at)[0] != row['value']:
            raise ValueError('Bridge string relocation disagrees with bytes')
        struct.pack_into('>I', data, at, translate_string(row['value']))
    for row in metadata['tags']:
        at = row['offset']
        field(at, 4 if row['shortReference'] else 16)
        target_group, datum = resolve_tag(row['datum'])
        if not 0 <= datum <= 0xffffffff or len(target_group) != 4:
            raise ValueError('Invalid resolved tag reference')
        if row['shortReference']:
            struct.pack_into('>I', data, at, datum)
        else:
            data[at:at+4] = target_group.encode('ascii')
            struct.pack_into('>I', data, at+12, datum)
    for at in metadata['pointers']:
        field(at)
        value = struct.unpack_from('>I', data, at)[0]
        if value >= len(data):
            raise ValueError('Bridge pointer outside metadata')
    base = builder.alloc(data)
    for at in metadata['pointers']:
        value = struct.unpack_from('>I', data, at)[0]
        builder.put(base + at, 'I', base + value)
    return base + root
