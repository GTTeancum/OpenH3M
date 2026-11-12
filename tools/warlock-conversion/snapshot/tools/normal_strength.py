"""Bake detail strength with bounded error into native signed normal textures.

Attenuation retains BC5 size; reviewed amplification can use signed XY to avoid
compression-endpoint clipping. Every mip is checked before encoding.
"""
import numpy as np
from encode_bitmap import mip_size


def decode_blocks(blocks):
    endpoints = np.maximum(blocks[:, :, :2].copy().view(np.int8).astype(float), -127) / 127
    table = np.zeros((len(blocks), 2, 8))
    table[:, :, :2] = endpoints
    greater = endpoints[:, :, 0] > endpoints[:, :, 1]
    for k in range(2, 8):
        seven = ((8-k)*endpoints[:, :, 0] + (k-1)*endpoints[:, :, 1])/7
        five = ((6-k)*endpoints[:, :, 0] + (k-1)*endpoints[:, :, 1])/5 if k < 6 else (-1 if k == 6 else 1)
        table[:, :, k] = np.where(greater, seven, five)
    packed = sum(blocks[:, :, j+2].astype(np.uint64) << (8*j) for j in range(6))
    selectors = ((packed[:, :, None] >> (3*np.arange(16, dtype=np.uint64))) & 7).astype(int)
    return np.take_along_axis(table, selectors, axis=2).transpose(0, 2, 1)


def valid_pixels(values, width, height):
    return values.reshape((height+3)//4, (width+3)//4, 4, 4, 2).transpose(0, 2, 1, 3, 4).reshape(
        ((height+3)//4)*4, ((width+3)//4)*4, 2)[:height, :width]


def scaled_strength(source, tag, coefficient, *, uncompressed=False):
    if not np.isfinite(coefficient) or coefficient <= 0:
        raise ValueError('Detail-normal coefficient must be finite and positive')
    infos = source.info(tag)
    if len(infos) != 1 or infos[0]['format'] != 33:
        raise ValueError('Scaled detail requires one signed BC5 image')
    info = infos[0]
    row = source.c.block(source.c.tags[tag]['offset']+96, 56)[0]
    if source.c.unpack('H', row+10)[0] != 0 or source.c.data[row+21] != 3:
        raise ValueError('Detail normal must be linear 2D data')
    raw = source.pixels(tag)
    result = bytearray()
    offset = 0
    errors = []
    for level in range(info['mips']):
        w, h = max(1, info['width'] >> level), max(1, info['height'] >> level)
        size = mip_size(w, h, 33)
        blocks = np.frombuffer(raw[offset:offset+size], dtype=np.uint8).reshape(-1, 2, 8)
        offset += size
        original = valid_pixels(decode_blocks(blocks), w, h)
        if np.any(np.sum(original*original, axis=2) > 1.00000001):
            raise ValueError('Detail requires nonlinear normal reconstruction before scaling')
        if uncompressed:
            scaled_pixels = np.rint(original*coefficient*127)
            if np.any(np.abs(scaled_pixels)>127):
                raise ValueError('Scaled normal pixels exceed native signed XY range')
            actual = scaled_pixels/127
            if np.any(np.sum(actual*actual,axis=2)>1.00000001):
                raise ValueError('Scaled normal pixels require nonlinear reconstruction')
            errors.append(float(np.max(np.abs(actual-original*coefficient))))
            result.extend(scaled_pixels.astype(np.int8).tobytes())
            continue
        endpoints = np.maximum(blocks[:, :, :2].copy().view(np.int8).astype(np.int16), -127)
        # Unused endpoints (including padding in tiny mips) may exceed the
        # range even when every sampled texel fits. Validate decoded pixels
        # below instead of rejecting on unused compression metadata alone.
        scaled = np.clip(np.rint(endpoints*coefficient), -127, 127).astype(np.int16)
        # Preserve the eight-entry interpolation mode when rounding collapses
        # its endpoints. Otherwise selectors 6/7 would become extreme normals.
        collapsed = (endpoints[:, :, 0] > endpoints[:, :, 1]) & (scaled[:, :, 0] == scaled[:, :, 1])
        scaled[:, :, 0] += collapsed
        output = blocks.copy()
        output[:, :, :2] = scaled.astype(np.int8).view(np.uint8)
        actual = valid_pixels(decode_blocks(output), w, h)
        if np.any(np.sum(actual*actual, axis=2) > 1.00000001):
            raise ValueError('Scaled detail requires nonlinear normal reconstruction')
        error = float(np.max(np.abs(actual-original*coefficient)))
        if error > 1.0/127 + 1e-12:
            raise ValueError('Scaled detail exceeds one signed-eight-bit step')
        errors.append(error)
        result.extend(output.tobytes())
    if offset != len(raw):
        raise ValueError('Unexpected trailing normal data')
    class Baked:
        c = source.c
        def info(self, unused):
            return [dict(info, format=22 if uncompressed else info['format'], kind=0, curve=3)]
        def pixels(self, unused, index=0):
            return bytes(result)
    report = {'coefficient': coefficient, 'mips': info['mips'],
              'max_component_error': max(errors)}
    report.update({'encoded_bytes':len(result),'source_bytes':len(raw),'format':'native signed XY'}
                  if uncompressed else {'bytes_unchanged':len(result)})
    return Baked(), report


def half_strength(source, tag):
    return scaled_strength(source, tag, .5)
