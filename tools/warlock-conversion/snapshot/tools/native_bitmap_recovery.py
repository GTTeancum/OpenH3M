"""Recover explicitly audited, stripped native textures from retained MCC pixels.

Called only after NativeAssets exhausts all original-cache candidates. Keep the
native bitmap root and its consuming shader; replace storage and image metadata
through the established encoder. No name-only or arbitrary-image fallback.
"""
import hashlib
import struct

from encode_bitmap import encode_bitmap_base


def recover(importer, native, datum, schema):
    tag = native.tags[datum & 65535]
    name = native.name(datum & 65535)
    expected = getattr(importer, 'audited_bitmap_recoveries', {}).get(name)
    if tag['group'] != 'bitm' or expected is None:
        return None
    source = importer.source
    matches = [(index, entry) for index, entry in source.tags.items()
               if entry['group'] == 'bitm' and source.name(index) == name]
    if len(matches) != 1:
        raise ValueError('Audited bitmap recovery needs one source: ' + name)
    index, source_tag = matches[0]
    source_rows = source.block(source_tag['offset'] + 96, 56)
    native_rows = native.block(tag['offset'] + 96, 48)
    if len(source_rows) != 1 or len(native_rows) != 1:
        raise ValueError('Audited bitmap recovery requires one image: ' + name)
    for cache, row in ((source, source_rows[0]), (native, native_rows[0])):
        observed = dict(width=cache.unpack('H', row + 4)[0], height=cache.unpack('H', row + 6)[0],
                        depth=cache.data[row + 8], kind=cache.unpack('H', row + 10)[0],
                        format=cache.unpack('H', row + 12)[0], mips=cache.data[row + 20] + 1,
                        curve=cache.data[row + 21])
        if observed != {key: expected[key] for key in observed}:
            raise ValueError('Audited bitmap recovery layout changed: ' + name)
    pixels = importer.materials.bitmaps.pixels(index)
    if hashlib.sha256(pixels).hexdigest() != expected['source_sha256']:
        raise ValueError('Audited bitmap recovery pixels changed: ' + name)
    if expected['kind'] != 0 or expected['depth'] != 1 or expected['format'] not in (14, 15, 16):
        raise ValueError('Audited recovery only supports single BC1/2/3 2D images')
    root = bytearray(native.data[tag['offset']:tag['offset'] + int(schema.get('baseSize'), 0)])
    for field in schema:
        if field.get('offset') is None:
            continue
        offset = int(field.get('offset'), 0)
        if field.tag.lower() == 'tagblock':
            count = native.u(tag['offset'] + offset)
            if field.get('name') in ('Bitmaps', 'Hardware Textures'):
                if count != 1:
                    raise ValueError('Audited recovery needs one native image/resource')
            elif count:
                raise ValueError('Audited recovery cannot discard ' + field.get('name'))
            # Rewritten below for images/resources; empty blocks have no address.
            root[offset:offset + 12] = bytes(12)
        elif field.tag.lower() == 'dataref':
            if native.u(tag['offset'] + offset):
                raise ValueError('Audited recovery cannot discard native bitmap data')
            root[offset:offset + 20] = bytes(20)
    encoded = encode_bitmap_base(importer.materials.bitmaps, index,
                                 max_dimension=max(expected['width'], expected['height']),
                                 preserve_authored_mips=True)
    owner = importer.materials.bitmap_resource(*encoded)
    builder = importer.builder
    address = struct.unpack_from('>I', importer.registry.tags, (owner & 65535) * 8 + 4)[0]
    generated = builder.read(address, len(root))
    for offset in (96, 140):
        root[offset:offset + 12] = generated[offset:offset + 12]
    builder.meta[address - builder.base:address - builder.base + len(root)] = root
    result = 'bitm', owner
    importer.resolved['bitm', name] = result
    importer.materials.done['bitm', name] = owner
    importer.added.append(dict(source=name, group='bitm', datum=hex(owner),
        recovered_texture='Audited same-name MCC pixels; all native resource candidates unavailable',
        native_metadata_donor=str(native.file.name), source_pixels_sha256=expected['source_sha256'],
        width=expected['width'], height=expected['height'], mips=expected['mips'],
        limitations='Original stripped pixel payload is unavailable for bit-identical comparison'))
    return result
