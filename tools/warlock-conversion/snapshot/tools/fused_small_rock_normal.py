"""Compose reviewed Powerhouse DXT5NM layers into native signed XY normals."""
import numpy as np
from PIL import Image
from encode_bitmap import mip_size
from fused_ridge_normal import sample, normal


def decode(source, tag, expected_dimensions):
    infos = source.info(tag)
    if len(infos) != 1:
        raise ValueError('Small-rock normal must have one image')
    info = infos[0]
    if (info['width'], info['height']) != expected_dimensions or info['format'] != 16:
        raise ValueError('Small-rock DXT5NM dimensions/format changed')
    row = source.c.block(source.c.tags[tag]['offset']+96, 56)[0]
    if source.c.unpack('H', row+10)[0] != 0 or source.c.data[row+21] != 3:
        raise ValueError('Small-rock normals must be linear 2D images')
    data, offset, levels = source.pixels(tag), 0, []
    for level in range(info['mips']):
        w, h = max(1, info['width'] >> level), max(1, info['height'] >> level)
        size = mip_size(w, h, 16)
        rgba = np.asarray(Image.frombytes('RGBA', (w, h), data[offset:offset+size], 'bcn', 3)).astype(float)
        offset += size
        # HaloShaderGenerator bump_mapping_util.fx DXT5_NORMALS: X in
        # eight-bit alpha, Y in the six-bit green component, signed bias.
        xy = np.stack(((rgba[..., 3]-128)/127,
                       (rgba[..., 1]*(63/255)-32)/31), axis=-1)
        levels.append(xy)
    if offset != len(data):
        raise ValueError('Unexpected DXT5NM trailing payload')
    return levels


def bake(source, base_tag, detail_tag):
    base = decode(source, base_tag, (1024, 512))
    detail = decode(source, detail_tag, (512, 512))
    result = bytearray()
    for level in range(11):
        w, h = max(1, 1024 >> level), max(1, 512 >> level)
        yy, xx = np.indices((h, w))
        uv = np.stack(((xx+.5)/w, (yy+.5)/h), axis=-1)
        value = normal(sample(base[min(level, len(base)-1)], uv))
        layer = normal(sample(detail[min(level, len(detail)-1)], uv*np.array([2., 1.])))
        value[..., :2] += 2.5*layer[..., :2]
        value /= np.linalg.norm(value, axis=-1, keepdims=True)
        result.extend(np.rint(value[..., :2]*127).astype(np.int8).tobytes())
    class Baked:
        c = source.c
        def info(self, unused):
            return [dict(width=1024, height=512, format=22, mips=11, kind=0, curve=3)]
        def pixels(self, unused, index=0):
            return bytes(result)
    return Baked()
