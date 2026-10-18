"""Bake the separate, untiled decal mask into tiled diffuse alpha for retail.

POC: nearest sampling, one mip, maximum 512 pixels. No sprite atlases.
The mask's alpha replaces diffuse alpha; it is not multiplied by diffuse alpha.
"""
import numpy as np
from PIL import Image
from encode_bitmap import encode_bitmap_base, expand_argb, mip_size


def decode(source, tag):
    info = source.info(tag)[0]
    w, h, fmt = info['width'], info['height'], info['format']
    data = source.pixels(tag)
    level = 0
    while max(w, h) > 512:
        level += 1
        if level >= info['mips']:
            raise ValueError('Decal bitmap has no mip within the POC size limit')
        data = data[mip_size(w, h, fmt):]
        w, h = max(1, w // 2), max(1, h // 2)
    if fmt in (0, 1, 10, 11):
        bgra = np.frombuffer(expand_argb(data, w, h, fmt), dtype=np.uint8).reshape(h, w, 4)
        return bgra[:, :, [2, 1, 0, 3]]
    if fmt not in (14, 16):
        raise ValueError(f'Unsupported decal diffuse/mask format {fmt}')
    return np.array(Image.frombytes('RGBA', (w, h), data[:mip_size(w, h, fmt)],
                                   'bcn', 1 if fmt == 14 else 3))


def bake(source, base_tag, mask_tag, tiles):
    if not all(np.isfinite(value) and 0 < value <= 32 for value in tiles):
        raise ValueError('Unsupported decal tile scale')
    for tag in (base_tag, mask_tag):
        root = source.c.tags[tag]['offset']
        if len(source.info(tag)) != 1 or source.c.u(root + 0x54):
            raise ValueError('Decal mask baking does not support sprite/multi-image bitmaps')
    base, mask = decode(source, base_tag), decode(source, mask_tag)
    h, w = min(512, max(base.shape[0], mask.shape[0])), min(512, max(base.shape[1], mask.shape[1]))
    u, v = (np.arange(w) + .5) / w, (np.arange(h) + .5) / h
    bx = ((u * tiles[0] % 1) * base.shape[1]).astype(int)
    by = ((v * tiles[1] % 1) * base.shape[0]).astype(int)
    mx, my = (u * mask.shape[1]).astype(int), (v * mask.shape[0]).astype(int)
    rgba = base[by[:, None], bx].copy()
    rgba[:, :, 3] = mask[my[:, None], mx, 3]
    payload = rgba[:, :, [2, 1, 0, 3]].tobytes()

    class BakedSource:
        c = source.c

        def info(self, tag):
            return [{'width': w, 'height': h, 'format': 11, 'mips': 1}]

        def pixels(self, tag, index=0):
            return payload

    return encode_bitmap_base(BakedSource(), base_tag)
