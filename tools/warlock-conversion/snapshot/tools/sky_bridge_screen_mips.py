"""Retain audited Sky Bridge billboard mips with native packed-tail addresses.

Call only after stock/native asset lookup. These are custom textures from the
Halo Online map pack; no authored pixels, constants or animation are changed.
"""
import hashlib
from pathlib import Path
import struct

import numpy as np

from encode_bitmap import encode_bitmap_base
from xbox_bitmap import addresses

TEXTURES = {
    r'levels\shared\bitmaps\human\crop_01':
        ((256, 256, 11, 9), 'e0d4c49e9abb36e5afd23b68e8fe20797afa6120aa3a99839c9ae9b3a161095d'),
    r'objects\bitmaps\screen_maps\screen_line_01':
        ((128, 16, 14, 8), '2d7a8477335935dfb5f3a035212edd99c256b2060e4eaa81ad86d0c6392008ee')}


def encode(source, tag):
    name = source.c.name(tag)
    dimensions, expected_hash = TEXTURES[name]
    info, = source.info(tag)
    if tuple(info[k] for k in ('width', 'height', 'format', 'mips')) != dimensions:
        raise ValueError('Sky Bridge screen dimensions or format changed; re-audit')
    pixels = source.pixels(tag)
    if hashlib.sha256(pixels).hexdigest() != expected_hash:
        raise ValueError('Sky Bridge authored screen mip bytes changed; re-audit')
    fixups = [(12, 0x40000000), (52, 0x20000000)]
    if dimensions[2] == 11:
        record, control, raw = encode_bitmap_base(source, tag, preserve_color_mips=True)
    else:
        record, control, _ = encode_bitmap_base(source, tag)
        # Verified against native GetPackedMipOffset/GetTiledOffset2D for
        # every BC1 block. At 128x16, all eight levels share the level-0 tail.
        offsets = ((0, 4), (0, 2), (0, 1), (16, 0), (8, 0), (4, 0), (2, 0), (1, 0))
        tiled = addresses(32, 32, 8)
        raw = np.zeros(4096, dtype=np.uint8)
        consumed = 0
        for level, (x, y) in enumerate(offsets):
            wb, hb = (max(1, 128 >> level)+3)//4, (max(1, 16 >> level)+3)//4
            size = wb*hb*8
            blocks = np.frombuffer(pixels[consumed:consumed+size], dtype=np.uint8)
            blocks = blocks.reshape(-1, 2)[:, ::-1].reshape(-1, 8)
            pos = tiled[y:y+hb, x:x+wb]
            raw[pos.reshape(-1, 1)+np.arange(8)] = blocks
            consumed += size
        assert consumed == len(pixels)
        raw = raw.tobytes()
        record, control = bytearray(record), bytearray(control)
        record[20] = 7
        struct.pack_into('>I', record, 28, len(raw))
        struct.pack_into('>I', control, 0, len(raw))
        struct.pack_into('>I', control, 20, len(raw))
        control[45], control[47] = 8, 1
        # Native 82298970 -> 82097828 sets both addresses explicitly. Generic
        # relocation (826085A8) leaves the zero packed-tail offset as null.
        # Aliasing both data references keeps one resource allocation and
        # ensures the optional-base test retains minimum LOD zero.
        fixups.insert(1, (32, 0x40000000))
        record, control = bytes(record), bytes(control)
    if record[21] != (3 if dimensions[2] == 11 else 1):
        raise ValueError('Sky Bridge screen color curve changed; re-audit')
    return record, {'control': control, 'raw': raw, 'root': 52,
                    'fixups': fixups, 'interops': [(0x20000034, 2)]}


def import_bitmap(importer, tag):
    source = importer.source
    name = source.name(tag)
    if Path(source.file.name).name.casefold() != 's3d_sky_bridgenew.map' or name not in TEXTURES:
        return None
    record, resource = encode(importer.bitmaps, tag)
    root = bytearray(0xa4)
    struct.pack_into('>H', root, 4, 0x50)
    owner, address = importer.registry.newtag('bitm', root)
    handle = importer.registry.add_resource(owner, 'bitmap_texture_interop_resource', resource)
    b = importer.builder
    b.put(address+0x60, 'III', 1, b.alloc(record), 0)
    b.put(address+0x8c, 'III', 1, b.alloc(struct.pack('>II', handle, 0)), 0)
    b.put(address+0x98, 'III', 0, 0, 0)
    importer.done[('bitm', name)] = owner
    importer.report.append({'source': name, 'authored_mips_retained': record[20]+1,
        'raw_bytes': len(resource['raw']), 'source_pixels_unchanged': True,
        'packed_tail_explicit_addresses': len(resource['fixups']) == 3})
    return owner
