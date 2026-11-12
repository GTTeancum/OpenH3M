"""Combine static, identically sampled wire detail layers for native H3.

Two-detail albedo is base * D^2 * a * b. Native default albedo is
base * D * combined, so combined = D*a*b, with alpha = a.alpha*b.alpha.
Filtering the product is an approximation; parallax and emission stay live.
"""
import numpy as np
from PIL import Image
from encode_bitmap import mip_size


def bake(materials, post):
    s = materials.source
    names, constants = materials.parameters(s, materials.source_strings, post)
    values = dict(zip(constants, [s.unpack('4f', r) for r in s.block(post+28, 16)]))
    if values['detail_map'] != (2., 8., 0., 0.) or values['detail_map2'] != values['detail_map']:
        raise ValueError('Wire detail transforms changed')
    rows = [s.block(post+16, 28)[names.index(n)] for n in ('detail_map', 'detail_map2')]
    if s.data[rows[0]+16:rows[0]+22] != s.data[rows[1]+16:rows[1]+22] or any(s.unpack('H', r+24)[0] for r in rows):
        raise ValueError('Wire detail samplers differ or animate')
    layers = []
    for row in rows:
        tag = s.u(row+12) & 65535
        info = materials.bitmaps.info(tag)
        if len(info) != 1 or (info[0]['width'], info[0]['height'], info[0]['format'], info[0]['mips']) != (512, 512, 16, 10):
            raise ValueError('Wire detail image layout changed')
        curve = s.data[s.block(s.tags[tag]['offset']+96, 56)[0]+21]
        if curve not in (1, 3, 5):
            raise ValueError('Unsupported wire detail color curve')
        data = materials.bitmaps.pixels(tag)
        offset, mips = 0, []
        for level in range(10):
            size = max(1, 512 >> level)
            count = mip_size(size, size, 16)
            rgba = np.asarray(Image.frombytes('RGBA', (size, size), data[offset:offset+count], 'bcn', 3), dtype=np.float64)/255.
            if curve in (1, 5):
                rgb = rgba[:, :, :3]
                rgba[:, :, :3] = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
            mips.append(rgba)
            offset += count
        layers.append(mips)
    output, maximum, error = [], 0., 0.
    for a, b in zip(*layers):
        combined = a*b
        combined[:, :, :3] *= 4.59479
        if np.any(combined < 0) or np.any(combined > 1):
            raise ValueError('Wire detail product would clip')
        maximum = max(maximum, float(combined[:, :, :3].max()))
        rgb = combined[:, :, :3]
        encoded = combined.copy()
        encoded[:, :, :3] = np.where(rgb <= .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
        quantized = np.rint(encoded*255).astype(np.uint8)
        decoded = quantized[:, :, :3].astype(float)/255
        decoded = np.where(decoded <= .04045, decoded/12.92, ((decoded+.055)/1.055)**2.4)
        error = max(error, float(abs(decoded-rgb).max()))
        output.append(quantized[:, :, [2, 1, 0, 3]].tobytes())
    class Baked:
        def info(self, unused):
            return [dict(width=512, height=512, format=11, mips=10, kind=0, curve=1)]
        def pixels(self, unused, index=0):
            return b''.join(output)
    return Baked(), dict(equation='combined RGB = 4.59479 * detail1 * detail2; alpha = alpha1 * alpha2',
                         maximum_linear_rgb=maximum, maximum_quantization_error=error,
                         approximation='Filtering a precomputed product differs from multiplying filtered samples')
