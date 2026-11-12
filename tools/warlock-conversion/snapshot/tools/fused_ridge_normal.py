"""Precompose Powerhouse's static, commensurate two-layer ridge normals."""
import numpy as np
from normal_strength import decode_blocks, valid_pixels
from encode_bitmap import mip_size


def sample(image, uv):
    h, w = image.shape[:2]
    v = uv*np.array([w, h])-.5
    lo = np.floor(v).astype(int)
    f = v-lo
    x, y = lo[..., 0], lo[..., 1]
    fx, fy = f[..., 0, None], f[..., 1, None]
    return ((image[y % h, x % w]*(1-fx)+image[y % h, (x+1) % w]*fx)*(1-fy)
            +(image[(y+1) % h, x % w]*(1-fx)+image[(y+1) % h, (x+1) % w]*fx)*fy)


def normal(xy):
    z = np.sqrt(np.maximum(1-np.sum(xy*xy, axis=-1, keepdims=True), 0))
    v = np.concatenate((xy, z), axis=-1)
    return v/np.linalg.norm(v, axis=-1, keepdims=True)


def bake(source, tag, base_transform, detail_transform):
    infos = source.info(tag)
    if len(infos) != 1 or (infos[0]['format'], infos[0]['width'], infos[0]['height']) != (33, 512, 512):
        raise ValueError('Combined ridge normal requires reviewed 512-square BC5 source')
    if tuple(base_transform[:2]) != (10., 10.) or tuple(detail_transform[:2]) != (5., 5.):
        raise ValueError('Combined ridge normal requires reviewed 2:1 frequency ratio')
    row = source.c.block(source.c.tags[tag]['offset']+96, 56)[0]
    if source.c.unpack('H', row+10)[0] != 0 or source.c.data[row+21] != 3:
        raise ValueError('Combined ridge normal must be linear 2D data')
    raw, levels, offset = source.pixels(tag), [], 0
    for level in range(infos[0]['mips']):
        n = max(1, 512 >> level)
        size = mip_size(n, n, 33)
        blocks = np.frombuffer(raw[offset:offset+size], dtype=np.uint8).reshape(-1, 2, 8)
        levels.append(valid_pixels(decode_blocks(blocks), n, n))
        offset += size
    if offset != len(raw):
        raise ValueError('Unexpected ridge normal mip payload')
    shift = np.asarray(base_transform[2:])-2*np.asarray(detail_transform[2:])
    result = bytearray()
    for level in range(11):
        n = max(1, 1024 >> level)
        yy, xx = np.indices((n, n))
        uv = np.stack(((xx+.5)/n, (yy+.5)/n), axis=-1)
        base = normal(sample(levels[min(level, len(levels)-1)], uv*2+shift))
        detail = normal(sample(levels[min(max(level-1, 0), len(levels)-1)], uv))
        base[..., :2] += 2*detail[..., :2]
        base /= np.linalg.norm(base, axis=-1, keepdims=True)
        result.extend(np.rint(base[..., :2]*127).astype(np.int8).tobytes())
    class Baked:
        c = source.c
        def info(self, unused):
            return [dict(width=1024, height=1024, format=22, mips=11, kind=0, curve=3)]
        def pixels(self, unused, index=0):
            return bytes(result)
    return Baked()
