"""Linear MCC Reach lightmap channels; never interpret DXN as normal vectors.

Unsigned interpolation matches TagTool BitmapCompression (ce2dc6ac), including
its integer rounding. Direction red is log intensity; alpha is a light mask.
"""
import numpy as np


def _bc4(blocks):
    a = blocks[:, 0].astype(np.uint16)
    b = blocks[:, 1].astype(np.uint16)
    palette = np.empty((len(blocks), 8), dtype=np.uint8)
    palette[:, 0], palette[:, 1] = a, b
    for i in range(2, 8):
        seven = ((8-i)*a + (i-1)*b + 3)//7
        five = ((6-i)*a + (i-1)*b + 2)//5 if i < 6 else (0 if i == 6 else 255)
        palette[:, i] = np.where(a > b, seven, five)
    selectors = np.zeros(len(blocks), dtype=np.uint64)
    for i in range(6):
        selectors |= blocks[:, i+2].astype(np.uint64) << (8*i)
    indices = (selectors[:, None] >> (3*np.arange(16, dtype=np.uint64))) & 7
    return np.take_along_axis(palette, indices.astype(np.intp), axis=1)


def decode_mono_alpha(pixels, width, height):
    """Return H×W×4 uint8 RGBA; both BC4 blocks are UNORM, not SNORM."""
    if width <= 0 or height <= 0:
        raise ValueError('Lightmap dimensions must be positive')
    bx, by = (width+3)//4, (height+3)//4
    if len(pixels) != bx*by*16:
        raise ValueError('Unexpected BC5 lightmap byte count')
    blocks = np.frombuffer(pixels, dtype=np.uint8).reshape(-1, 16)
    mono, alpha = _bc4(blocks[:, :8]), _bc4(blocks[:, 8:])
    rgba = np.stack((mono, mono, mono, alpha), axis=-1)
    return rgba.reshape(by, bx, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(by*4, bx*4, 4)[:height, :width].copy()
