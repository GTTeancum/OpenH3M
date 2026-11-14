"""Audited native H3 dither pixels for the Powerhouse overlay composition.

This is not a generic native image decoder. The stock 8x8 Y8 payload uses
one-byte Xenos microtiles, unlike the BC/ARGB formats supported elsewhere.
Expanded pixels match all five supplied local MCC copies byte-for-byte.
"""
import hashlib
from pathlib import Path
import numpy as np
from cache_reader import Cache
from resource_reader import Resource
from encode_bitmap import expand_argb

NAME = r'shaders\default_bitmaps\bitmaps\dither_pattern'
RGBA_SHA256 = 'c4ea99f1a910b3d9193ee5bb27a5bcaf1559e0edfe36f0648eaf6b1b5f74a65c'


def decode_native_dither(payload):
    if len(payload) != 64:
        raise ValueError('Native dither must have exactly64 Y8 texels')
    # Xenos tiled address for x,y<8 and one byte/texel:
    # ((y & 2)<<2) + ((y & 4)<<3) + x + ((y & 1)<<4).
    # Address bit4 is moved to bit5; no endian swap for Y8.
    linear = bytes(payload[((y & 2) << 2) + ((y & 4) << 3) + x + ((y & 1) << 4)]
                   for y in range(8) for x in range(8))
    expanded = expand_argb(linear, 8, 8, 1)
    if hashlib.sha256(expanded).hexdigest() != RGBA_SHA256:
        raise ValueError('Native dither differs from audited stock pixels')
    return np.frombuffer(expanded, np.uint8).reshape(8, 8, 4)[:, :, :3].astype(np.float32) / 255


def read_overlay(materials, tag):
    source = materials.source
    info = materials.bitmaps.info(tag)
    rows = source.block(source.tags[tag]['offset'] + 96, 56)
    if (source.name(tag) != NAME or len(info) != 1 or len(rows) != 1
            or tuple(info[0][k] for k in ('width', 'height', 'format', 'mips')) != (8, 8, 11, 1)
            or source.unpack('H', rows[0] + 10)[0] != 0 or source.data[rows[0] + 21] != 3):
        raise ValueError('Powerhouse overlay is not the audited linear stock dither')
    native = getattr(materials, 'native_assets', None)
    candidates = native.candidates.get(('bitm', NAME), []) if native else []
    matches = [(Path(path), index) for path, index in candidates if Path(path).name == 'sandbox.map']
    if len(matches) != 1:
        raise ValueError('Audited native Sandbox dither donor unavailable')
    path, index = matches[0]
    cache = Cache(path)
    try:
        root = cache.tags[index]['offset']
        rows, handles = cache.block(root + 96, 48), cache.block(root + 140, 8)
        if len(rows) != 1 or len(handles) != 1:
            raise ValueError('Native dither image/resource table changed')
        row = rows[0]
        if (cache.unpack('HH', row + 4) != (8, 8) or cache.unpack('HH', row + 10) != (0, 1)
                or cache.data[row + 20] != 0 or cache.data[row + 21] != 3):
            raise ValueError('Native dither format/curve changed')
        resource = Resource(cache, cache.u(handles[0]),
                            {r'maps\shared.map': path.parent / 'shared.map'})
        if (len(resource.data) != 64 or resource.root != 52
                or resource.unpack('I', 0)[0] != 64 or resource.unpack('I', 20)[0] != 0
                or resource.unpack('HH', 40) != (8, 8)
                or resource.data[44:48] != bytes([1, 1, 0, 0])):
            raise ValueError('Native dither resource control changed')
        return decode_native_dither(resource.raw[0][:64])
    finally:
        cache.close()
